from __future__ import annotations

from my_agents.schemas import AgentSpec


def build_agent(
    agent_name: str,
    spec: AgentSpec,
    llm: object,
    tools: list[object],
    verbose: bool = False,
) -> object:
    from crewai import Agent

    return Agent(
        role=spec.role,
        goal=spec.goal,
        backstory=spec.backstory,
        llm=llm,
        tools=tools,
        verbose=verbose,
        allow_delegation=spec.allow_delegation,
    )
