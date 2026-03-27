from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from my_agents.llm_policy import validate_llm_config
from my_agents.schemas import (
    AgentSpec,
    Brief,
    IntegrationsConfig,
    LLMConfig,
    OutputProfileConfig,
    SourcePriorityConfig,
    WorkflowConfig,
)


PACKAGE_ROOT = Path(__file__).resolve().parent
DEFAULT_CONFIG_DIR = PACKAGE_ROOT / "config"


@dataclass
class AppConfig:
    config_dir: Path
    agents: dict[str, AgentSpec]
    workflows: dict[str, WorkflowConfig]
    output_profiles: dict[str, OutputProfileConfig]
    scorecard_base: dict[str, int]
    scorecard_overlays: dict[str, dict[str, int]]
    source_base: SourcePriorityConfig
    source_overlays: dict[str, SourcePriorityConfig]
    llm: LLMConfig
    integrations: IntegrationsConfig
    warnings: list[str]

    def resolve_score_weights(self, sector: str | None) -> dict[str, int]:
        resolved = dict(self.scorecard_base)
        if sector and sector in self.scorecard_overlays:
            resolved.update(self.scorecard_overlays[sector])
        return resolved

    def resolve_source_profile(self, sector: str | None) -> SourcePriorityConfig:
        base_payload = self.source_base.model_dump()
        if sector and sector in self.source_overlays:
            overlay_payload = self.source_overlays[sector].model_dump(exclude_unset=True)
            base_payload["tiers"].update(overlay_payload.get("tiers", {}))
            for field in ("india_priority_sources", "founder_signal_sources"):
                if overlay_payload.get(field):
                    base_payload[field] = overlay_payload[field]
            if overlay_payload.get("search_provider"):
                base_payload["search_provider"] = overlay_payload["search_provider"]
        return SourcePriorityConfig.model_validate(base_payload)


def load_yaml(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return yaml.safe_load(handle) or {}


def load_json(path: Path) -> Any:
    with path.open("r", encoding="utf-8") as handle:
        return json.load(handle)


def load_brief(path: Path) -> Brief:
    payload = load_json(path) if path.suffix == ".json" else load_yaml(path)
    return Brief.model_validate(payload)


def _load_agents(config_dir: Path) -> dict[str, AgentSpec]:
    payload = load_yaml(config_dir / "agents.yaml")
    return {name: AgentSpec.model_validate(spec) for name, spec in payload.items()}


def _load_workflows(config_dir: Path) -> dict[str, WorkflowConfig]:
    workflows_dir = config_dir / "workflows"
    return {
        workflow_path.stem: WorkflowConfig.model_validate(load_yaml(workflow_path))
        for workflow_path in sorted(workflows_dir.glob("*.yaml"))
    }


def _load_output_profiles(config_dir: Path) -> dict[str, OutputProfileConfig]:
    output_dir = config_dir / "output_profiles"
    return {
        profile_path.stem: OutputProfileConfig.model_validate(load_yaml(profile_path))
        for profile_path in sorted(output_dir.glob("*.yaml"))
    }


def _load_scorecards(config_dir: Path) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
    scorecard_dir = config_dir / "scorecard"
    base = load_yaml(scorecard_dir / "weights_base.yaml")
    overlays = {}
    for path in sorted(scorecard_dir.glob("weights_*.yaml")):
        if path.stem == "weights_base":
            continue
        overlays[path.stem.replace("weights_", "", 1)] = load_yaml(path)
    return base, overlays


def _load_sources(config_dir: Path) -> tuple[SourcePriorityConfig, dict[str, SourcePriorityConfig]]:
    source_dir = config_dir / "sources"
    base = SourcePriorityConfig.model_validate(load_yaml(source_dir / "priority_base.yaml"))
    overlays = {}
    for path in sorted(source_dir.glob("priority_*.yaml")):
        if path.stem == "priority_base":
            continue
        overlays[path.stem.replace("priority_", "", 1)] = SourcePriorityConfig.model_validate(
            load_yaml(path)
        )
    return base, overlays


def validate_app_config(config: AppConfig) -> list[str]:
    warnings: list[str] = []

    validate_llm_config(config.llm)

    for workflow_name, workflow in config.workflows.items():
        for task in workflow.tasks:
            if task.agent not in config.agents:
                raise ValueError(
                    f"Workflow {workflow_name} references unknown agent {task.agent}."
                )

    for weights_name, weights in {
        "base": config.scorecard_base,
        **config.scorecard_overlays,
    }.items():
        total = sum(int(value) for value in weights.values())
        if total != 100:
            raise ValueError(
                f"Scorecard weights for {weights_name} sum to {total}, expected 100."
            )

    if config.integrations.linear.enabled and not os.environ.get("LINEAR_API_KEY"):
        warnings.append(
            "LINEAR_API_KEY is not set. Linear integration will be skipped at runtime."
        )

    return warnings


def load_app_config(config_dir: Path | None = None) -> AppConfig:
    resolved_config_dir = (config_dir or DEFAULT_CONFIG_DIR).resolve()
    config = AppConfig(
        config_dir=resolved_config_dir,
        agents=_load_agents(resolved_config_dir),
        workflows=_load_workflows(resolved_config_dir),
        output_profiles=_load_output_profiles(resolved_config_dir),
        scorecard_base={str(key): int(value) for key, value in _load_scorecards(resolved_config_dir)[0].items()},
        scorecard_overlays={
            name: {str(key): int(value) for key, value in overlay.items()}
            for name, overlay in _load_scorecards(resolved_config_dir)[1].items()
        },
        source_base=_load_sources(resolved_config_dir)[0],
        source_overlays=_load_sources(resolved_config_dir)[1],
        llm=LLMConfig.model_validate(load_yaml(resolved_config_dir / "llm.yaml")),
        integrations=IntegrationsConfig.model_validate(
            load_yaml(resolved_config_dir / "integrations.yaml")
        ),
        warnings=[],
    )
    config.warnings = validate_app_config(config)
    return config
