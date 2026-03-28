from __future__ import annotations

import unittest
from pathlib import Path

from my_agents.schemas import Brief, RunRequest


class QuickModeTests(unittest.TestCase):
    def test_run_request_validates_with_only_company_name(self) -> None:
        # User only gives --company
        req = RunRequest(company_name="Razorpay")
        self.assertEqual(req.company_name, "Razorpay")
        self.assertIsNone(req.brief_path)
        # Default workflow is SOURCING
        self.assertEqual(req.workflow.value, "sourcing")

    def test_run_request_fails_if_no_company_or_brief(self) -> None:
        with self.assertRaisesRegex(ValueError, "Either --brief or --company is required"):
            RunRequest()

    def test_brief_schema_defaults(self) -> None:
        brief = Brief(
            company_name="Ather Energy",
            focus_instructions="Focus on battery manufacturing capabilities",
            exclude_instructions="Ignore their early prototypes",
        )
        self.assertEqual(brief.company_name, "Ather Energy")
        self.assertEqual(brief.website, "Unknown")
        self.assertEqual(brief.sector, "general")
        self.assertEqual(brief.stage, "unknown")
        self.assertEqual(brief.geography, "India")
        self.assertEqual(brief.focus_instructions, "Focus on battery manufacturing capabilities")
        self.assertEqual(brief.exclude_instructions, "Ignore their early prototypes")

    def test_brief_schema_validation_fails_without_company_name(self) -> None:
        with self.assertRaises(ValueError):
            Brief()
