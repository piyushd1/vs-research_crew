from __future__ import annotations

import unittest
from my_agents.schemas import FindingsBundle, ScorecardSummary, ScorecardDimension, WorkflowType
from my_agents.renderers.ic_memo_renderer import render_ic_memo
from my_agents.renderers.one_pager_renderer import render_one_pager
from my_agents.renderers.full_report_renderer import render_full_report

class RendererTests(unittest.TestCase):
    def setUp(self) -> None:
        self.bundle = FindingsBundle(
            company_name="TestCorp",
            workflow=WorkflowType.DUE_DILIGENCE,
            summary="Default summary",
            sections={
                "executive_summary": "Exec summary text",
                "market_landscape": "Market is good",
                "portfolio_health": "Very healthy",
                "founder_assessment": "Strong team",
            },
            scorecard=ScorecardSummary(
                overall_score=85.0,
                recommendation="Invest",
                dimensions=[
                    ScorecardDimension(dimension="Team", weight=50, score=4, rationale="Great"),
                    ScorecardDimension(dimension="Market", weight=50, score=5, rationale="Huge"),
                ]
            ),
            top_signals=["Signal 1", "Signal 2"],
            top_risks=["Risk 1"],
            open_questions=["Question 1"],
            evidence_gaps=["Gap 1"]
        )

    def test_ic_memo_renderer_includes_optional_sections(self) -> None:
        rendered = render_ic_memo(self.bundle)
        self.assertIn("## Market Landscape", rendered)
        self.assertIn("Market is good", rendered)
        self.assertIn("## Portfolio Health", rendered)
        self.assertIn("Very healthy", rendered)
        self.assertIn("## Founder Assessment", rendered)
        self.assertIn("Strong team", rendered)
        self.assertIn("Signal 1", rendered)
        self.assertIn("Risk 1", rendered)

    def test_one_pager_renderer_includes_optional_sections(self) -> None:
        rendered = render_one_pager(self.bundle)
        self.assertIn("<h2>Market Landscape</h2>", rendered)
        self.assertIn("<p>Market is good</p>", rendered)
        self.assertIn("<h2>Portfolio Health</h2>", rendered)
        self.assertIn("<p>Very healthy</p>", rendered)
        self.assertIn("<h2>Founder Assessment</h2>", rendered)
        self.assertIn("<p>Strong team</p>", rendered)
        self.assertIn("TestCorp One Pager", rendered)

    def test_full_report_renderer_includes_optional_sections(self) -> None:
        rendered = render_full_report(self.bundle)
        self.assertIn("## Executive Summary", rendered)
        self.assertIn("## Market Landscape", rendered)
        self.assertIn("Market is good", rendered)
        self.assertIn("## Portfolio Health", rendered)
        self.assertIn("Very healthy", rendered)

if __name__ == "__main__":
    unittest.main()
