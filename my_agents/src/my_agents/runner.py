from __future__ import annotations

from typing import Protocol

from pydantic import BaseModel

from my_agents.crew import build_agent
from my_agents.schemas import AgentSpec


class AgentRunner(Protocol):
    def run_agent(
        self,
        agent_name: str,
        spec: AgentSpec,
        prompt: str,
        response_model: type[BaseModel],
        llm: object,
        tools: list[object],
        verbose: bool = False,
    ) -> BaseModel:
        ...


class CrewAIAgentRunner:
    def run_agent(
        self,
        agent_name: str,
        spec: AgentSpec,
        prompt: str,
        response_model: type[BaseModel],
        llm: object,
        tools: list[object],
        verbose: bool = False,
    ) -> BaseModel:
        agent = build_agent(
            agent_name=agent_name,
            spec=spec,
            llm=llm,
            tools=tools,
            verbose=verbose,
        )
        output = agent.kickoff(prompt, response_format=response_model)
        if output.pydantic is not None:
            return output.pydantic
        return response_model.model_validate_json(output.raw)
