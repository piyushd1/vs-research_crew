from __future__ import annotations

import unittest

from my_agents.report_standards import assess_report_standards
from my_agents.schemas import FindingsBundle, OutputProfile, ScorecardSummary, WorkflowType


class ReportStandardsTests(unittest.TestCase):
    def test_assessment_flags_short_memo_with_missing_sections(self) -> None:
        bundle = FindingsBundle(
            company_name="ShortMemoCo",
            workflow=WorkflowType.SOURCING,
            summary="Short summary",
            sections={
                "executive_summary": "Very short summary only.",
                "top_signals": "Signal text",
            },
            scorecard=ScorecardSummary(overall_score=55.0, recommendation="CONDITIONAL"),
            citations=["https://example.com/1"],
        )
        assessment = assess_report_standards(
            bundle=bundle,
            workflow=WorkflowType.SOURCING,
            output_profile=OutputProfile.IC_MEMO,
            rendered_output="Too short.",
            required_sections=[
                "executive_summary",
                "investment_recommendation",
                "scorecard_summary",
                "top_signals",
                "top_risks",
                "open_questions",
            ],
        )
        self.assertEqual(assessment.length_status.value, "too_short")
        self.assertIn("investment_recommendation", assessment.missing_sections)
        self.assertGreater(len(assessment.notes), 0)


if __name__ == "__main__":
    unittest.main()
