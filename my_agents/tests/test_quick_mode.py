from __future__ import annotations

import argparse
from pathlib import Path
import unittest

from my_agents.main import _prompt_for_missing_run_inputs, _should_prompt_for_run_inputs
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

    def test_run_request_allows_eval_only_dir_without_brief_or_company(self) -> None:
        req = RunRequest(eval_only_dir=Path("/tmp/existing-run"))
        self.assertIsNone(req.workflow)

    def test_should_prompt_for_missing_terminal_inputs(self) -> None:
        args = argparse.Namespace(
            resume=None,
            eval_only_dir=None,
            brief=None,
            interactive=False,
            company=None,
            workflow=None,
            output_profile=None,
        )
        self.assertTrue(_should_prompt_for_run_inputs(args, stdin_is_tty=True))

    def test_should_not_prompt_for_brief_or_non_tty(self) -> None:
        args = argparse.Namespace(
            resume=None,
            eval_only_dir=None,
            brief=Path("/tmp/brief.yaml"),
            interactive=False,
            company=None,
            workflow=None,
            output_profile=None,
        )
        self.assertFalse(_should_prompt_for_run_inputs(args, stdin_is_tty=True))
        args.brief = None
        self.assertFalse(_should_prompt_for_run_inputs(args, stdin_is_tty=False))

    def test_prompt_for_missing_run_inputs_populates_quick_mode_values(self) -> None:
        answers = iter(["Razorpay", "https://razorpay.com", "2", "2", "3", "y", ""])
        prompts: list[str] = []
        messages: list[str] = []
        args = argparse.Namespace(
            company=None,
            website=None,
            sector=None,
            workflow=None,
            output_profile=None,
            docs_dir=None,
            run_evals=False,
            approve_mode=None,
        )

        updated = _prompt_for_missing_run_inputs(
            args,
            prompt_fn=lambda text: prompts.append(text) or next(answers),
            print_fn=messages.append,
        )

        self.assertEqual(updated.company, "Razorpay")
        self.assertEqual(updated.website, "https://razorpay.com")
        self.assertEqual(updated.sector, "fintech")
        self.assertEqual(updated.workflow, "due_diligence")
        self.assertEqual(updated.output_profile, "one_pager")
        self.assertTrue(updated.run_evals)
        self.assertEqual(updated.approve_mode, "auto")
        self.assertTrue(prompts)
        self.assertIn("Interactive mode", messages[0])

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
