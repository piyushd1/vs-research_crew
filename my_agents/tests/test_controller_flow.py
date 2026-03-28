from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from my_agents.controller import VCResearchController
from my_agents.schemas import (
    AgentFindingResult,
    ApproveMode,
    AuditResult,
    FindingRecord,
    FindingsBundle,
    OutputProfile,
    RunRequest,
    ScorecardSummary,
    RunState,
    WorkflowType,
)


class FakeRunner:
    def __init__(self, fail_on_agent: str | None = None):
        self.fail_on_agent = fail_on_agent

    def run_agent(
        self,
        agent_name: str,
        spec,
        prompt: str,
        response_model,
        llm,
        tools,
        verbose: bool = False,
    ):
        if self.fail_on_agent == agent_name:
            raise RuntimeError(f"Simulated failure in {agent_name}")

        if response_model is AgentFindingResult:
            return AgentFindingResult(
                agent_name=agent_name,
                summary=f"{agent_name} completed review",
                findings=[
                    FindingRecord(
                        claim=f"{agent_name} identified a useful signal",
                        evidence_summary="Grounded in the brief and deterministic test fixture.",
                        source_ref="brief://company",
                        source_type="uploaded_private",
                        confidence=0.8,
                    )
                ],
                suggested_section_keys=["company_snapshot", "top_signals"],
            )
        if response_model is AuditResult:
            return AuditResult(passed=True, issues=[], gaps=[])
        if response_model is FindingsBundle:
            return FindingsBundle(
                company_name="Test D2C Brand",
                workflow=WorkflowType.SOURCING,
                summary="Synthesized summary",
                sections={
                    "executive_summary": "Summary",
                    "company_snapshot": "Snapshot",
                    "top_signals": "Signals",
                    "top_risks": "Risks",
                    "open_questions": "Questions",
                    "next_steps": "Next steps",
                },
                scorecard=ScorecardSummary(overall_score=75.0, recommendation="Investigate"),
                top_signals=["Strong category pull"],
                top_risks=["Channel concentration"],
                citations=["brief://company"],
            )
        raise AssertionError(f"Unexpected response model: {response_model}")


class ControllerFlowTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = tempfile.TemporaryDirectory()
        self.project_root = Path(self.temp_dir.name)
        self.brief_path = self.project_root / "brief.yaml"
        self.brief_path.write_text(
            "\n".join(
                [
                    "company_name: Test Company",
                    "website: https://example.com",
                    "sector: saas",
                    "stage: series_a",
                    "geography: India",
                    "one_line: Test company.",
                ]
            ),
            encoding="utf-8",
        )

    def tearDown(self) -> None:
        self.temp_dir.cleanup()

    def run_workflow_profile_test(self, workflow: WorkflowType, profile: OutputProfile) -> None:
        controller = VCResearchController(
            runner=FakeRunner(),
            project_root=self.project_root,
        )
        request = RunRequest(
            workflow=workflow,
            brief_path=self.brief_path,
            output_profile=profile,
            approve_mode=ApproveMode.AUTO,
        )
        with patch("my_agents.controller.build_llm", return_value=object()):
            artifacts = controller.run(request)

        self.assertTrue(artifacts.report_path.exists())
        state = json.loads(artifacts.run_state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["workflow"], workflow.value)

        # Check expected outputs
        if profile == OutputProfile.ONE_PAGER:
            self.assertTrue(artifacts.one_pager_path is not None and artifacts.one_pager_path.exists())
        else:
            self.assertTrue(artifacts.pdf_path is None or artifacts.pdf_path.exists())  # PDF can fail but shouldn't crash
            
    # Matrix tests: 3 workflows X 3 profiles
    def test_sourcing_ic_memo(self) -> None:
        self.run_workflow_profile_test(WorkflowType.SOURCING, OutputProfile.IC_MEMO)

    def test_sourcing_full_report(self) -> None:
        self.run_workflow_profile_test(WorkflowType.SOURCING, OutputProfile.FULL_REPORT)

    def test_sourcing_one_pager(self) -> None:
        self.run_workflow_profile_test(WorkflowType.SOURCING, OutputProfile.ONE_PAGER)

    def test_due_diligence_ic_memo(self) -> None:
        self.run_workflow_profile_test(WorkflowType.DUE_DILIGENCE, OutputProfile.IC_MEMO)

    def test_due_diligence_full_report(self) -> None:
        self.run_workflow_profile_test(WorkflowType.DUE_DILIGENCE, OutputProfile.FULL_REPORT)

    def test_due_diligence_one_pager(self) -> None:
        self.run_workflow_profile_test(WorkflowType.DUE_DILIGENCE, OutputProfile.ONE_PAGER)

    def test_portfolio_ic_memo(self) -> None:
        self.run_workflow_profile_test(WorkflowType.PORTFOLIO, OutputProfile.IC_MEMO)

    def test_portfolio_full_report(self) -> None:
        self.run_workflow_profile_test(WorkflowType.PORTFOLIO, OutputProfile.FULL_REPORT)

    def test_portfolio_one_pager(self) -> None:
        self.run_workflow_profile_test(WorkflowType.PORTFOLIO, OutputProfile.ONE_PAGER)

    def test_quick_mode_flow(self) -> None:
        controller = VCResearchController(
            runner=FakeRunner(),
            project_root=self.project_root,
        )
        request = RunRequest(
            company_name="QuickModeCorp",
            focus_instructions="Focus on API limits",
            exclude_instructions="Ignore marketing setup",
            approve_mode=ApproveMode.AUTO,
        )
        with patch("my_agents.controller.build_llm", return_value=object()):
            artifacts = controller.run(request)
        self.assertTrue(artifacts.report_path.exists())
        state = json.loads(artifacts.run_state_path.read_text(encoding="utf-8"))
        self.assertEqual(state["company_name"], "QuickModeCorp")
        self.assertIn("QuickModeCorp", artifacts.run_state_path.read_text(encoding="utf-8"))

    def test_resume_from_failed_state(self) -> None:
        controller1 = VCResearchController(
            runner=FakeRunner(fail_on_agent="founder_signal_analyst"),
            project_root=self.project_root,
        )
        request1 = RunRequest(
            workflow=WorkflowType.SOURCING,
            company_name="ResumeCo",
            approve_mode=ApproveMode.AUTO,
        )
        
        with patch("my_agents.controller.build_llm", return_value=object()):
            with self.assertRaisesRegex(RuntimeError, "Simulated failure in founder_signal_analyst"):
                controller1.run(request1)
                
        # Find the run_dir
        runs_dir = self.project_root / "runs" / "resumeco"
        subdirs = list(runs_dir.iterdir())
        self.assertEqual(len(subdirs), 1)
        run_dir = subdirs[0]
        
        state1 = RunState.model_validate_json((run_dir / "run_state.json").read_text("utf-8"))
        self.assertIn("founder_signal_analyst", state1.pending_agents)
        
        # Now resume
        controller2 = VCResearchController(
            runner=FakeRunner(),  # No failure this time
            project_root=self.project_root,
        )
        request2 = RunRequest(resume=run_dir, approve_mode=ApproveMode.AUTO)
        
        with patch("my_agents.controller.build_llm", return_value=object()):
            artifacts = controller2.run(request2)
            
        self.assertTrue(artifacts.report_path.exists())
        state2 = RunState.model_validate_json(artifacts.run_state_path.read_text("utf-8"))
        self.assertEqual(len(state2.pending_agents), 0)


if __name__ == "__main__":
    unittest.main()
