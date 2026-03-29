from __future__ import annotations

from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from my_agents.main import run
from my_agents.schemas import (
    AgentFindingResult,
    AuditResult,
    FindingRecord,
    FindingsBundle,
    ScorecardSummary,
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
                scorecard=ScorecardSummary(
                    overall_score=75.0, recommendation="Investigate"
                ),
                top_signals=["Strong category pull"],
                top_risks=["Channel concentration"],
                citations=["brief://company"],
            )
        raise AssertionError(f"Unexpected response model: {response_model}")


class E2ESmokeTests(unittest.TestCase):
    def test_cli_quick_mode_e2e_smoke(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)

            with patch(
                "my_agents.controller.CrewAIAgentRunner", return_value=FakeRunner()
            ):
                with patch(
                    "my_agents.controller.VCResearchController._load_project_env"
                ):
                    with patch("my_agents.controller.build_llm", return_value=object()):
                        with patch(
                            "my_agents.main.VCResearchController"
                        ) as MockController:
                            # We'll just patch VCResearchController so it doesn't actually run,
                            # or we can let it run with FakeRunner.
                            # Let's let it run with FakeRunner to ensure it completes!
                            pass

            # Actually, let's just directly mock the runner and run the real controller.
            with patch(
                "my_agents.controller.CrewAIAgentRunner", return_value=FakeRunner()
            ):
                with patch(
                    "my_agents.controller.VCResearchController._load_project_env"
                ):
                    with patch("my_agents.controller.build_llm", return_value=object()):
                        # We also need to mock project_root inside VCResearchController
                        with patch(
                            "my_agents.controller.VCResearchController.__init__",
                            lambda self, runner=None, prompt_fn=None, print_fn=None, now_fn=None, project_root_arg=None: (
                                setattr(self, "runner", FakeRunner())
                                or setattr(self, "prompt_fn", input)
                                or setattr(self, "print_fn", print)
                                or setattr(
                                    self, "now_fn", __import__("datetime").datetime.now
                                )
                                or setattr(self, "project_root", project_root)
                            ),
                        ):
                            run(
                                [
                                    "--company",
                                    "SmokeTestCorp",
                                    "--focus",
                                    "E2E testing",
                                    "--verbose",
                                ]
                            )

            # Verify the run directory was created
            runs_root = project_root / "runs"
            self.assertTrue(runs_root.exists())
            company_dirs = list(runs_root.iterdir())
            self.assertEqual(len(company_dirs), 1)
            self.assertEqual(company_dirs[0].name, "smoketestcorp")

            run_dirs = [d for d in company_dirs[0].iterdir() if d.name != "latest"]
            self.assertEqual(len(run_dirs), 1)
            run_dir = run_dirs[0]

            self.assertTrue((run_dir / "report.md").exists())
            self.assertTrue((run_dir / "execution.log").exists())


if __name__ == "__main__":
    unittest.main()
