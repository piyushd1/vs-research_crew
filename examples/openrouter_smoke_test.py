from __future__ import annotations

import os
from pathlib import Path

from crewai import Agent
from crewai.memory.unified_memory import Memory
from crewai.utilities.llm_utils import create_llm
from crewai.utilities.planning_handler import CrewPlanner
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parents[1] / ".env")


def describe_llm(name: str, llm: object) -> None:
    model = getattr(llm, "model", None)
    provider = getattr(llm, "provider", None)
    base_url = getattr(llm, "base_url", None)
    print(f"{name}: model={model!r} provider={provider!r} base_url={base_url!r}")


def main() -> None:
    print(f"MODEL env: {os.getenv('MODEL')!r}")
    print(f"OPENROUTER_API_KEY set: {bool(os.getenv('OPENROUTER_API_KEY'))}")

    default_llm = create_llm()
    if default_llm is None:
        raise RuntimeError("create_llm() did not resolve a default model.")

    describe_llm("create_llm()", default_llm)

    agent = Agent(
        role="Verifier",
        goal="Confirm the default LLM wiring.",
        backstory="Checks that CrewAI resolves the configured provider correctly.",
    )
    describe_llm("Agent default llm", agent.llm)

    planner = CrewPlanner(tasks=[])
    print(f"CrewPlanner default llm: {planner.planning_agent_llm!r}")

    memory = Memory()
    print(f"Memory default llm: {memory.llm!r}")


if __name__ == "__main__":
    main()
