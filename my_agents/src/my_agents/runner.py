from __future__ import annotations

import json
from typing import Protocol

from pydantic import BaseModel

from my_agents.crew import build_agent
from my_agents.schemas import AgentFindingResult, AgentSpec

_JSON_EXAMPLE = json.dumps(
    {
        "agent_name": "financial_researcher",
        "summary": "Brief 2-3 sentence summary of findings.",
        "findings": [
            {
                "claim": "Revenue grew 50% YoY in FY2024.",
                "evidence_summary": "Per the company's annual report, revenue increased from $10M to $15M.",
                "source_ref": "FY2024 Annual Report, p.12",
                "source_type": "company_filing",
                "confidence": 0.85,
            }
        ],
        "dimension_scores": [
            {
                "dimension": "financial_health",
                "score": 4,
                "rationale": "Strong revenue growth with improving margins.",
            }
        ],
        "open_questions": ["What is the customer churn rate?"],
        "sources_checked": [
            {
                "source_name": "Company website",
                "source_type": "website",
                "accessed": True,
            }
        ],
        "suggested_section_keys": ["financial_analysis"],
    },
    indent=2,
)


class AgentFinalAnswerError(RuntimeError):
    """Raised when CrewAI never reaches a final answer after retries."""


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
    def _build_json_prompt(
        prompt: str,
        response_model: type[BaseModel],
        retry: bool = False,
        final_attempt: bool = False,
        previous_error: str | None = None,
    ) -> str:
        schema = json.dumps(response_model.model_json_schema(), indent=2)
        retry_block = ""
        if retry:
            retry_block = (
                "The previous response was not valid JSON. "
                "Return ONLY a valid JSON object this time. "
                "Start your response with { and end with }. "
                "Do not include ANY text before or after the JSON.\n"
            )
        if previous_error:
            retry_block += f"Previous error: {previous_error}\n"
        if final_attempt:
            retry_block += (
                "This is the final retry. STOP searching and STOP using tools immediately. "
                "Return your best partial answer RIGHT NOW as valid JSON. "
                "If evidence is incomplete, set confidence values low (0.1-0.3) "
                "and list gaps in open_questions. Do not keep searching or looping.\n"
            )

        example_block = ""
        if response_model is AgentFindingResult or (
            hasattr(response_model, "__name__")
            and response_model.__name__ == "AgentFindingResult"
        ):
            example_block = (
                "\nHere is a concrete example of valid output JSON:\n"
                f"{_JSON_EXAMPLE}\n\n"
            )

        return (
            f"{prompt}\n\n"
            "Return ONLY a valid JSON object that matches this schema exactly. "
            "Start your response with { and end with }. "
            "Do not add commentary, preamble, markdown fences, or explanations.\n"
            f"{retry_block}"
            f"{example_block}"
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

    @staticmethod
    def _salvage_partial_result(
        agent_name: str, raw_output: str
    ) -> AgentFindingResult:
        """Build a partial AgentFindingResult from unstructured prose output.

        This is a last-resort fallback when the agent fails to produce valid
        JSON after all retries.  The raw text is preserved as the summary so
        downstream stages can still extract value.
        """
        truncated = raw_output[:1000].strip() if raw_output else "No output captured."
        return AgentFindingResult(
            agent_name=agent_name,
            summary=truncated,
            findings=[],
            partial=True,
            open_questions=[
                "Agent failed to return structured JSON. Manual review needed.",
                "Raw output has been preserved in the summary field.",
            ],
        )

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
        attempts = [
            {"retry": False, "final_attempt": False},
            {"retry": True, "final_attempt": False},
            {"retry": True, "final_attempt": True},
        ]
        errors: list[Exception] = []
        last_raw_output: str | None = None

        for attempt in attempts:
            agent = build_agent(
                agent_name=agent_name,
                spec=spec,
                llm=llm,
                tools=tools,
                verbose=verbose,
            )
            try:
                output = agent.kickoff(
                    self._build_json_prompt(
                        prompt,
                        response_model,
                        retry=attempt["retry"],
                        final_attempt=attempt["final_attempt"],
                        previous_error=str(errors[-1]) if errors else None,
                    )
                )
                last_raw_output = output.raw
                return response_model.model_validate_json(
                    self._extract_json_payload(output.raw)
                )
            except Exception as exc:
                errors.append(exc)

        # --- Salvage path for AgentFindingResult ---
        is_finding_result = response_model is AgentFindingResult or (
            hasattr(response_model, "__name__")
            and response_model.__name__ == "AgentFindingResult"
        )
        if is_finding_result and last_raw_output:
            return self._salvage_partial_result(agent_name, last_raw_output)

        last_error = errors[-1]
        if any("ended without reaching a final answer" in str(error) for error in errors):
            raise AgentFinalAnswerError(
                f"Agent '{agent_name}' did not reach a final answer after {len(attempts)} attempts."
            ) from last_error
        raise last_error
