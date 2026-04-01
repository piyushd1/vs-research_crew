from __future__ import annotations

import unittest
from unittest.mock import patch

from pydantic import BaseModel

from my_agents.runner import CrewAIAgentRunner
from my_agents.schemas import AgentSpec


class SampleResponse(BaseModel):
    answer: str


class StubKickoffOutput:
    def __init__(self, raw: str) -> None:
        self.raw = raw
        self.pydantic = None


class StubAgent:
    def __init__(self, outputs: list[str]) -> None:
        self.outputs = outputs
        self.prompts: list[str] = []

    def kickoff(self, prompt: str, response_format=None):
        self.prompts.append(prompt)
        return StubKickoffOutput(self.outputs.pop(0))


class RunnerTests(unittest.TestCase):
    def test_runner_retries_with_stricter_json_prompt(self) -> None:
        agent = StubAgent(
            [
                "I will now analyze the company before returning the answer.",
                '{"answer": "ok"}',
            ]
        )
        runner = CrewAIAgentRunner()
        spec = AgentSpec(
            role="Test",
            goal="Test",
            backstory="Test",
        )

        with patch("my_agents.runner.build_agent", return_value=agent):
            result = runner.run_agent(
                agent_name="test_agent",
                spec=spec,
                prompt="Analyze this company.",
                response_model=SampleResponse,
                llm=object(),
                tools=[],
            )

        self.assertEqual(result.answer, "ok")
        self.assertEqual(len(agent.prompts), 2)
        self.assertIn("Return ONLY a valid JSON object", agent.prompts[0])
        self.assertIn("previous response was not valid JSON", agent.prompts[1])


if __name__ == "__main__":
    unittest.main()
