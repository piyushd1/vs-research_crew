from __future__ import annotations

import unittest

from my_agents.configuration import (
    DEFAULT_CONFIG_DIR,
    SECTOR_PROFILE_ALIASES,
    canonicalize_profile_key,
    load_app_config,
)
from my_agents.tools.custom_tool import SECTOR_SOURCE_HINTS


class SectorCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.config = load_app_config(DEFAULT_CONFIG_DIR)

    def test_new_aliases_resolve_correctly(self) -> None:
        cases = [
            ("lending", "fintech"),
            ("bnpl", "fintech"),
            ("neo banking", "fintech"),
            ("micro_lending", "fintech"),
            ("regtech", "fintech"),
            ("supply chain finance", "fintech"),
            ("gaming", "consumer"),
            ("media", "consumer"),
            ("ott", "consumer"),
            ("streaming", "consumer"),
            ("travel", "consumer"),
            ("food delivery", "consumer"),
            ("cloud kitchen", "consumer"),
            ("hospitality", "consumer"),
            ("hr tech", "saas_ai"),
            ("hrtech", "saas_ai"),
            ("legal tech", "saas_ai"),
            ("adtech", "saas_ai"),
            ("recruitment", "saas_ai"),
            ("biotech", "deeptech"),
            ("drone", "deeptech"),
            ("uav", "deeptech"),
            ("clean energy", "climate"),
            ("solar", "climate"),
            ("ev charging", "climate"),
            ("waste management", "climate"),
            ("recycling", "climate"),
            ("beauty", "d2c"),
            ("skincare", "d2c"),
            ("personal care", "d2c"),
            ("pet care", "d2c"),
            ("grocery", "d2c"),
            ("quick commerce", "d2c"),
            ("ride hailing", "logistics"),
            ("ride sharing", "logistics"),
        ]
        for alias_input, expected in cases:
            with self.subTest(alias_input=alias_input):
                self.assertEqual(canonicalize_profile_key(alias_input), expected)

    def test_unknown_sector_falls_back_gracefully(self) -> None:
        result = canonicalize_profile_key("quantum_computing_startups")
        self.assertEqual(result, "quantum_computing_startups")

        profile = self.config.resolve_source_profile("quantum_computing_startups")
        self.assertEqual(profile.profile, "base")
        self.assertTrue(len(profile.india_priority_sources) > 0)

    def test_source_hints_exist_for_all_canonical_sectors(self) -> None:
        canonical_sectors = set(SECTOR_PROFILE_ALIASES.values())
        for sector in canonical_sectors:
            with self.subTest(sector=sector):
                hints = SECTOR_SOURCE_HINTS.get(sector, SECTOR_SOURCE_HINTS.get("generic", []))
                self.assertTrue(
                    len(hints) > 0,
                    f"No source hints found for canonical sector '{sector}'",
                )

    def test_generic_fallback_has_hints(self) -> None:
        self.assertIn("generic", SECTOR_SOURCE_HINTS)
        self.assertTrue(len(SECTOR_SOURCE_HINTS["generic"]) >= 3)

    def test_all_alias_values_are_valid_canonical_sectors(self) -> None:
        valid_sectors = {
            "agritech", "climate", "consumer", "cybersecurity", "d2c",
            "deeptech", "edtech", "fintech", "healthtech", "logistics",
            "marketplaces", "proptech", "saas_ai",
        }
        for alias, canonical in SECTOR_PROFILE_ALIASES.items():
            with self.subTest(alias=alias):
                self.assertIn(
                    canonical,
                    valid_sectors,
                    f"Alias '{alias}' maps to unknown canonical sector '{canonical}'",
                )


if __name__ == "__main__":
    unittest.main()
