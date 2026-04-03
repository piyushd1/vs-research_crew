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
    VCRubric,
    WorkflowType,
)


class FakeRunnerForEvals:
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
                },
                scorecard=ScorecardSummary(overall_score=75.0, recommendation="Investigate"),
            )
        if response_model is VCRubric:
            return VCRubric(
                relevance_score=9,
                tone_score=8,
                citation_quality_score=9,
                structure_score=9,
                length_fit_score=8,
                evidence_strength_score=9,
                hallucinations=[],
                negative_constraint_violations=[],
                improvement_actions=["Tighten evidence traceability."],
                final_eval_score=0,
                summary_feedback="Strong evaluation metrics without hallucinations.",
            )
        raise AssertionError(f"Unexpected response model: {response_model}")


class EvalBenchmarkTests(unittest.TestCase):
    def test_cli_runs_eval_and_generates_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            project_root = Path(tmp_dir)
            with patch(
                "my_agents.controller.VCResearchController.__init__",
                lambda self, runner=None, prompt_fn=None, print_fn=None, now_fn=None, project_root_arg=None: setattr(
                    self, "runner", FakeRunnerForEvals()
                )
                or setattr(self, "prompt_fn", input)
                or setattr(self, "print_fn", print)
                or setattr(self, "now_fn", __import__("datetime").datetime.now)
                or setattr(self, "project_root", project_root),
            ):
                with patch("my_agents.controller.VCResearchController._load_project_env"):
                    with patch("my_agents.controller.build_llm", return_value=object()):
                        with patch("my_agents.llm_policy.build_eval_llm", return_value=object()):
                            with patch("logging.FileHandler") as mock_fh:
                                mock_fh.return_value.level = 0
                                run(
                                    [
                                        "--company",
                                        "EvalTestCorp",
                                        "--focus",
                                        "E2E testing",
                                        "--run-evals",
                                    ]
                                )

            # Verify the run directory was created and eval json exists
            runs_root = project_root / "runs"
            self.assertTrue(runs_root.exists())
            company_dirs = list(runs_root.iterdir())
            self.assertEqual(len(company_dirs), 1)

            run_dirs = [d for d in company_dirs[0].iterdir() if d.name != "latest"]
            self.assertEqual(len(run_dirs), 1)
            run_dir = run_dirs[0]

            self.assertTrue((run_dir / "eval_score.json").exists())
            self.assertTrue((run_dir / "eval_report.md").exists())
            self.assertTrue((run_dir / "eval_report.html").exists())
            self.assertTrue((run_dir / "eval_prompt.txt").exists())
            eval_data = VCRubric.model_validate_json((run_dir / "eval_score.json").read_text())
            self.assertEqual(eval_data.final_eval_score, 84)


if __name__ == "__main__":
    unittest.main()
