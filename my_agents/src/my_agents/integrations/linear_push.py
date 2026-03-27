from __future__ import annotations

import os
from pathlib import Path

import httpx

from my_agents.schemas import FindingsBundle, IntegrationsConfig, OutputProfile, WorkflowType


LINEAR_URL = "https://api.linear.app/graphql"


def build_linear_issue_payload(
    bundle: FindingsBundle,
    workflow: WorkflowType,
    output_profile: OutputProfile,
    run_dir: Path,
) -> dict[str, object]:
    top_risks = "\n".join(f"- {risk}" for risk in bundle.top_risks[:3]) or "- None"
    top_signals = "\n".join(f"- {signal}" for signal in bundle.top_signals[:3]) or "- None"
    description = (
        f"Workflow: {workflow.value}\n"
        f"Output profile: {output_profile.value}\n"
        f"Run folder: {run_dir}\n\n"
        f"Score: {bundle.scorecard.overall_score:.1f}\n\n"
        f"Top risks:\n{top_risks}\n\n"
        f"Top signals:\n{top_signals}\n"
    )
    return {
        "title": f"{bundle.company_name} - {workflow.value}",
        "description": description,
    }


def push_linear_issue(
    bundle: FindingsBundle,
    workflow: WorkflowType,
    output_profile: OutputProfile,
    run_dir: Path,
    integrations: IntegrationsConfig,
) -> bool:
    linear_config = integrations.linear
    if not linear_config.enabled:
        return False

    api_key = os.environ.get("LINEAR_API_KEY")
    if not api_key:
        return False

    payload = build_linear_issue_payload(bundle, workflow, output_profile, run_dir)
    query = """
    mutation IssueCreate($input: IssueCreateInput!) {
      issueCreate(input: $input) {
        success
      }
    }
    """
    input_payload = {
        "teamId": linear_config.team_id,
        "projectId": linear_config.project_id,
        "title": payload["title"],
        "description": payload["description"],
        "labelIds": linear_config.label_ids,
    }
    response = httpx.post(
        LINEAR_URL,
        headers={"Authorization": api_key},
        json={"query": query, "variables": {"input": input_payload}},
        timeout=15.0,
    )
    response.raise_for_status()
    return bool(
        response.json().get("data", {}).get("issueCreate", {}).get("success", False)
    )
