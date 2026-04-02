from __future__ import annotations

import unittest
from unittest.mock import patch

from pydantic import BaseModel

from my_agents.runner import AgentFinalAnswerError, CrewAIAgentRunner
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


class FailingStubAgent:
    def __init__(self, exc: Exception) -> None:
        self.exc = exc
        self.prompts: list[str] = []

    def kickoff(self, prompt: str, response_format=None):
        self.prompts.append(prompt)
        raise self.exc


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

    def test_runner_raises_agent_final_answer_error_after_exhausted_retries(self) -> None:
        agent = FailingStubAgent(
            RuntimeError("Agent execution ended without reaching a final answer.")
        )
        runner = CrewAIAgentRunner()
        spec = AgentSpec(role="Test", goal="Test", backstory="Test")

        with patch("my_agents.runner.build_agent", return_value=agent):
            with self.assertRaises(AgentFinalAnswerError):
                runner.run_agent(
                    agent_name="test_agent",
                    spec=spec,
                    prompt="Analyze this company.",
                    response_model=SampleResponse,
                    llm=object(),
                    tools=[],
                )

        self.assertEqual(len(agent.prompts), 3)
        self.assertIn("final retry", agent.prompts[-1])


    def test_runner_salvages_partial_output_from_prose(self) -> None:
        prose = (
            "After researching Acme Corp, I found that the company has strong revenue growth. "
            "Revenue grew 50% YoY. The main risk is regulatory uncertainty."
        )
        result = CrewAIAgentRunner._salvage_partial_result("financial_researcher", prose)
        self.assertEqual(result.agent_name, "financial_researcher")
        self.assertTrue(len(result.summary) > 0)
        self.assertTrue(result.partial)


if __name__ == "__main__":
    unittest.main()
