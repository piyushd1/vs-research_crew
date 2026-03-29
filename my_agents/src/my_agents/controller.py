from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
import os
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv

from my_agents.configuration import DEFAULT_CONFIG_DIR, AppConfig, load_app_config, load_brief
from my_agents.evidence import EvidenceRegistry, combine_open_questions
from my_agents.integrations.linear_push import push_linear_issue
from my_agents.llm_policy import build_llm
from my_agents.pdf_export import export_pdf
from my_agents.renderers import render_full_report, render_ic_memo, render_one_pager
from my_agents.runner import AgentRunner, CrewAIAgentRunner
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
    RunArtifacts,
    RunRequest,
    RunState,
    ScorecardDimension,
    ScorecardSummary,
    SourcePriorityConfig,
    WorkflowTaskDefinition,
)
from my_agents.tools import build_tools


class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        data = {
            "timestamp": self.formatTime(record, self.datefmt),
            "level": record.levelname,
            "message": record.getMessage(),
            "name": record.name,
        }
        if hasattr(record, "step"):
            data["step"] = getattr(record, "step")
        if hasattr(record, "agent"):
            data["agent"] = getattr(record, "agent")
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
            
            from my_agents.schemas import FindingsBundle, Brief
            bundle = FindingsBundle.model_validate_json(bundle_path.read_text(encoding="utf-8"))
            brief = Brief(company_name=bundle.company_name, sector="general", geography="India")
            
            self.print_fn(f"\nEvaluating existing run: {run_dir}")
            from my_agents.evals.judge import evaluate_run
            try:
                rubric = evaluate_run(brief, bundle, config, runner=self.runner, verbose=request.verbose)
                eval_path = run_dir / "eval_score.json"
                eval_path.write_text(rubric.model_dump_json(indent=2), encoding="utf-8")
                self.print_fn(f"Evaluation Complete! Score: {rubric.final_eval_score}/100")
                self.print_fn(f"Feedback: {rubric.summary_feedback}")
            except Exception as ev_exc:
                self.print_fn(f"Warning: Evals skipped due to error: {ev_exc}")
                
            return RunArtifacts(
                run_dir=run_dir,
                report_path=run_dir / "report.md",
                scorecard_path=run_dir / "scorecard.json",
                sources_path=run_dir / "sources.json",
                run_state_path=run_dir / "run_state.json",
                bundle_path=bundle_path,
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
            tools = build_tools(brief, source_profile, task.agent)
            self._write_run_state(run_dir, state, workflow)
            
            logger.info(f"Starting agent: {task.agent}", extra={"step": "agent_start", "agent": task.agent})
            self.print_fn(f"\n[bold green]Starting Agent: {task.agent}[/]")
            
            result = self.runner.run_agent(
                agent_name=task.agent,
                spec=config.agents[task.agent],
                prompt=prompt,
                response_model=AgentFindingResult,
                llm=llm,
                tools=tools,
                verbose=request.verbose,
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
        one_pager_path: Path | None = None
        pdf_path: Path | None = None

        if selected_profile == OutputProfile.IC_MEMO:
            report_text = render_ic_memo(bundle)
            report_path.write_text(report_text, encoding="utf-8")
            candidate_pdf_path = run_dir / "report.pdf"
            try:
                export_pdf(report_text, candidate_pdf_path, f"{brief.company_name} IC Memo")
                pdf_path = candidate_pdf_path
            except Exception as exc:
                self.print_fn(f"Warning: PDF export skipped due to error: {exc}")
        elif selected_profile == OutputProfile.FULL_REPORT:
            report_text = render_full_report(bundle)
            report_path.write_text(report_text, encoding="utf-8")
            candidate_pdf_path = run_dir / "report.pdf"
            try:
                export_pdf(report_text, candidate_pdf_path, f"{brief.company_name} Full Report")
                pdf_path = candidate_pdf_path
            except Exception as exc:
                self.print_fn(f"Warning: PDF export skipped due to error: {exc}")
        else:
            report_text = render_ic_memo(bundle)
            report_path.write_text(report_text, encoding="utf-8")
            one_pager_path = run_dir / "one_pager.html"
            one_pager_path.write_text(render_one_pager(bundle), encoding="utf-8")

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
            
        if request.run_evals:
            self.print_fn("\nRunning VC Evaluation Judge...")
            logger.info("Starting subjective evaluations", extra={"step": "evaluate"})
            from my_agents.evals.judge import evaluate_run
            try:
                rubric = evaluate_run(brief, bundle, config, runner=self.runner, verbose=request.verbose)
                eval_path = run_dir / "eval_score.json"
                eval_path.write_text(rubric.model_dump_json(indent=2), encoding="utf-8")
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
                sector=request.sector if getattr(request, 'sector', None) is not None else "general",
                stage=request.stage if getattr(request, 'stage', None) is not None else "unknown",
                geography=request.geography if getattr(request, 'geography', None) is not None else "India",
                focus_instructions=request.focus_instructions,
                exclude_instructions=request.exclude_instructions,
            )
            if request.docs_dir:
                brief.docs_dir = request.docs_dir
        else:
            raise ValueError("Either --brief or --company must be provided.")

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

        return (
            f"{injected_context}"
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
            f"India-first source priorities:\n{source_notes}\n\n"
            f"{docs_block}"
            "When adding downstream_flags.for_agent, use ONLY these exact agent ids:\n"
            f"{workflow_agent_ids}\n{control_agent_ids}\n\n"
            f"{scoring_block}"
            "Use suggested_section_keys only from this allowed set:\n"
            + "\n".join(f"- {item}" for item in sorted(ALLOWED_SECTION_KEYS))
            + "\n\n"
            f"{founder_signal_block}"
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
        scorecard = self._build_scorecard(list(state.findings.values()), weights)
        fallback_bundle = self._build_fallback_bundle(config, brief, state, evidence, audit, scorecard)
        prompt = (
            "Synthesize the VC diligence record into a structured findings bundle.\n\n"
            f"Company: {brief.company_name}\n"
            f"Workflow: {state.workflow.value}\n"
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

    def _build_scorecard(
        self,
        results: list[AgentFindingResult],
        weights: dict[str, int],
    ) -> ScorecardSummary:
        dimension_map: dict[str, list[tuple[int, str]]] = {}
        for result in results:
            for score in result.dimension_scores:
                dimension_map.setdefault(score.dimension, []).append(
                    (score.score, score.rationale)
                )

        dimensions: list[ScorecardDimension] = []
        weighted_total = 0.0
        for dimension, weight in weights.items():
            entries = dimension_map.get(dimension, [])
            if entries:
                average = round(sum(value for value, _ in entries) / len(entries))
                rationale = entries[-1][1]
            else:
                average = 3
                rationale = "No specialist score supplied; using neutral baseline."
            dimensions.append(
                ScorecardDimension(
                    dimension=dimension,
                    weight=weight,
                    score=average,
                    rationale=rationale,
                )
            )
            weighted_total += average * weight

        overall = (weighted_total / 100.0) * 20.0
        if overall < 50:
            recommendation = "PASS"
        elif overall > 75:
            recommendation = "STRONG INTEREST"
        else:
            recommendation = "CONDITIONAL"

        return ScorecardSummary(
            overall_score=overall,
            recommendation=recommendation,
            dimensions=dimensions,
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
