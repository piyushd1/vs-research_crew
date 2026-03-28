#!/usr/bin/env python
from __future__ import annotations

import argparse
from pathlib import Path
import sys

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
        default=OutputProfile.IC_MEMO.value,
        choices=[item.value for item in OutputProfile],
    )
    parser.add_argument(
        "--approve-mode",
        default=ApproveMode.AUTO.value,
        choices=[item.value for item in ApproveMode],
    )
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
    return parser


def run(argv: list[str] | None = None):
    args = _build_parser().parse_args(argv or sys.argv[1:])
    request = RunRequest(
        workflow=WorkflowType(args.workflow) if args.workflow else None,
        brief_path=args.brief,
        output_profile=OutputProfile(args.output_profile),
        approve_mode=ApproveMode(args.approve_mode),
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
    artifacts = VCResearchController().run(request)
    print(f"Run complete: {artifacts.run_dir}")
    print(f"Report: {artifacts.report_path}")
    print(f"Scorecard: {artifacts.scorecard_path}")
    if artifacts.one_pager_path:
        print(f"One-pager: {artifacts.one_pager_path}")
    if artifacts.pdf_path:
        print(f"PDF: {artifacts.pdf_path}")
    return artifacts


def replay():
    return run()


def train():
    raise SystemExit("Training is not implemented for this VC workflow app.")


def test():
    raise SystemExit("Use the project test suite instead of the starter template command.")


def run_with_trigger():
    raise SystemExit("run_with_trigger is not implemented for this VC workflow app.")


if __name__ == "__main__":
    run()
