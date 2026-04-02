from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
import json
import logging
import os
from pathlib import Path
import sys

from dotenv import load_dotenv

from my_agents.configuration import (
    DEFAULT_CONFIG_DIR,
    AppConfig,
    load_app_config,
    load_brief,
)
from my_agents.evals.judge import build_eval_prompt, evaluate_run
from my_agents.evals.report_renderer import render_eval_report, render_standards_report
from my_agents.evidence import EvidenceRegistry, combine_open_questions
from my_agents.html_utils import markdownish_to_html_document
from my_agents.integrations.linear_push import push_linear_issue
from my_agents.llm_policy import build_llm
from my_agents.pdf_export import export_pdf
from my_agents.report_standards import assess_report_standards
from my_agents.renderers import render_full_report, render_ic_memo, render_one_pager
from my_agents.runner import AgentFinalAnswerError, AgentRunner, CrewAIAgentRunner
from my_agents.schemas import (
    ALLOWED_SECTION_KEYS,
    AgentFindingResult,
    ApprovalAction,
    ApproveMode,
    AuditResult,
    Brief,
    CompletedAgentState,
    FindingsBundle,
    OutputProfile,
    RiskLevel,
    RunArtifacts,
    RunRequest,
    RunState,
    ScorecardDimension,
    ScorecardSummary,
    SourcePriorityConfig,
    WorkflowType,
    WorkflowTaskDefinition,
)
from my_agents.tools import build_tools


WORKFLOW_DIMENSION_MULTIPLIERS: dict[str, dict[str, float]] = {
    "sourcing": {
        "market_size_and_growth": 1.0,
        "founder_quality_and_signal": 1.0,
        "business_model_and_unit_economics": 0.55,
        "product_tech_differentiation": 0.45,
        "india_regulatory_and_compliance_posture": 0.40,
        "gtm_traction_and_momentum": 1.0,
        "risk_profile": 0.80,
    },
    "due_diligence": {
        "market_size_and_growth": 1.0,
        "founder_quality_and_signal": 1.0,
        "business_model_and_unit_economics": 1.0,
        "product_tech_differentiation": 1.0,
        "india_regulatory_and_compliance_posture": 1.0,
        "gtm_traction_and_momentum": 1.0,
        "risk_profile": 1.0,
    },
    "portfolio": {
        "market_size_and_growth": 0.70,
        "founder_quality_and_signal": 0.35,
        "business_model_and_unit_economics": 1.0,
        "product_tech_differentiation": 0.55,
        "india_regulatory_and_compliance_posture": 1.0,
        "gtm_traction_and_momentum": 0.90,
        "risk_profile": 1.0,
    },
}


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "name": record.name,
        }
        if hasattr(record, "step"):
            data["step"] = record.step
        if hasattr(record, "agent"):
            data["agent"] = record.agent
        return json.dumps(data)

class VCResearchController:
    def __init__(
        self,
        runner: AgentRunner | None = None,
        prompt_fn: Callable[[str], str] | None = None,
        print_fn: Callable[[str], None] | None = None,
        now_fn: Callable[[], datetime] | None = None,
        project_root: Path | None = None,
    ) -> None:
        self.runner = runner or CrewAIAgentRunner()
        self.prompt_fn = prompt_fn or input
        self.print_fn = print_fn or print
        self.now_fn = now_fn or (lambda: datetime.now(timezone.utc))
        self.project_root = project_root

    def run(self, request: RunRequest) -> RunArtifacts:
        self._load_project_env()
        config = load_app_config(request.config_dir or DEFAULT_CONFIG_DIR)

        if request.eval_only_dir:
            run_dir = Path(request.eval_only_dir).resolve()
            bundle_path = run_dir / "findings_bundle.json"
            if not bundle_path.exists():
                raise FileNotFoundError(f"findings_bundle.json not found in {run_dir}. Cannot evaluate.")
            bundle = FindingsBundle.model_validate_json(bundle_path.read_text(encoding="utf-8"))
            run_state_path = run_dir / "run_state.json"
            state = (
                RunState.model_validate_json(run_state_path.read_text(encoding="utf-8"))
                if run_state_path.exists()
                else RunState(
                    workflow=bundle.workflow,
                    output_profile=OutputProfile.IC_MEMO,
                    company_name=bundle.company_name,
                )
            )
            brief_path = run_dir / "brief.json"
            if brief_path.exists():
                brief = load_brief(brief_path)
            else:
                brief = Brief(company_name=bundle.company_name, sector="general", geography="India")

            report_path = run_dir / "report.md"
            if report_path.exists():
                report_text = report_path.read_text(encoding="utf-8")
            elif state.output_profile == OutputProfile.FULL_REPORT:
                report_text = render_full_report(bundle)
            else:
                report_text = render_ic_memo(bundle)

            if state.output_profile == OutputProfile.ONE_PAGER:
                rendered_output = (run_dir / "one_pager.html").read_text(encoding="utf-8")
            else:
                rendered_output = report_text
            standards = assess_report_standards(
                bundle=bundle,
                workflow=state.workflow,
                output_profile=state.output_profile,
                rendered_output=rendered_output,
                required_sections=config.output_profiles[state.output_profile.value].sections,
            )
            standards_path, standards_html_path = self._write_standards_artifacts(
                run_dir=run_dir,
                assessment=standards,
            )

            self.print_fn(f"\nEvaluating existing run: {run_dir}")
            eval_path: Path | None = None
            eval_report_path: Path | None = None
            eval_report_html_path: Path | None = None
            eval_prompt_path = run_dir / "eval_prompt.txt"
            try:
                prompt_text = build_eval_prompt(brief, bundle, standards)
                eval_prompt_path.write_text(prompt_text, encoding="utf-8")
                rubric = evaluate_run(
                    brief,
                    bundle,
                    config,
                    standards_assessment=standards,
                    runner=self.runner,
                    verbose=request.verbose,
                    prompt_override=prompt_text,
                )
                eval_path, eval_report_path, eval_report_html_path = self._write_eval_artifacts(
                    run_dir=run_dir,
                    bundle=bundle,
                    rubric=rubric,
                    standards=standards,
                    eval_model=config.llm.eval_model or config.llm.model,
                    eval_prompt_path=eval_prompt_path,
                )
                self.print_fn(f"Evaluation Complete! Score: {rubric.final_eval_score}/100")
                self.print_fn(f"Feedback: {rubric.summary_feedback}")
            except Exception as ev_exc:
                self.print_fn(f"Warning: Evals skipped due to error: {ev_exc}")

            return RunArtifacts(
                run_dir=run_dir,
                report_path=report_path,
                scorecard_path=run_dir / "scorecard.json",
                sources_path=run_dir / "sources.json",
                run_state_path=run_dir / "run_state.json",
                bundle_path=bundle_path,
                report_html_path=run_dir / "report.html" if (run_dir / "report.html").exists() else None,
                one_pager_path=run_dir / "one_pager.html" if (run_dir / "one_pager.html").exists() else None,
                eval_path=eval_path,
                eval_report_path=eval_report_path,
                eval_report_html_path=eval_report_html_path,
                eval_prompt_path=eval_prompt_path if eval_prompt_path.exists() else None,
                standards_path=standards_path,
                standards_html_path=standards_html_path,
            )

        for warning in config.warnings:
            self.print_fn(f"Warning: {warning}")

        brief, run_dir, state = self._prepare_run_context(config, request)
        self._configure_local_crewai_environment(run_dir)

        logger = logging.getLogger(f"vc_research.{state.company_name}")
        logger.setLevel(logging.INFO)
        fh = None
        if not logger.handlers:
            fh = logging.FileHandler(run_dir / "execution.log", encoding="utf-8")
            fh.setFormatter(JSONFormatter())
            logger.addHandler(fh)

        logger.info(f"Initialized run for {state.company_name}", extra={"step": "init"})

        selected_profile = state.output_profile
        llm = build_llm(config.llm)
        workflow = config.workflows[state.workflow.value]
        source_profile = config.resolve_source_profile(
            brief.sector,
            request.sources_profile,
        )
        weights = config.resolve_score_weights(brief.sector)
        evidence = EvidenceRegistry(source_profile=source_profile)

        # Initialize RAG vector store
        chroma_collection = None
        indexer = None
        try:
            from my_agents.tools.rag_tool import DocumentIndexer
            indexer = DocumentIndexer()
            run_collection_id = f"{self._slugify(brief.company_name)}-{state.workflow.value}"
            chroma_collection = indexer.create_collection(run_collection_id)
            if brief.docs_dir:
                doc_count = indexer.index_docs_dir(chroma_collection, brief.docs_dir)
                if doc_count:
                    self.print_fn(f"Indexed {doc_count} document chunks into vector store.")
        except Exception as rag_exc:
            self.print_fn(f"Warning: RAG initialization skipped: {rag_exc}")

        for completed in state.completed_agents:
            finding_path = run_dir / "findings" / f"{completed.agent_name}.json"
            if finding_path.exists():
                result = AgentFindingResult.model_validate_json(
                    finding_path.read_text(encoding="utf-8")
                )
                state.findings[completed.agent_name] = result
                evidence.add_result(result)

        for task in workflow.tasks:
            if task.agent in {entry.agent_name for entry in state.completed_agents}:
                continue
            prompt = self._build_specialist_prompt(
                brief=brief,
                task=task,
                config=config,
                state=state,
                evidence=evidence,
                source_profile=source_profile,
            )
            tools = build_tools(brief, source_profile, task.agent, chroma_collection=chroma_collection)
            self._write_run_state(run_dir, state, workflow)

            logger.info(f"Starting agent: {task.agent}", extra={"step": "agent_start", "agent": task.agent})
            self.print_fn(f"\n[bold green]Starting Agent: {task.agent}[/]")

            try:
                result = self.runner.run_agent(
                    agent_name=task.agent,
                    spec=config.agents[task.agent],
                    prompt=prompt,
                    response_model=AgentFindingResult,
                    llm=llm,
                    tools=tools,
                    verbose=request.verbose,
                )
            except AgentFinalAnswerError as exc:
                logger.warning(
                    f"Agent failed to finalize after retries: {task.agent}",
                    extra={"step": "agent_fallback", "agent": task.agent},
                )
                self.print_fn(
                    f"Warning: {task.agent} did not reach a final answer. "
                    "Recording a conservative placeholder result and continuing."
                )
                result = self._build_failed_agent_result(
                    agent_name=task.agent,
                    spec=config.agents[task.agent],
                    error=exc,
                )
            if not isinstance(result, AgentFindingResult):
                result = AgentFindingResult.model_validate(result.model_dump())
            result = self._normalize_agent_result(
                result=result,
                agent_key=task.agent,
                spec=config.agents[task.agent],
                config=config,
            )

            self._persist_agent_result(run_dir, result)
            evidence.add_result(result)
            state.findings[task.agent] = result

            # Index agent findings for cross-agent RAG
            if indexer and chroma_collection is not None and result.findings:
                try:
                    findings_text = "\n".join(
                        f"- {f.claim} (confidence: {f.confidence}, source: {f.source_ref})"
                        for f in result.findings
                    )
                    indexer.index_agent_findings(
                        chroma_collection,
                        agent_name=task.agent,
                        summary=result.summary,
                        findings_text=findings_text,
                    )
                except Exception:
                    pass  # RAG indexing is non-critical

            logger.info(
                f"Completed agent: {task.agent}",
                extra={"step": "agent_complete", "agent": task.agent}
            )
            state.completed_agents.append(
                CompletedAgentState(
                    agent_name=task.agent,
                    completed_at=self.now_fn(),
                )
            )
            state.pending_flags.extend(result.downstream_flags)
            state.pending_agents = self._remaining_agents(workflow.tasks, state)
            state.last_updated = self.now_fn()
            self._write_run_state(run_dir, state, workflow)

            if task.checkpoint:
                action = self._handle_checkpoint(
                    task.agent,
                    evidence.summary(),
                    request.approve_mode,
                )
                state.checkpoint_history[task.agent] = action
                state.last_updated = self.now_fn()
                self._write_run_state(run_dir, state, workflow)
                if action == ApprovalAction.ABORT:
                    logger.warning("Run aborted at manual checkpoint", extra={"step": "checkpoint", "agent": task.agent})
                    raise SystemExit("Run aborted at manual checkpoint.")

        logger.info("Starting synthesis and audit", extra={"step": "synthesis"})
        audit = self._run_evidence_audit(config, llm, evidence, request.verbose)
        bundle = self._run_report_synthesizer(
            config=config,
            llm=llm,
            brief=brief,
            state=state,
            evidence=evidence,
            audit=audit,
            weights=weights,
            verbose=request.verbose,
        )

        bundle_path = run_dir / "findings_bundle.json"
        bundle_path.write_text(bundle.model_dump_json(indent=2), encoding="utf-8")
        scorecard_path = run_dir / "scorecard.json"
        scorecard_path.write_text(
            bundle.scorecard.model_dump_json(indent=2), encoding="utf-8"
        )
        sources_path = run_dir / "sources.json"
        sources_path.write_text(
            json.dumps(evidence.unique_sources(), indent=2), encoding="utf-8"
        )

        report_path = run_dir / "report.md"
        report_html_path = run_dir / "report.html"
        one_pager_path: Path | None = None
        pdf_path: Path | None = None
        report_text = ""
        rendered_output = ""

        if selected_profile == OutputProfile.IC_MEMO:
            report_text = render_ic_memo(bundle)
            report_path.write_text(report_text, encoding="utf-8")
            report_html_path.write_text(
                markdownish_to_html_document(report_text, f"{brief.company_name} IC Memo"),
                encoding="utf-8",
            )
            rendered_output = report_text
            candidate_pdf_path = run_dir / "report.pdf"
            try:
                export_pdf(report_text, candidate_pdf_path, f"{brief.company_name} IC Memo")
                pdf_path = candidate_pdf_path
            except Exception as exc:
                self.print_fn(f"Warning: PDF export skipped due to error: {exc}")
        elif selected_profile == OutputProfile.FULL_REPORT:
            report_text = render_full_report(bundle)
            report_path.write_text(report_text, encoding="utf-8")
            report_html_path.write_text(
                markdownish_to_html_document(report_text, f"{brief.company_name} Full Report"),
                encoding="utf-8",
            )
            rendered_output = report_text
            candidate_pdf_path = run_dir / "report.pdf"
            try:
                export_pdf(report_text, candidate_pdf_path, f"{brief.company_name} Full Report")
                pdf_path = candidate_pdf_path
            except Exception as exc:
                self.print_fn(f"Warning: PDF export skipped due to error: {exc}")
        else:
            report_text = render_ic_memo(bundle)
            report_path.write_text(report_text, encoding="utf-8")
            report_html_path.write_text(
                markdownish_to_html_document(report_text, f"{brief.company_name} One Pager Briefing"),
                encoding="utf-8",
            )
            one_pager_path = run_dir / "one_pager.html"
            rendered_output = render_one_pager(bundle)
            one_pager_path.write_text(rendered_output, encoding="utf-8")

        standards = assess_report_standards(
            bundle=bundle,
            workflow=state.workflow,
            output_profile=selected_profile,
            rendered_output=rendered_output,
            required_sections=config.output_profiles[state.output_profile.value].sections,
        )
        standards_path, standards_html_path = self._write_standards_artifacts(
            run_dir=run_dir,
            assessment=standards,
        )

        try:
            push_linear_issue(
                bundle=bundle,
                workflow=state.workflow,
                output_profile=state.output_profile,
                run_dir=run_dir,
                integrations=config.integrations,
            )
        except Exception as exc:
            self.print_fn(f"Warning: Linear push skipped due to error: {exc}")

        eval_path: Path | None = None
        eval_report_path: Path | None = None
        eval_report_html_path: Path | None = None
        eval_prompt_path: Path | None = None
        if request.run_evals:
            self.print_fn("\nRunning VC Evaluation Judge...")
            logger.info("Starting subjective evaluations", extra={"step": "evaluate"})
            try:
                prompt_text = build_eval_prompt(brief, bundle, standards)
                eval_prompt_path = run_dir / "eval_prompt.txt"
                eval_prompt_path.write_text(prompt_text, encoding="utf-8")
                rubric = evaluate_run(
                    brief,
                    bundle,
                    config,
                    standards_assessment=standards,
                    runner=self.runner,
                    verbose=request.verbose,
                    prompt_override=prompt_text,
                )
                eval_path, eval_report_path, eval_report_html_path = self._write_eval_artifacts(
                    run_dir=run_dir,
                    bundle=bundle,
                    rubric=rubric,
                    standards=standards,
                    eval_model=config.llm.eval_model or config.llm.model,
                    eval_prompt_path=eval_prompt_path,
                )
                self.print_fn(f"Evaluation Complete! Score: {rubric.final_eval_score}/100")
                self.print_fn(f"Feedback: {rubric.summary_feedback}")
            except Exception as ev_exc:
                self.print_fn(f"Warning: Evals skipped due to error: {ev_exc}")

        self._update_latest_symlink(run_dir)
        logger.info("Run finished", extra={"step": "finish"})

        if fh:
            fh.close()
            logger.removeHandler(fh)

        return RunArtifacts(
            run_dir=run_dir,
            report_path=report_path,
            scorecard_path=scorecard_path,
            sources_path=sources_path,
            run_state_path=run_dir / "run_state.json",
            bundle_path=bundle_path,
            pdf_path=pdf_path,
            one_pager_path=one_pager_path,
            report_html_path=report_html_path,
            eval_path=eval_path,
            eval_report_path=eval_report_path,
            eval_report_html_path=eval_report_html_path,
            eval_prompt_path=eval_prompt_path,
            standards_path=standards_path,
            standards_html_path=standards_html_path,
        )

    def _prepare_run_context(
        self,
        config: AppConfig,
        request: RunRequest,
    ) -> tuple[Brief, Path, RunState]:
        project_root = self.project_root or Path(__file__).resolve().parents[2]
        runs_root = project_root / "runs"
        runs_root.mkdir(parents=True, exist_ok=True)

        if request.resume is not None:
            run_dir = request.resume.resolve()
            run_state_path = run_dir / "run_state.json"
            if not run_state_path.exists():
                raise FileNotFoundError(
                    f"No run_state.json found in {run_dir}. Use --brief to start a fresh run."
                )
            state = RunState.model_validate_json(run_state_path.read_text("utf-8"))
            brief = load_brief(run_dir / "brief.json")
            return brief, run_dir, state

        assert request.workflow is not None
        if request.brief_path:
            brief = load_brief(request.brief_path)
            if request.website:
                brief.website = request.website
            if request.sector:
                brief.sector = request.sector
            if request.stage:
                brief.stage = request.stage
            if request.geography:
                brief.geography = request.geography
            if request.docs_dir:
                brief.docs_dir = request.docs_dir
        elif request.company_name:
            brief = Brief(
                company_name=request.company_name,
                website=request.website or "Unknown",
                sector=request.sector or "general",
                stage=request.stage or "unknown",
                geography=request.geography or "India",
                focus_instructions=request.focus_instructions,
                exclude_instructions=request.exclude_instructions,
            )
            if request.docs_dir:
                brief.docs_dir = request.docs_dir
        else:
            raise ValueError("Either --brief or --company must be provided.")

        if (
            request.workflow == WorkflowType.DUE_DILIGENCE
            and not brief.docs_dir
            and brief.website == "Unknown"
        ):
            self.print_fn(
                "Warning: due_diligence works better with a website or a docs directory. "
                "Without those, financial and product findings will rely on limited public evidence."
            )

        company_slug = self._slugify(brief.company_name)
        timestamp = self.now_fn().strftime("%Y-%m-%d_%H%M%S")
        run_dir = runs_root / company_slug / timestamp
        (run_dir / "findings").mkdir(parents=True, exist_ok=True)
        (run_dir / "brief.json").write_text(brief.model_dump_json(indent=2), encoding="utf-8")

        workflow = config.workflows[request.workflow.value]
        state = RunState(
            workflow=request.workflow,
            output_profile=request.output_profile,
            company_name=brief.company_name,
            pending_agents=[task.agent for task in workflow.tasks],
        )
        self._write_run_state(run_dir, state, workflow)
        return brief, run_dir, state

    def _load_project_env(self) -> None:
        project_root = self.project_root or Path(__file__).resolve().parents[2]
        env_path = project_root / ".env"
        if env_path.exists():
            load_dotenv(env_path, override=False)

    def _configure_local_crewai_environment(self, run_dir: Path) -> None:
        project_root = self.project_root or Path(__file__).resolve().parents[2]
        local_home = project_root / ".crewai-home"
        local_home.mkdir(parents=True, exist_ok=True)
        os.environ["CREWAI_STORAGE_DIR"] = project_root.name
        if sys.platform != "win32":
            xdg_data_home = project_root / ".local" / "share"
            xdg_data_home.mkdir(parents=True, exist_ok=True)
            os.environ["HOME"] = str(local_home)
            os.environ["XDG_DATA_HOME"] = str(xdg_data_home)

    def _build_specialist_prompt(
        self,
        brief: Brief,
        task: WorkflowTaskDefinition,
        config: AppConfig,
        state: RunState,
        evidence: EvidenceRegistry,
        source_profile: SourcePriorityConfig,
    ) -> str:
        spec = config.agents[task.agent]
        injected_flags = self._consume_flags_for_agent(state, task.agent)
        source_notes = "\n".join(f"- {source}" for source in source_profile.india_priority_sources)
        injected_context = ""
        if injected_flags:
            rendered_flags = "\n".join(
                f"- {flag.flag}: {flag.detail}" for flag in injected_flags
            )
            injected_context = (
                "Prior agents flagged the following for your attention:\n"
                f"{rendered_flags}\n\n"
            )

        focus_block = ""
        if brief.focus_instructions:
            focus_block = (
                "FOCUS INSTRUCTIONS (prioritize these areas):\n"
                f"- {brief.focus_instructions}\n\n"
            )

        exclude_block = ""
        if brief.exclude_instructions:
            exclude_block = (
                "EXCLUSION INSTRUCTIONS (deprioritize or skip):\n"
                f"- {brief.exclude_instructions}\n\n"
            )

        founder_signal_block = ""
        if task.agent == "founder_signal_analyst":
            founder_signal_block = (
                "Use this founder-signal fallback hierarchy and explicitly record missing signals:\n"
                + "\n".join(
                    f"- {item}"
                    for item in source_profile.founder_signal_sources
                )
                + "\n"
            )

        financial_block = ""
        if task.agent == "financial_researcher":
            financial_block = (
                "Financial diligence guidance:\n"
                "- Exact burn, runway, and contribution margin are often not public. Do not loop trying to force exact numbers.\n"
                "- If the financial_signal_search tool is available, use it early to gather a compact public-finance packet before making conclusions.\n"
                "- If uploaded docs are missing, use public proxies such as reported revenue, funding history, pricing, gross-margin hints, working-capital signals, and partner or distribution disclosures.\n"
                "- If website data is missing too, do at most 2 web searches, return the strongest public finance signal you found, and clearly list the missing diligence items.\n"
                "- A conservative final answer with explicit open questions is better than repeated searching.\n\n"
            )

        docs_block = ""
        if brief.docs_dir:
            docs_block = (
                "Uploaded diligence docs are available.\n"
                f"- Use ONLY this docs_dir when calling document tools: {brief.docs_dir}\n"
                "- Do not inspect the broader filesystem. Prefer relative filenames from that directory.\n\n"
            )

        scoring_block = ""
        if spec.scoring_dimensions:
            scoring_block = (
                "Your dimension_scores entries must use ONLY these configured dimensions:\n"
                + "\n".join(f"- {item}" for item in spec.scoring_dimensions)
                + "\n\n"
            )

        workflow_agent_ids = "\n".join(
            f"- {workflow_task.agent}" for workflow_task in config.workflows[state.workflow.value].tasks
        )
        control_agent_ids = "\n".join(
            f"- {name}" for name in ("evidence_auditor", "report_synthesizer")
        )

        prompt_notes_block = ""
        if spec.prompt_notes:
            prompt_notes_block = (
                "RESEARCH FRAMEWORK (follow this structure):\n"
                + "\n".join(f"- {note}" for note in spec.prompt_notes)
                + "\n\n"
            )

        failure_guidance_block = ""
        failure_guidance = getattr(spec, "failure_guidance", None)
        if failure_guidance:
            failure_guidance_block = (
                "IF DATA IS SPARSE (read this carefully):\n"
                f"{failure_guidance}\n\n"
            )

        return (
            f"{injected_context}"
            "--- RESEARCH PLANNING (think before you search) ---\n"
            "Before using any tools, mentally plan:\n"
            "1. What are the 3-5 most important questions to answer?\n"
            "2. What sources are most likely to have this data?\n"
            "3. What will you do if primary sources don't have the data?\n\n"
            f"You are {spec.role}.\n"
            f"Goal: {spec.goal}\n"
            f"Backstory: {spec.backstory}\n\n"
            f"Workflow: {state.workflow.value}\n"
            f"Task objective: {task.objective}\n\n"
            f"Company brief:\n"
            f"- Name: {brief.company_name}\n"
            f"- Website: {brief.website}\n"
            f"- Sector: {brief.sector}\n"
            f"- Stage: {brief.stage}\n"
            f"- Geography: {brief.geography}\n"
            f"- One-line: {brief.one_line or 'Not provided'}\n"
            f"- Thesis: {brief.investment_thesis or 'Not provided'}\n"
            f"- Notes: {brief.notes or 'Not provided'}\n\n"
            f"Prior evidence summary:\n{evidence.summary()}\n\n"
            f"{focus_block}"
            f"{exclude_block}"
            f"{prompt_notes_block}"
            f"India-first source priorities:\n{source_notes}\n\n"
            f"{docs_block}"
            f"{scoring_block}"
            f"{financial_block}"
            f"{failure_guidance_block}"
            "--- RESEARCH DISCIPLINE ---\n"
            "- INDIA FOCUS: This is an India-focused VC. The company operates in India. "
            "ALWAYS include 'India' in your search queries. Prefer Indian sources "
            "(Inc42, YourStory, Entrackr, The Ken, ET Startup, MCA, SEBI, RBI). "
            "Reference competitors in the Indian market, not US/global equivalents.\n"
            "- Use at most 6 tool calls total. Quality over quantity.\n"
            "- Prioritize: official sources > India business media > general web.\n"
            "- If a search returns nothing useful, DO NOT repeat similar queries. Move on.\n"
            "- You MUST return a final structured answer even if evidence is thin.\n"
            "- A conservative answer with explicit gaps is better than looping forever.\n"
            "- If evidence is weak or conflicting, record an open question instead of stretching the claim.\n\n"
            "--- SELF-CRITIQUE CHECKLIST (verify before submitting) ---\n"
            "Before producing your final JSON, verify:\n"
            "[ ] Every claim has a specific source (not 'various sources' or 'industry reports')\n"
            "[ ] Confidence scores reflect actual evidence (don't default everything to 0.8)\n"
            "[ ] Open questions list everything you could NOT verify\n"
            "[ ] Dimension scores use the scoring rubric, not gut feel\n"
            "[ ] No claims are merely restating the company brief\n\n"
            "When adding downstream_flags.for_agent, use ONLY these exact agent ids:\n"
            f"{workflow_agent_ids}\n{control_agent_ids}\n\n"
            f"{founder_signal_block}"
            "Use suggested_section_keys only from this allowed set:\n"
            + "\n".join(f"- {item}" for item in sorted(ALLOWED_SECTION_KEYS))
            + "\n\n"
            "Produce a structured result with cited findings, confidence scores, open questions, "
            "dimension scores where relevant, and downstream flags only when another named agent "
            "should investigate something further."
        )

    def _run_evidence_audit(
        self,
        config: AppConfig,
        llm: object,
        evidence: EvidenceRegistry,
        verbose: bool,
    ) -> AuditResult:
        deterministic = evidence.deterministic_audit()
        prompt = (
            "Audit the following evidence set for missing citations, contradictions, and gaps.\n\n"
            f"{evidence.summary(limit=20)}\n"
        )
        try:
            result = self.runner.run_agent(
                agent_name="evidence_auditor",
                spec=config.agents["evidence_auditor"],
                prompt=prompt,
                response_model=AuditResult,
                llm=llm,
                tools=[],
                verbose=verbose,
            )
            if not isinstance(result, AuditResult):
                result = AuditResult.model_validate(result.model_dump())
            result.issues.extend(deterministic.issues)
            result.gaps.extend(deterministic.gaps)
            result.passed = not result.issues
            return result
        except Exception:
            return deterministic

    def _run_report_synthesizer(
        self,
        config: AppConfig,
        llm: object,
        brief: Brief,
        state: RunState,
        evidence: EvidenceRegistry,
        audit: AuditResult,
        weights: dict[str, int],
        verbose: bool,
    ) -> FindingsBundle:
        scorecard = self._build_scorecard(
            list(state.findings.values()),
            weights,
            state.workflow,
            audit,
        )
        fallback_bundle = self._build_fallback_bundle(config, brief, state, evidence, audit, scorecard)
        prompt = (
            "Synthesize the VC diligence record into a structured findings bundle.\n\n"
            f"Company: {brief.company_name}\n"
            f"Workflow: {state.workflow.value}\n\n"
            "--- WRITING GUIDELINES ---\n"
            "Write like a senior VC analyst preparing an IC memo:\n"
            "- Lead with conclusions, then evidence\n"
            "- Use specific data points: numbers, dates, named sources\n"
            "- No marketing language ('revolutionary', 'game-changing', 'disruptive')\n"
            "- Acknowledge gaps honestly rather than padding with vague statements\n"
            "- Each section should be 100-300 words with at least 2 specific data points\n\n"
            "--- SECTION REQUIREMENTS ---\n"
            "executive_summary: 3-4 sentences. Verdict first, then 2 key evidence points, then biggest risk.\n"
            "company_snapshot: Founded when, by whom, what they do, funding to date, stage, key metrics.\n"
            "market_landscape: TAM/SAM/SOM, 3-5 competitors named, India-specific dynamics.\n"
            "financial_analysis: Revenue model, growth rate, unit economics (or proxies), burn/runway.\n"
            "product_technology: What the product does, tech differentiation, IP, engineering signals.\n"
            "founder_assessment: Founder background, domain expertise, team completeness.\n"
            "gtm_momentum: GTM motion type, traction metrics, customer acquisition evidence.\n"
            "regulatory_compliance: Applicable regulations, compliance status, risks.\n"
            "risk_register: Top 3-5 risks with probability and impact assessment.\n"
            "investment_recommendation: INVEST/PASS/CONDITIONAL with 2-3 reasons.\n\n"
            "If a section has NO real evidence from the agents, write: "
            "'Insufficient evidence. Key gap: [what is missing].'\n\n"
            f"Scorecard: {scorecard.model_dump_json(indent=2)}\n"
            f"Audit: {audit.model_dump_json(indent=2)}\n"
            f"Findings: {json.dumps({name: result.model_dump() for name, result in state.findings.items()}, indent=2)}\n"
        )
        try:
            result = self.runner.run_agent(
                agent_name="report_synthesizer",
                spec=config.agents["report_synthesizer"],
                prompt=prompt,
                response_model=FindingsBundle,
                llm=llm,
                tools=[],
                verbose=verbose,
            )
            if not isinstance(result, FindingsBundle):
                result = FindingsBundle.model_validate(result.model_dump())
            result.scorecard = scorecard
            result.citations = fallback_bundle.citations
            if not result.sections:
                result.sections = fallback_bundle.sections
            if not result.top_signals:
                result.top_signals = fallback_bundle.top_signals
            if not result.top_risks:
                result.top_risks = fallback_bundle.top_risks
            if not result.open_questions:
                result.open_questions = fallback_bundle.open_questions
            if not result.evidence_gaps:
                result.evidence_gaps = fallback_bundle.evidence_gaps
            return result
        except Exception:
            return fallback_bundle

    def _build_fallback_bundle(
        self,
        config: AppConfig,
        brief: Brief,
        state: RunState,
        evidence: EvidenceRegistry,
        audit: AuditResult,
        scorecard: ScorecardSummary,
    ) -> FindingsBundle:
        all_findings = evidence.findings()
        summaries = [result.summary for result in state.findings.values()]
        top_risks = [issue.detail for issue in audit.issues[:3]]

        all_sections = {
            "executive_summary": "\n".join(summaries[:3]) or "No executive summary available.",
            "company_snapshot": state.findings.get("startup_sourcer", None).summary
            if state.findings.get("startup_sourcer")
            else f"{brief.company_name} operates in {brief.sector} at {brief.stage} stage.",
            "market_landscape": state.findings.get("market_mapper", None).summary
            if state.findings.get("market_mapper")
            else "Market landscape not explicitly mapped.",
            "financial_analysis": state.findings.get("financial_researcher", None).summary
            if state.findings.get("financial_researcher")
            else "Financial analysis not available.",
            "product_technology": state.findings.get("product_tech_researcher", None).summary
            if state.findings.get("product_tech_researcher")
            else "Product and technology analysis not available.",
            "founder_assessment": state.findings.get("founder_signal_analyst", None).summary
            if state.findings.get("founder_signal_analyst")
            else "Founder assessment not available.",
            "gtm_momentum": state.findings.get("marketing_gtm_researcher", None).summary
            if state.findings.get("marketing_gtm_researcher")
            else "GTM analysis not available.",
            "regulatory_compliance": state.findings.get("india_regulatory_legal_analyst", None).summary
            if state.findings.get("india_regulatory_legal_analyst")
            else "Regulatory analysis not available.",
            "risk_register": state.findings.get("risk_red_team_analyst", None).summary
            if state.findings.get("risk_red_team_analyst")
            else "\n".join(top_risks) or "No risk register available.",
            "portfolio_health": state.findings.get("portfolio_monitor", None).summary
            if state.findings.get("portfolio_monitor")
            else "Portfolio health not available.",
            "support_recommendations": state.findings.get("growth_ops_analyst", None).summary
            if state.findings.get("growth_ops_analyst")
            else "Support recommendations not available.",
            "investment_recommendation": (
                f"{scorecard.recommendation} based on an overall score of "
                f"{scorecard.overall_score:.1f}/100."
            ),
            "scorecard_summary": "\n".join(
                f"- {dimension.dimension}: {dimension.score}/5"
                for dimension in scorecard.dimensions
            ),
            "top_signals": "\n".join(
                f"- {finding.claim}" for finding in all_findings[:3]
            )
            or "No signals recorded.",
            "top_risks": "\n".join(f"- {risk}" for risk in top_risks) or "No risks recorded.",
            "open_questions": "\n".join(
                f"- {question}" for question in combine_open_questions(state.findings.values())
            )
            or "No open questions recorded.",
            "evidence_gaps": "\n".join(f"- {gap}" for gap in audit.gaps) or "No evidence gaps recorded.",
            "next_steps": "Validate unresolved open questions and decide whether to proceed, pass, or monitor.",
        }

        profile_sections = config.output_profiles[state.output_profile.value].sections
        sections = {k: v for k, v in all_sections.items() if k in profile_sections}

        return FindingsBundle(
            company_name=brief.company_name,
            workflow=state.workflow,
            summary="\n".join(summaries) or "No findings were generated.",
            sections=sections,
            scorecard=scorecard,
            top_signals=[finding.claim for finding in all_findings[:3]],
            top_risks=top_risks,
            open_questions=combine_open_questions(state.findings.values()),
            evidence_gaps=audit.gaps,
            citations=[item["source_ref"] for item in evidence.unique_sources()],
        )

    def _write_standards_artifacts(
        self,
        run_dir: Path,
        assessment: object,
    ) -> tuple[Path, Path]:
        standards_path = run_dir / "report_validation.json"
        standards_path.write_text(
            assessment.model_dump_json(indent=2), encoding="utf-8"
        )
        standards_report_path = run_dir / "report_validation.md"
        standards_report = render_standards_report(assessment)
        standards_report_path.write_text(standards_report, encoding="utf-8")
        standards_html_path = run_dir / "report_validation.html"
        standards_html_path.write_text(
            markdownish_to_html_document(standards_report, "Report Standards Validation"),
            encoding="utf-8",
        )
        return standards_path, standards_html_path

    def _write_eval_artifacts(
        self,
        run_dir: Path,
        bundle: FindingsBundle,
        rubric: object,
        standards: object,
        eval_model: str,
        eval_prompt_path: Path | None,
    ) -> tuple[Path, Path, Path]:
        eval_path = run_dir / "eval_score.json"
        eval_path.write_text(rubric.model_dump_json(indent=2), encoding="utf-8")
        eval_report_path = run_dir / "eval_report.md"
        eval_report = render_eval_report(
            bundle=bundle,
            rubric=rubric,
            assessment=standards,
            eval_model=eval_model,
            prompt_path=str(eval_prompt_path) if eval_prompt_path else None,
        )
        eval_report_path.write_text(eval_report, encoding="utf-8")
        eval_report_html_path = run_dir / "eval_report.html"
        eval_report_html_path.write_text(
            markdownish_to_html_document(eval_report, f"{bundle.company_name} Eval Report"),
            encoding="utf-8",
        )
        return eval_path, eval_report_path, eval_report_html_path

    def _build_scorecard(
        self,
        results: list[AgentFindingResult],
        weights: dict[str, int],
        workflow: object,
        audit: AuditResult,
    ) -> ScorecardSummary:
        dimension_map: dict[str, list[dict[str, object]]] = {}
        for result in results:
            findings = result.findings or []
            evidence_count = len(findings)
            average_confidence = (
                sum(finding.confidence for finding in findings) / evidence_count
                if evidence_count
                else 0.55
            )
            medium_conflicts = sum(
                1 for finding in findings if finding.conflict_level.value == "medium"
            )
            high_conflicts = sum(
                1 for finding in findings if finding.conflict_level.value == "high"
            )
            conflict_ratio = (
                ((medium_conflicts * 0.5) + high_conflicts) / max(evidence_count, 1)
            )
            entry_weight = max(0.35, average_confidence) * (1 + min(evidence_count, 3) * 0.15)
            for score in result.dimension_scores:
                dimension_map.setdefault(score.dimension, []).append(
                    {
                        "score": score.score,
                        "rationale": score.rationale,
                        "weight": entry_weight,
                        "evidence_count": evidence_count,
                        "average_confidence": average_confidence,
                        "conflict_ratio": conflict_ratio,
                    }
                )

        workflow_key = getattr(workflow, "value", str(workflow))
        multipliers = WORKFLOW_DIMENSION_MULTIPLIERS.get(
            workflow_key,
            WORKFLOW_DIMENSION_MULTIPLIERS["due_diligence"],
        )
        active_weights = {
            dimension: max(0.0, weight * multipliers.get(dimension, 1.0))
            for dimension, weight in weights.items()
        }
        total_active_weight = sum(active_weights.values()) or 1.0
        normalized_weights: dict[str, int] = {}
        consumed_weight = 0
        active_dimensions = list(weights.keys())
        for index, dimension in enumerate(active_dimensions):
            if index == len(active_dimensions) - 1:
                normalized_weights[dimension] = max(0, 100 - consumed_weight)
            else:
                normalized = round((active_weights[dimension] / total_active_weight) * 100)
                normalized_weights[dimension] = normalized
                consumed_weight += normalized

        dimensions: list[ScorecardDimension] = []
        weighted_dimension_score = 0.0
        confidence_index = 0.0
        coverage_index = 0.0
        conflict_index = 0.0
        for dimension in active_dimensions:
            weight = normalized_weights[dimension]
            entries = dimension_map.get(dimension, [])
            if entries:
                total_entry_weight = sum(float(entry["weight"]) for entry in entries) or 1.0
                weighted_mean = sum(
                    int(entry["score"]) * float(entry["weight"])
                    for entry in entries
                ) / total_entry_weight
                average_confidence = sum(
                    float(entry["average_confidence"]) * float(entry["weight"])
                    for entry in entries
                ) / total_entry_weight
                conflict_ratio = sum(
                    float(entry["conflict_ratio"]) * float(entry["weight"])
                    for entry in entries
                ) / total_entry_weight
                evidence_count = sum(int(entry["evidence_count"]) for entry in entries)
                coverage_ratio = min(1.0, evidence_count / 4.0)
                support_bonus = max(0.0, coverage_ratio - 0.5) * 0.4
                confidence_penalty = max(0.0, 0.6 - average_confidence) * 1.25
                conflict_penalty = min(1.0, conflict_ratio * 1.2)
                adjusted_score = weighted_mean + support_bonus - confidence_penalty - conflict_penalty
                score_value = max(1, min(5, round(adjusted_score)))
                rationale = (
                    f"{entries[-1]['rationale']} Evidence-backed score from {len(entries)} specialist view(s), "
                    f"{evidence_count} finding(s), {average_confidence:.2f} average confidence, "
                    f"and {conflict_ratio:.2f} conflict load."
                )
            else:
                average_confidence = 0.0
                conflict_ratio = 0.0
                evidence_count = 0
                coverage_ratio = 0.0
                score_value = 2 if multipliers.get(dimension, 1.0) >= 0.8 else 3
                rationale = (
                    "No relevant specialist score supplied; dimension kept conservative "
                    "instead of using a neutral default."
                )
            dimensions.append(
                ScorecardDimension(
                    dimension=dimension,
                    weight=weight,
                    score=score_value,
                    rationale=rationale,
                    evidence_count=evidence_count,
                    average_confidence=average_confidence,
                    coverage_ratio=coverage_ratio,
                    conflict_ratio=conflict_ratio,
                )
            )
            normalized_dimension_score = ((score_value - 1) / 4.0) * 100.0
            weighted_dimension_score += normalized_dimension_score * (weight / 100.0)
            confidence_index += average_confidence * 100.0 * (weight / 100.0)
            coverage_index += coverage_ratio * 100.0 * (weight / 100.0)
            conflict_index += conflict_ratio * 100.0 * (weight / 100.0)

        high_issue_count = sum(
            1 for issue in audit.issues if issue.severity == RiskLevel.HIGH
        )
        medium_issue_count = sum(
            1 for issue in audit.issues if issue.severity == RiskLevel.MEDIUM
        )
        gap_penalty = min(
            18.0,
            (len(audit.gaps) * 2.0) + (high_issue_count * 3.0) + (medium_issue_count * 1.5),
        )
        overall = (
            weighted_dimension_score
            + ((confidence_index - 60.0) * 0.15)
            + ((coverage_index - 50.0) * 0.10)
            - (conflict_index * 0.08)
            - gap_penalty
        )
        overall = max(0.0, min(100.0, round(overall, 1)))
        if overall < 55:
            recommendation = "PASS"
        elif overall >= 75:
            recommendation = "STRONG INTEREST"
        else:
            recommendation = "CONDITIONAL"

        return ScorecardSummary(
            overall_score=overall,
            recommendation=recommendation,
            dimensions=dimensions,
            weighted_dimension_score=round(weighted_dimension_score, 1),
            confidence_index=round(confidence_index, 1),
            coverage_index=round(coverage_index, 1),
            conflict_index=round(conflict_index, 1),
            gap_penalty=round(gap_penalty, 1),
        )

    def _handle_checkpoint(
        self,
        agent_name: str,
        summary: str,
        approve_mode: ApproveMode,
    ) -> ApprovalAction:
        if approve_mode == ApproveMode.AUTO:
            return ApprovalAction.APPROVE
        self.print_fn(f"Checkpoint reached after {agent_name}.\n{summary}\n")
        while True:
            response = self.prompt_fn("[APPROVE / SKIP / ABORT]: ").strip().lower()
            if response in {"approve", "a"}:
                return ApprovalAction.APPROVE
            if response in {"skip", "s"}:
                return ApprovalAction.SKIP
            if response in {"abort", "q"}:
                return ApprovalAction.ABORT
            self.print_fn("Please choose APPROVE, SKIP, or ABORT.")

    def _persist_agent_result(self, run_dir: Path, result: AgentFindingResult) -> None:
        findings_dir = run_dir / "findings"
        findings_dir.mkdir(parents=True, exist_ok=True)
        finding_path = findings_dir / f"{result.agent_name}.json"
        finding_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")

    def _build_failed_agent_result(
        self,
        agent_name: str,
        spec: object,
        error: Exception,
    ) -> AgentFindingResult:
        role = getattr(spec, "role", agent_name)
        return AgentFindingResult(
            agent_name=agent_name,
            summary=(
                f"{role} did not complete successfully after repeated attempts. "
                "Treat this workstream as unresolved."
            ),
            findings=[],
            open_questions=[
                f"{role} could not finish automatically. Revisit this workstream manually. Error: {error}"
            ],
            dimension_scores=[],
            downstream_flags=[],
            sources_checked=[],
            suggested_section_keys=[],
        )

    def _normalize_agent_result(
        self,
        result: AgentFindingResult,
        agent_key: str,
        spec: object,
        config: AppConfig,
    ) -> AgentFindingResult:
        allowed_agents = set(config.agents)
        allowed_dimensions = set(getattr(spec, "scoring_dimensions", []))
        normalized_flags = [
            flag
            for flag in result.downstream_flags
            if flag.for_agent in allowed_agents
        ]
        normalized_scores = [
            score
            for score in result.dimension_scores
            if not allowed_dimensions or score.dimension in allowed_dimensions
        ]
        normalized_sections = [
            section_key
            for section_key in result.suggested_section_keys
            if section_key in ALLOWED_SECTION_KEYS
        ]
        normalized_sources = []
        seen_sources: set[tuple[str, str]] = set()
        for source in result.sources_checked:
            source_key = (source.source_name, source.source_type)
            if source_key in seen_sources:
                continue
            seen_sources.add(source_key)
            normalized_sources.append(source)

        payload = result.model_dump()
        payload["agent_name"] = agent_key
        payload["downstream_flags"] = [flag.model_dump() for flag in normalized_flags]
        payload["dimension_scores"] = [score.model_dump() for score in normalized_scores]
        payload["suggested_section_keys"] = normalized_sections
        payload["sources_checked"] = [source.model_dump() for source in normalized_sources]
        return AgentFindingResult.model_validate(payload)

    def _write_run_state(
        self,
        run_dir: Path,
        state: RunState,
        workflow: object | None = None,
    ) -> None:
        state.last_updated = self.now_fn()
        (run_dir / "run_state.json").write_text(
            state.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def _consume_flags_for_agent(self, state: RunState, agent_name: str):
        matching = [flag for flag in state.pending_flags if flag.for_agent == agent_name]
        state.pending_flags = [
            flag for flag in state.pending_flags if flag.for_agent != agent_name
        ]
        return matching

    def _remaining_agents(
        self,
        workflow_tasks: list[WorkflowTaskDefinition],
        state: RunState,
    ) -> list[str]:
        completed = {entry.agent_name for entry in state.completed_agents}
        return [task.agent for task in workflow_tasks if task.agent not in completed]

    def _update_latest_symlink(self, run_dir: Path) -> None:
        latest_link = run_dir.parent / "latest"
        try:
            if latest_link.exists() or latest_link.is_symlink():
                latest_link.unlink()
            latest_link.symlink_to(run_dir.name)
        except OSError:
            self.print_fn(
                f"Warning: Could not create 'latest' symlink at {latest_link}. "
                "On Windows, symlinks may require developer mode or admin privileges."
            )

    @staticmethod
    def _slugify(value: str) -> str:
        return "".join(ch.lower() if ch.isalnum() else "-" for ch in value).strip("-")
