from __future__ import annotations

import unittest

from my_agents.configuration import (
    DEFAULT_CONFIG_DIR,
    canonicalize_profile_key,
    load_app_config,
)


class ConfigurationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_app_config(DEFAULT_CONFIG_DIR)

    def test_sector_aliases_resolve_to_expected_profiles(self) -> None:
        self.assertEqual(canonicalize_profile_key("D2C Brands"), "d2c")
        self.assertEqual(canonicalize_profile_key("healthcare"), "healthtech")
        self.assertEqual(canonicalize_profile_key("deep-tech"), "deeptech")
        self.assertEqual(canonicalize_profile_key("marketplace"), "marketplaces")
        self.assertEqual(canonicalize_profile_key("cyber security"), "cybersecurity")

    def test_d2c_overlay_weights_are_selected(self) -> None:
        weights = self.config.resolve_score_weights("consumer brands")
        self.assertEqual(weights["gtm_traction_and_momentum"], 22)
        self.assertEqual(sum(weights.values()), 100)

    def test_healthcare_overlay_sources_are_selected(self) -> None:
        profile = self.config.resolve_source_profile("healthcare")
        joined = " ".join(profile.india_priority_sources)
        self.assertIn("ABDM", joined)
        self.assertEqual(profile.profile, "healthtech")

    def test_marketplace_profile_override_uses_alias(self) -> None:
        profile = self.config.resolve_source_profile("consumer", "marketplace")
        joined = " ".join(profile.india_priority_sources)
        self.assertIn("ONDC", joined)

    def test_all_scorecards_sum_to_one_hundred(self) -> None:
        for sector in self.config.scorecard_overlays:
            with self.subTest(sector=sector):
                self.assertEqual(
                    sum(self.config.resolve_score_weights(sector).values()), 100
                )


if __name__ == "__main__":
    unittest.main()
