from __future__ import annotations

import json
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
    @staticmethod
    def _build_json_prompt(prompt: str, response_model: type[BaseModel], retry: bool = False) -> str:
        schema = json.dumps(response_model.model_json_schema(), indent=2)
        retry_block = ""
        if retry:
            retry_block = (
                "The previous response was not valid JSON. "
                "Return ONLY a valid JSON object this time.\n"
            )
        return (
            f"{prompt}\n\n"
            "Return ONLY a valid JSON object that matches this schema exactly. "
            "Do not add commentary, preamble, markdown fences, or explanations.\n"
            f"{retry_block}"
            f"{schema}\n"
        )

    @staticmethod
    def _extract_json_payload(text: str) -> str:
        candidate = text.strip()
        if candidate.startswith("```"):
            lines = candidate.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            candidate = "\n".join(lines).strip()

        if candidate.startswith("{") and candidate.endswith("}"):
            return candidate

        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            return candidate[start : end + 1]
        return candidate

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
        try:
            output = agent.kickoff(self._build_json_prompt(prompt, response_model))
            return response_model.model_validate_json(
                self._extract_json_payload(output.raw)
            )
        except Exception:
            output = agent.kickoff(self._build_json_prompt(prompt, response_model, retry=True))
            return response_model.model_validate_json(
                self._extract_json_payload(output.raw)
            )
