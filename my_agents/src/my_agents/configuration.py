from __future__ import annotations

from dataclasses import dataclass
import json
import os
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


SECTOR_PROFILE_ALIASES = {
    "adtech": "saas_ai",
    "advertising": "saas_ai",
    "agri": "agritech",
    "agritech": "agritech",
    "agriculture": "agritech",
    "ai": "saas_ai",
    "b2b_marketplace": "marketplaces",
    "b2b_saas": "saas_ai",
    "b2c_marketplace": "marketplaces",
    "banking": "fintech",
    "beauty": "d2c",
    "bio_tech": "deeptech",
    "biotech": "deeptech",
    "bnpl": "fintech",
    "brands": "d2c",
    "buy_now_pay_later": "fintech",
    "care_delivery": "healthtech",
    "clean_energy": "climate",
    "climate": "climate",
    "climate_tech": "climate",
    "climatetech": "climate",
    "cloud_kitchen": "consumer",
    "commerce": "d2c",
    "construction_tech": "proptech",
    "consumer": "consumer",
    "consumer_brand": "d2c",
    "consumer_brands": "d2c",
    "consumer_internet": "consumer",
    "content": "consumer",
    "cyber_security": "cybersecurity",
    "cybersecurity": "cybersecurity",
    "d2c": "d2c",
    "d2c_brand": "d2c",
    "d2c_brands": "d2c",
    "deep_tech": "deeptech",
    "deeptech": "deeptech",
    "defence": "deeptech",
    "defencetech": "deeptech",
    "defense": "deeptech",
    "defensetech": "deeptech",
    "developer_tools": "saas_ai",
    "devtools": "saas_ai",
    "diagnostics": "healthtech",
    "drone": "deeptech",
    "drones": "deeptech",
    "e_commerce": "d2c",
    "ecommerce": "d2c",
    "edtech": "edtech",
    "education": "edtech",
    "energy": "climate",
    "enterprise": "saas_ai",
    "enterprise_software": "saas_ai",
    "entertainment": "consumer",
    "ev": "climate",
    "ev_charging": "climate",
    "farmtech": "agritech",
    "fashion": "d2c",
    "fintech": "fintech",
    "food": "d2c",
    "food_brand": "d2c",
    "food_delivery": "consumer",
    "game_studio": "consumer",
    "gaming": "consumer",
    "genai": "saas_ai",
    "grocery": "d2c",
    "health_care": "healthtech",
    "health_tech": "healthtech",
    "healthcare": "healthtech",
    "healthtech": "healthtech",
    "hospitality": "consumer",
    "housing": "proptech",
    "hr_tech": "saas_ai",
    "hrtech": "saas_ai",
    "industrial_ai": "deeptech",
    "infosec": "cybersecurity",
    "insurtech": "fintech",
    "it_services": "saas_ai",
    "last_mile": "logistics",
    "legal_tech": "saas_ai",
    "legaltech": "saas_ai",
    "lending": "fintech",
    "logistics": "logistics",
    "marketplace": "marketplaces",
    "marketplaces": "marketplaces",
    "materials": "deeptech",
    "media": "consumer",
    "medtech": "healthtech",
    "micro_lending": "fintech",
    "mobility": "logistics",
    "neo_banking": "fintech",
    "neobank": "fintech",
    "ott": "consumer",
    "payment_infra": "fintech",
    "payments": "fintech",
    "personal_care": "d2c",
    "pet_care": "d2c",
    "pettech": "d2c",
    "pharma_tech": "healthtech",
    "proptech": "proptech",
    "qsr": "consumer",
    "quick_commerce": "d2c",
    "real_estate": "proptech",
    "recruitment": "saas_ai",
    "recycling": "climate",
    "regtech": "fintech",
    "retail_brand": "d2c",
    "retail_brands": "d2c",
    "ride_hailing": "logistics",
    "ride_sharing": "logistics",
    "robotics": "deeptech",
    "saas": "saas_ai",
    "saas_ai": "saas_ai",
    "security": "cybersecurity",
    "security_software": "cybersecurity",
    "semiconductor": "deeptech",
    "skincare": "d2c",
    "social_commerce": "consumer",
    "software": "saas_ai",
    "solar": "climate",
    "space": "deeptech",
    "spacetech": "deeptech",
    "streaming": "consumer",
    "supply_chain": "logistics",
    "supply_chain_finance": "fintech",
    "supplychain": "logistics",
    "sustainability": "climate",
    "travel": "consumer",
    "travel_tech": "consumer",
    "uav": "deeptech",
    "upskilling": "edtech",
    "warehousing": "logistics",
    "waste_management": "climate",
    "wealthtech": "fintech",
}


def normalize_profile_key(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip().lower()
    for needle, replacement in (("&", " and "), ("/", "_"), ("-", "_"), (" ", "_")):
        normalized = normalized.replace(needle, replacement)
    while "__" in normalized:
        normalized = normalized.replace("__", "_")
    normalized = normalized.strip("_")
    return normalized or None


def canonicalize_profile_key(value: str | None) -> str | None:
    normalized = normalize_profile_key(value)
    if normalized is None:
        return None
    return SECTOR_PROFILE_ALIASES.get(normalized, normalized)


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
    sector_aliases: dict[str, str]
    llm: LLMConfig
    integrations: IntegrationsConfig
    warnings: list[str]

    def resolve_score_weights(self, sector: str | None) -> dict[str, int]:
        resolved = dict(self.scorecard_base)
        resolved_sector = canonicalize_profile_key(sector)
        if resolved_sector and resolved_sector in self.scorecard_overlays:
            resolved.update(self.scorecard_overlays[resolved_sector])
        return resolved

    def resolve_source_profile(
        self,
        sector: str | None,
        profile_override: str | None = None,
    ) -> SourcePriorityConfig:
        base_payload = self.source_base.model_dump()
        resolved_override = canonicalize_profile_key(profile_override)
        selected_profile = resolved_override or canonicalize_profile_key(sector)
        if (
            resolved_override
            and resolved_override != "base"
            and resolved_override not in self.source_overlays
        ):
            raise ValueError(
                f"Unknown sources profile '{profile_override}'. Available profiles: "
                + ", ".join(["base", *sorted(self.source_overlays)])
            )
        if selected_profile and selected_profile in self.source_overlays:
            overlay_payload = self.source_overlays[selected_profile].model_dump(
                exclude_unset=True
            )
            base_payload["profile"] = selected_profile
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


def _load_scorecards(
    config_dir: Path,
) -> tuple[dict[str, int], dict[str, dict[str, int]]]:
    scorecard_dir = config_dir / "scorecard"
    base = load_yaml(scorecard_dir / "weights_base.yaml")
    overlays = {}
    for path in sorted(scorecard_dir.glob("weights_*.yaml")):
        if path.stem == "weights_base":
            continue
        overlays[path.stem.replace("weights_", "", 1)] = load_yaml(path)
    return base, overlays


def _load_sources(
    config_dir: Path,
) -> tuple[SourcePriorityConfig, dict[str, SourcePriorityConfig]]:
    source_dir = config_dir / "sources"
    base = SourcePriorityConfig.model_validate(
        load_yaml(source_dir / "priority_base.yaml")
    )
    overlays = {}
    for path in sorted(source_dir.glob("priority_*.yaml")):
        if path.stem == "priority_base":
            continue
        overlays[path.stem.replace("priority_", "", 1)] = (
            SourcePriorityConfig.model_validate(load_yaml(path))
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
    scorecard_base, scorecard_overlays = _load_scorecards(resolved_config_dir)
    source_base, source_overlays = _load_sources(resolved_config_dir)
    config = AppConfig(
        config_dir=resolved_config_dir,
        agents=_load_agents(resolved_config_dir),
        workflows=_load_workflows(resolved_config_dir),
        output_profiles=_load_output_profiles(resolved_config_dir),
        scorecard_base={str(key): int(value) for key, value in scorecard_base.items()},
        scorecard_overlays={
            name: {str(key): int(value) for key, value in overlay.items()}
            for name, overlay in scorecard_overlays.items()
        },
        source_base=source_base,
        source_overlays=source_overlays,
        sector_aliases=dict(SECTOR_PROFILE_ALIASES),
        llm=LLMConfig.model_validate(load_yaml(resolved_config_dir / "llm.yaml")),
        integrations=IntegrationsConfig.model_validate(
            load_yaml(resolved_config_dir / "integrations.yaml")
        ),
        warnings=[],
    )
    config.warnings = validate_app_config(config)
    return config
