from __future__ import annotations

import unittest

from my_agents.configuration import DEFAULT_CONFIG_DIR, load_app_config
from my_agents.controller import VCResearchController
from my_agents.schemas import (
    AgentFindingResult,
    DimensionScore,
    DownstreamFlag,
    FindingRecord,
    RiskLevel,
    SourceAccessRecord,
)


class ControllerNormalizationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_app_config(DEFAULT_CONFIG_DIR)
        cls.controller = VCResearchController()

    def test_normalization_clamps_agent_fields_to_config(self) -> None:
        result = AgentFindingResult(
            agent_name="Startup Sourcer",
            summary="Summary",
            findings=[
                FindingRecord(
                    claim="Test claim",
                    evidence_summary="Evidence",
                    source_ref="https://example.com",
                    source_type="public_web",
                    confidence=0.7,
                    risk_level=RiskLevel.MEDIUM,
                )
            ],
            dimension_scores=[
                DimensionScore(
                    dimension="market_size_and_growth",
                    score=4,
                    rationale="Valid score",
                ),
                DimensionScore(
                    dimension="invented_dimension",
                    score=1,
                    rationale="Should be removed",
                ),
            ],
            downstream_flags=[
                DownstreamFlag(
                    flag="good_follow_up",
                    for_agent="thesis_fit_analyst",
                    detail="Relevant follow-up",
                ),
                DownstreamFlag(
                    flag="bad_follow_up",
                    for_agent="invented_agent",
                    detail="Should be removed",
                ),
            ],
            sources_checked=[
                SourceAccessRecord(
                    source_name="MCA / ROC",
                    source_type="mca",
                    accessed=True,
                ),
                SourceAccessRecord(
                    source_name="MCA / ROC",
                    source_type="mca",
                    accessed=True,
                ),
            ],
            suggested_section_keys=["company_snapshot", "made_up_section"],
        )

        normalized = self.controller._normalize_agent_result(
            result=result,
            agent_key="startup_sourcer",
            spec=self.config.agents["startup_sourcer"],
            config=self.config,
        )

        self.assertEqual(normalized.agent_name, "startup_sourcer")
        self.assertEqual(
            [item.for_agent for item in normalized.downstream_flags],
            ["thesis_fit_analyst"],
        )
        self.assertEqual(
            [item.dimension for item in normalized.dimension_scores],
            ["market_size_and_growth"],
        )
        self.assertEqual(normalized.suggested_section_keys, ["company_snapshot"])
        self.assertEqual(len(normalized.sources_checked), 1)


if __name__ == "__main__":
    unittest.main()
