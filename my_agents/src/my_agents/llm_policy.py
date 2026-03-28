from __future__ import annotations

import os
from typing import Iterable

from my_agents.schemas import LLMConfig, LLMProvider


DEFAULT_OPEN_SOURCE_HINTS = (
    "deepseek/",
    "openrouter/deepseek/",
    "meta-llama/",
    "openrouter/meta-llama/",
    "llama-",
    "qwen/",
    "openrouter/qwen/",
    "gemma",
    "openrouter/google/gemma",
    "mistral/",
    "openrouter/mistral/",
    "mixtral",
    "granite",
    "phi-",
    "falcon",
    "olmo",
    "nemotron",
)


def _lowered_candidates(model: str) -> list[str]:
    model_l = model.lower().strip()
    pieces = [model_l]
    if "/" in model_l:
        pieces.extend(segment for segment in model_l.split("/") if segment)
    return pieces


def is_allowed_open_source_model(model: str, prefixes: Iterable[str]) -> bool:
    model_l = model.lower().strip()
    hints = tuple(prefix.lower() for prefix in prefixes) or DEFAULT_OPEN_SOURCE_HINTS
    return any(hint in model_l for hint in hints)


def normalize_model_name(config: LLMConfig) -> str:
    model = config.model.strip()
    if config.provider == LLMProvider.OPENROUTER and not model.startswith("openrouter/"):
        return f"openrouter/{model}"
    if config.provider == LLMProvider.OLLAMA and not model.startswith("ollama/"):
        return f"ollama/{model}"
    return model


def validate_llm_config(config: LLMConfig) -> None:
    normalized_model = normalize_model_name(config)

    if config.open_source_only and not config.allow_closed_models:
        if config.provider == LLMProvider.OLLAMA:
            return
        if not is_allowed_open_source_model(
            normalized_model, config.allowed_model_prefixes
        ):
            raise ValueError(
                "Configured model does not match the allowed open-source model families. "
                "Either choose an OSS model or explicitly opt into closed models."
            )


def build_llm(config: LLMConfig):
    from crewai.llm import LLM

    validate_llm_config(config)
    normalized_model = normalize_model_name(config)
    base_url = config.base_url
    api_key = None

    if config.provider == LLMProvider.OPENROUTER:
        base_url = base_url or "https://openrouter.ai/api/v1"
    elif config.provider == LLMProvider.OLLAMA:
        base_url = base_url or "http://localhost:11434"

    if config.api_key_env:
        api_key = os.environ.get(config.api_key_env)
        if config.provider != LLMProvider.OLLAMA and not api_key:
            raise RuntimeError(
                f"Environment variable {config.api_key_env} is required for provider "
                f"{config.provider.value}."
            )

    if config.provider == LLMProvider.OPENAI_COMPATIBLE and not base_url:
        raise RuntimeError("openai_compatible provider requires base_url in config.")

    return LLM(
        model=normalized_model,
        base_url=base_url,
        api_key=api_key,
        temperature=config.temperature,
        max_tokens=config.max_tokens,
    )

def build_eval_llm(config: LLMConfig):
    from crewai.llm import LLM
    if not config.eval_model:
        return build_llm(config)
        
    eval_config = config.model_copy(update={"model": config.eval_model})
    return build_llm(eval_config)
