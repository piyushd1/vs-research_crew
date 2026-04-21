#!/usr/bin/env python
from __future__ import annotations

import argparse
from collections.abc import Callable
from pathlib import Path
import sys

from my_agents.configuration import get_interactive_sector_choices
from my_agents.controller import VCResearchController
from my_agents.schemas import ApproveMode, OutputProfile, RunRequest, WorkflowType


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run the India-first VC research system."
    )
    parser.add_argument("--workflow", choices=[item.value for item in WorkflowType])
    parser.add_argument("--brief", type=Path, help="Path to a company brief YAML or JSON file.")
    parser.add_argument(
        "--output-profile",
        choices=[item.value for item in OutputProfile],
    )
    parser.add_argument(
        "--approve-mode",
        choices=[item.value for item in ApproveMode],
    )
    parser.add_argument("--website")
    parser.add_argument("--sector")
    parser.add_argument("--stage")
    parser.add_argument("--geography")
    parser.add_argument("--docs-dir")
    parser.add_argument("--sources-profile")
    parser.add_argument("--resume", type=Path)
    parser.add_argument("--config-dir", type=Path)
    parser.add_argument("--verbose", action="store_true")
    parser.add_argument("--company", help="Company name for quick-mode research")
    parser.add_argument("--focus", help="Instructions on what to focus on")
    parser.add_argument("--exclude", help="Instructions on what to exclude")
    parser.add_argument("--run-evals", action="store_true", help="Run LLM evaluation on output")
    parser.add_argument("--eval-only-dir", type=Path, help="Run evals on an existing run directory")
    parser.add_argument(
        "--interactive",
        action="store_true",
        help="Prompt for missing run inputs in the terminal.",
    )
    return parser


def _stdin_is_tty() -> bool:
    return bool(getattr(sys.stdin, "isatty", lambda: False)())


def _prompt_text(
    label: str,
    *,
    prompt_fn: Callable[[str], str],
    print_fn: Callable[[str], None],
    default: str | None = None,
    allow_blank: bool = False,
) -> str | None:
    suffix = f" [{default}]" if default else ""
    while True:
        value = prompt_fn(f"{label}{suffix}: ").strip()
        if value:
            return value
        if default is not None:
            return default
        if allow_blank:
            return None
        print_fn("Please enter a value.")


def _prompt_choice(
    label: str,
    choices: list[str],
    *,
    prompt_fn: Callable[[str], str],
    print_fn: Callable[[str], None],
    default: str,
) -> str:
    choice_map = {str(index): value for index, value in enumerate(choices, start=1)}
    choice_display = ", ".join(
        f"{index}:{value}" for index, value in enumerate(choices, start=1)
    )
    while True:
        raw_value = prompt_fn(f"{label} ({choice_display}) [{default}]: ").strip()
        if not raw_value:
            return default
        value = choice_map.get(raw_value, raw_value)
        if value in choices:
            return value
        print_fn(f"Choose one of: {', '.join(choices)}")


def _prompt_labeled_choice(
    label: str,
    choices: list[tuple[str, str]],
    *,
    prompt_fn: Callable[[str], str],
    print_fn: Callable[[str], None],
    default: str,
) -> str:
    values = [value for value, _ in choices]
    choice_map = {str(index): value for index, (value, _) in enumerate(choices, start=1)}
    choice_display = ", ".join(
        f"{index}:{choice_label}"
        for index, (_, choice_label) in enumerate(choices, start=1)
    )
    while True:
        raw_value = prompt_fn(f"{label} ({choice_display}) [{default}]: ").strip()
        if not raw_value:
            return default
        value = choice_map.get(raw_value, raw_value)
        if value in values:
            return value
        print_fn("Choose one of the listed sector numbers.")


def _prompt_yes_no(
    label: str,
    *,
    prompt_fn: Callable[[str], str],
    print_fn: Callable[[str], None],
    default: bool = False,
) -> bool:
    default_label = "Y/n" if default else "y/N"
    while True:
        value = prompt_fn(f"{label} [{default_label}]: ").strip().lower()
        if not value:
            return default
        if value in {"y", "yes"}:
            return True
        if value in {"n", "no"}:
            return False
        print_fn("Please answer yes or no.")


def _should_prompt_for_run_inputs(
    args: argparse.Namespace,
    *,
    stdin_is_tty: bool,
) -> bool:
    if args.resume or args.eval_only_dir or args.brief:
        return False
    if not stdin_is_tty:
        return False
    return bool(
        args.interactive
        or args.company is None
        or args.workflow is None
        or args.output_profile is None
    )


def _prompt_for_missing_run_inputs(
    args: argparse.Namespace,
    *,
    prompt_fn: Callable[[str], str],
    print_fn: Callable[[str], None],
) -> argparse.Namespace:
    print_fn("Interactive mode: answer a few questions to run the VC research workflow.")
    args.company = args.company or _prompt_text(
        "Company name",
        prompt_fn=prompt_fn,
        print_fn=print_fn,
    )
    args.website = args.website or _prompt_text(
        "Website (optional but recommended for diligence)",
        prompt_fn=prompt_fn,
        print_fn=print_fn,
        allow_blank=True,
    )
    args.sector = args.sector or _prompt_labeled_choice(
        "Sector",
        get_interactive_sector_choices(),
        prompt_fn=prompt_fn,
        print_fn=print_fn,
        default="general",
    )
    args.workflow = args.workflow or _prompt_choice(
        "Workflow",
        [item.value for item in WorkflowType],
        prompt_fn=prompt_fn,
        print_fn=print_fn,
        default=WorkflowType.SOURCING.value,
    )
    args.output_profile = args.output_profile or _prompt_choice(
        "Report type",
        [item.value for item in OutputProfile],
        prompt_fn=prompt_fn,
        print_fn=print_fn,
        default=OutputProfile.IC_MEMO.value,
    )
    if not args.run_evals:
        args.run_evals = _prompt_yes_no(
            "Run evals too",
            prompt_fn=prompt_fn,
            print_fn=print_fn,
            default=False,
        )
    if args.workflow in {
        WorkflowType.DUE_DILIGENCE.value,
        WorkflowType.PORTFOLIO.value,
    } and not args.docs_dir:
        args.docs_dir = _prompt_text(
            "Docs directory (optional, PDF/CSV only, helps finance and diligence agents)",
            prompt_fn=prompt_fn,
            print_fn=print_fn,
            allow_blank=True,
        )
    if args.approve_mode is None:
        args.approve_mode = ApproveMode.AUTO.value
    return args


def run(
    argv: list[str] | None = None,
    *,
    prompt_fn: Callable[[str], str] = input,
    print_fn: Callable[[str], None] = print,
    controller: VCResearchController | None = None,
    stdin_is_tty: bool | None = None,
):
    args = _build_parser().parse_args(argv or sys.argv[1:])
    if _should_prompt_for_run_inputs(
        args,
        stdin_is_tty=_stdin_is_tty() if stdin_is_tty is None else stdin_is_tty,
    ):
        args = _prompt_for_missing_run_inputs(
            args,
            prompt_fn=prompt_fn,
            print_fn=print_fn,
        )
    request = RunRequest(
        workflow=WorkflowType(args.workflow) if args.workflow else None,
        brief_path=args.brief,
        output_profile=OutputProfile(args.output_profile)
        if args.output_profile
        else OutputProfile.IC_MEMO,
        approve_mode=ApproveMode(args.approve_mode)
        if args.approve_mode
        else ApproveMode.AUTO,
        website=args.website,
        sector=args.sector,
        stage=args.stage,
        geography=args.geography,
        docs_dir=args.docs_dir,
        sources_profile=args.sources_profile,
        resume=args.resume,
        config_dir=args.config_dir,
        verbose=args.verbose,
        company_name=args.company,
        focus_instructions=args.focus,
        exclude_instructions=args.exclude,
        run_evals=args.run_evals,
        eval_only_dir=args.eval_only_dir,
    )
    artifacts = (controller or VCResearchController()).run(request)
    print_fn(f"Run complete: {artifacts.run_dir}")
    print_fn(f"Report: {artifacts.report_path}")
    if artifacts.report_html_path:
        print_fn(f"Report HTML: {artifacts.report_html_path}")
    print_fn(f"Scorecard: {artifacts.scorecard_path}")
    if artifacts.one_pager_path:
        print_fn(f"One-pager: {artifacts.one_pager_path}")
    if artifacts.pdf_path:
        print_fn(f"PDF: {artifacts.pdf_path}")
    if artifacts.standards_path:
        print_fn(f"Report Validation: {artifacts.standards_path}")
    if artifacts.eval_path:
        print_fn(f"Eval Score: {artifacts.eval_path}")
    if artifacts.eval_report_path:
        print_fn(f"Eval Report: {artifacts.eval_report_path}")
    if artifacts.eval_report_html_path:
        print_fn(f"Eval Report HTML: {artifacts.eval_report_html_path}")
    if artifacts.eval_prompt_path:
        print_fn(f"Eval Prompt: {artifacts.eval_prompt_path}")
    return artifacts


def replay():
    return run()


if __name__ == "__main__":
    run()
