# VC Research Quality Overhaul — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Fix agent failures, add deep research tools (Tavily + RAG), rewrite prompts with VC frameworks, add reflection loops, and improve report quality so eval scores go from 14/100 to >65/100.

**Architecture:** 9 layered changes applied bottom-up: fix the runner so agents stop crashing, add better tools so agents find data, rewrite prompts so agents know what to research, add RAG so agents can query documents and prior findings, add reflection so agents self-critique, improve synthesis and rendering so reports are IC-ready.

**Tech Stack:** CrewAI, ChromaDB (1.1.1, already installed), pdfplumber, Tavily Python SDK (to install), OpenRouter (DeepSeek R1 / Qwen 3), Pydantic v2

---

## Task 1: Install Tavily SDK & Update Dependencies

**Files:**
- Modify: `pyproject.toml`
- Modify: `requirements.txt`

**Step 1: Install tavily-python into the venv**

Run: `.venv/bin/uv pip install tavily-python`
Expected: Successfully installed tavily-python

**Step 2: Add to pyproject.toml dependencies**

Add `tavily-python>=0.5.0` to the `[project.dependencies]` list alongside `crewai[tools]`.

**Step 3: Update requirements.txt if it exists**

Add `tavily-python>=0.5.0`.

**Step 4: Verify import works**

Run: `.venv/bin/python -c "from tavily import TavilyClient; print('ok')"`
Expected: `ok`

**Step 5: Commit**

```bash
git add pyproject.toml requirements.txt
git commit -m "chore: add tavily-python dependency for deep web research"
```

---

## Task 2: Fix Agent Runner — Stop Agents From Crashing

**Files:**
- Modify: `src/my_agents/runner.py`
- Modify: `src/my_agents/crew.py`
- Modify: `src/my_agents/schemas.py:194-206` (FindingRecord defaults)
- Test: `tests/test_runner.py`

**Step 1: Write failing test for salvage extraction**

In `tests/test_runner.py`, add a test that verifies the runner can extract partial findings from non-JSON agent output:

```python
def test_runner_salvages_partial_output_from_prose(self) -> None:
    """When agent returns prose instead of JSON, extract what we can."""
    prose = (
        "After researching Acme Corp, I found that the company has strong revenue growth. "
        "Revenue grew 50% YoY. The main risk is regulatory uncertainty. "
        "I could not find exact burn rate data."
    )
    result = CrewAIAgentRunner._salvage_partial_result(
        "financial_researcher", prose
    )
    self.assertEqual(result.agent_name, "financial_researcher")
    self.assertTrue(len(result.summary) > 0)
    self.assertTrue(result.partial)
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_runner.py::RunnerTests::test_runner_salvages_partial_output_from_prose -v`
Expected: FAIL — `_salvage_partial_result` doesn't exist yet

**Step 3: Update schemas.py — add `partial` field to AgentFindingResult**

At `schemas.py:229`, add after `suggested_section_keys`:

```python
partial: bool = False
```

Also make `confidence` in `FindingRecord` default to 0.5:

```python
confidence: float = Field(default=0.5, ge=0.0, le=1.0)
```

**Step 4: Rewrite runner.py**

Replace the entire `runner.py` with an improved version:

```python
from __future__ import annotations

import json
import re
from typing import Protocol

from pydantic import BaseModel

from my_agents.crew import build_agent
from my_agents.schemas import AgentFindingResult, AgentSpec


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
    ) -> BaseModel: ...


_JSON_EXAMPLE = '''{
  "agent_name": "example_agent",
  "summary": "One paragraph summarizing key findings.",
  "findings": [
    {
      "claim": "Specific factual claim with data",
      "evidence_summary": "Where this claim comes from",
      "source_ref": "https://example.com or 'uploaded: filename.pdf page 5'",
      "source_type": "public_web",
      "confidence": 0.7,
      "risk_level": "medium",
      "open_questions": []
    }
  ],
  "dimension_scores": [
    {"dimension": "market_size_and_growth", "score": 3, "rationale": "Reason for score"}
  ],
  "open_questions": ["What we could not verify"],
  "downstream_flags": [],
  "sources_checked": [
    {"source_name": "Company website", "source_type": "company_site", "accessed": true, "note": "Found pricing page"}
  ],
  "suggested_section_keys": ["financial_analysis"]
}'''


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
                "\n--- IMPORTANT: PREVIOUS ATTEMPT FAILED ---\n"
                "Your previous response was not valid JSON. You MUST return ONLY a raw JSON object.\n"
                "Do NOT wrap it in markdown code fences. Do NOT add any text before or after the JSON.\n"
            )
        if previous_error:
            retry_block += f"Previous error: {previous_error}\n"
        if final_attempt:
            retry_block += (
                "\nFINAL ATTEMPT — STOP SEARCHING. Return your best answer NOW.\n"
                "If evidence is incomplete, that is OK. Return what you have with:\n"
                "- Low confidence scores (0.3-0.5) for uncertain claims\n"
                "- Open questions listing what you could not verify\n"
                "- At least one finding, even if it's basic company information\n"
                "A partial answer is infinitely better than no answer.\n"
            )

        example_block = ""
        if response_model is AgentFindingResult or (
            hasattr(response_model, '__name__') and 'Finding' in response_model.__name__
        ):
            example_block = f"\nHere is an EXAMPLE of a valid response (adapt to your findings):\n{_JSON_EXAMPLE}\n"

        return (
            f"{prompt}\n\n"
            "--- OUTPUT FORMAT ---\n"
            "Return ONLY a valid JSON object matching the schema below.\n"
            "No commentary, no preamble, no markdown fences, no explanations.\n"
            "Start your response with {{ and end with }}.\n"
            f"{retry_block}"
            f"{example_block}"
            f"\nJSON Schema:\n{schema}\n"
        )

    @staticmethod
    def _extract_json_payload(text: str) -> str:
        candidate = text.strip()
        # Strip markdown code fences
        if candidate.startswith("```"):
            lines = candidate.splitlines()
            if lines and lines[0].startswith("```"):
                lines = lines[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            candidate = "\n".join(lines).strip()

        if candidate.startswith("{") and candidate.endswith("}"):
            return candidate

        # Try to find the outermost JSON object
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            return candidate[start : end + 1]
        return candidate

    @staticmethod
    def _salvage_partial_result(
        agent_name: str,
        raw_output: str,
    ) -> AgentFindingResult:
        """Extract whatever we can from non-JSON agent output."""
        # Use the raw text as a summary
        summary = raw_output[:1000].strip()
        if not summary:
            summary = f"{agent_name} produced no usable output."

        # Try to extract any claims/findings from the prose
        findings = []
        open_questions = [
            f"{agent_name} did not produce structured output. Manual review recommended."
        ]

        return AgentFindingResult(
            agent_name=agent_name,
            summary=summary,
            findings=findings,
            open_questions=open_questions,
            partial=True,
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
        last_raw_output: str = ""

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
                last_raw_output = output.raw if hasattr(output, 'raw') else str(output)
                return response_model.model_validate_json(
                    self._extract_json_payload(last_raw_output)
                )
            except Exception as exc:
                errors.append(exc)
                if hasattr(output, 'raw'):
                    last_raw_output = output.raw

        # All retries exhausted — try to salvage if this is an AgentFindingResult
        if response_model is AgentFindingResult and last_raw_output:
            return self._salvage_partial_result(agent_name, last_raw_output)

        last_error = errors[-1]
        if any("ended without reaching a final answer" in str(error) for error in errors):
            raise AgentFinalAnswerError(
                f"Agent '{agent_name}' did not reach a final answer after {len(attempts)} attempts."
            ) from last_error
        raise last_error
```

**Step 5: Update crew.py — set max_iter and max_retry_limit**

```python
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
        max_iter=15,
        max_retry_limit=2,
        respect_context_window=True,
    )
```

**Step 6: Run all runner tests**

Run: `.venv/bin/python -m pytest tests/test_runner.py -v`
Expected: All pass including the new salvage test

**Step 7: Run full test suite**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: All 42+ tests pass

**Step 8: Commit**

```bash
git add src/my_agents/runner.py src/my_agents/crew.py src/my_agents/schemas.py tests/test_runner.py
git commit -m "fix: robust agent runner with salvage extraction and iteration limits"
```

---

## Task 3: Add Tavily Deep Research Tools

**Files:**
- Create: `src/my_agents/tools/tavily_tool.py`
- Modify: `src/my_agents/tools/__init__.py`
- Create: `tests/test_tavily_tool.py`

**Step 1: Write test for Tavily tool selection**

Create `tests/test_tavily_tool.py`:

```python
from __future__ import annotations

import os
import types
import unittest
from unittest.mock import patch, MagicMock

from my_agents.schemas import Brief, SourcePriorityConfig
from my_agents.tools import build_tools


class TavilyToolSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.brief = Brief(company_name="TestCo", website="https://testco.com", sector="fintech")
        self.source_profile = SourcePriorityConfig(
            profile="fintech",
            tiers={"company_site": 1},
            search_provider="serper",
        )

    def test_tavily_search_tool_added_when_api_key_set(self) -> None:
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}, clear=False):
            tools = build_tools(self.brief, self.source_profile, "market_mapper")
        tool_names = [getattr(tool, "name", type(tool).__name__) for tool in tools]
        self.assertIn("tavily_search", tool_names)

    def test_tavily_research_tool_added_for_financial_researcher(self) -> None:
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key", "SERPER_API_KEY": "test"}, clear=False):
            tools = build_tools(self.brief, self.source_profile, "financial_researcher")
        tool_names = [getattr(tool, "name", type(tool).__name__) for tool in tools]
        self.assertIn("tavily_research", tool_names)
        self.assertIn("financial_signal_search", tool_names)

    def test_no_tavily_tools_without_api_key(self) -> None:
        env = {k: v for k, v in os.environ.items() if k != "TAVILY_API_KEY"}
        with patch.dict(os.environ, env, clear=True):
            tools = build_tools(self.brief, self.source_profile, "market_mapper")
        tool_names = [getattr(tool, "name", type(tool).__name__) for tool in tools]
        self.assertNotIn("tavily_search", tool_names)
        self.assertNotIn("tavily_research", tool_names)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_tavily_tool.py -v`
Expected: FAIL — tavily tools don't exist yet

**Step 3: Create `tools/tavily_tool.py`**

```python
from __future__ import annotations

import json
import os
from urllib import error, parse, request

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class TavilySearchInput(BaseModel):
    query: str = Field(..., description="Search query. Be specific and include company name + India context.")
    search_depth: str = Field(default="advanced", description="'basic' for quick, 'advanced' for thorough")


class TavilySearchTool(BaseTool):
    name: str = "tavily_search"
    description: str = (
        "Deep web search that returns rich snippets and source URLs. "
        "Use for finding company information, financial data, regulatory filings, "
        "news articles, and market analysis. Returns more detailed results than basic search."
    )
    args_schema: type[BaseModel] = TavilySearchInput

    def _run(self, query: str, search_depth: str = "advanced") -> str:
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            return "TAVILY_API_KEY is not configured."

        payload = {
            "query": query,
            "search_depth": search_depth,
            "max_results": 8,
            "include_raw_content": False,
        }
        req = request.Request(
            "https://api.tavily.com/search",
            data=json.dumps({"api_key": api_key, **payload}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:
            return f"Search failed: {exc}"

        results = data.get("results", [])
        if not results:
            return f"No results found for: {query}"

        lines = [f"Search: {query}", f"Results ({len(results)}):"]
        for item in results:
            title = item.get("title", "Untitled")
            url = item.get("url", "")
            content = item.get("content", "")[:500]
            score = item.get("score", 0)
            lines.append(f"\n- [{title}]({url}) (relevance: {score:.2f})")
            if content:
                lines.append(f"  {content}")
        return "\n".join(lines)


class TavilyExtractInput(BaseModel):
    url: str = Field(..., description="URL to extract full content from")


class TavilyExtractTool(BaseTool):
    name: str = "tavily_extract"
    description: str = (
        "Extracts the full text content of a web page as markdown. "
        "Use after finding a relevant URL via search to get detailed content. "
        "Good for reading company websites, regulatory filings, news articles."
    )
    args_schema: type[BaseModel] = TavilyExtractInput

    def _run(self, url: str) -> str:
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            return "TAVILY_API_KEY is not configured."

        payload = {
            "urls": [url],
        }
        req = request.Request(
            "https://api.tavily.com/extract",
            data=json.dumps({"api_key": api_key, **payload}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=30) as response:
                data = json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:
            return f"Extraction failed: {exc}"

        results = data.get("results", [])
        if not results:
            return f"Could not extract content from: {url}"

        content = results[0].get("raw_content", results[0].get("content", ""))
        if not content:
            return f"No content extracted from: {url}"

        # Truncate to avoid overwhelming the agent context
        if len(content) > 8000:
            content = content[:8000] + "\n\n[Content truncated at 8000 characters]"

        return f"Extracted from {url}:\n\n{content}"


class TavilyResearchInput(BaseModel):
    topic: str = Field(..., description="Research topic — be specific, include company name and what you want to know")


class TavilyResearchTool(BaseTool):
    name: str = "tavily_research"
    description: str = (
        "Comprehensive multi-source research on a topic. Searches multiple sources, "
        "cross-references findings, and returns a detailed research report. "
        "Use for deep-dive analysis on financial performance, market positioning, "
        "competitive landscape, or regulatory environment. More thorough than basic search "
        "but takes longer."
    )
    args_schema: type[BaseModel] = TavilyResearchInput

    def _run(self, topic: str) -> str:
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            return "TAVILY_API_KEY is not configured."

        # Use Tavily search with advanced depth and more results
        payload = {
            "query": topic,
            "search_depth": "advanced",
            "max_results": 10,
            "include_raw_content": False,
        }
        req = request.Request(
            "https://api.tavily.com/search",
            data=json.dumps({"api_key": api_key, **payload}).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=45) as response:
                data = json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:
            return f"Research failed: {exc}"

        results = data.get("results", [])
        answer = data.get("answer", "")

        lines = [f"Research topic: {topic}"]
        if answer:
            lines.extend(["", "Summary:", answer])

        if results:
            lines.extend(["", f"Sources ({len(results)}):"])
            for item in results:
                title = item.get("title", "Untitled")
                url = item.get("url", "")
                content = item.get("content", "")[:600]
                lines.append(f"\n- [{title}]({url})")
                if content:
                    lines.append(f"  {content}")
        else:
            lines.append("No detailed sources found.")

        return "\n".join(lines)
```

**Step 4: Update `tools/__init__.py` with Tavily + agent-specific toolkits**

```python
from __future__ import annotations

import os
from pathlib import Path

from my_agents.schemas import Brief, SourcePriorityConfig

# Agents that get the comprehensive research tool (Tavily research + extract)
_DEEP_RESEARCH_AGENTS = {
    "financial_researcher",
    "market_mapper",
    "product_tech_researcher",
    "customer_competition_analyst",
    "marketing_gtm_researcher",
}

# Agents that primarily analyze prior findings (get DataRoomSearch but not external search)
_INTERNAL_ANALYSIS_AGENTS = {
    "risk_red_team_analyst",
    "investment_analyst",
    "valuation_scenarios_analyst",
}


def build_tools(
    brief: Brief,
    source_profile: SourcePriorityConfig,
    agent_name: str,
    chroma_collection: object | None = None,
) -> list[object]:
    from my_agents.tools.custom_tool import (
        CSVPreviewTool,
        DirectoryManifestTool,
        FinancialSignalSearchTool,
        IndiaSourceRegistryTool,
        PDFExcerptTool,
    )

    tools: list[object] = [
        IndiaSourceRegistryTool(),
    ]

    # Document tools when docs_dir is provided
    if brief.docs_dir:
        docs_path = Path(brief.docs_dir)
        if docs_path.exists():
            tools.extend(
                [
                    DirectoryManifestTool(docs_root=str(docs_path)),
                    PDFExcerptTool(docs_root=str(docs_path)),
                    CSVPreviewTool(docs_root=str(docs_path)),
                ]
            )

    # RAG tool when ChromaDB collection is available
    if chroma_collection is not None:
        try:
            from my_agents.tools.rag_tool import DataRoomSearchTool
            tools.append(DataRoomSearchTool(collection=chroma_collection))
        except Exception:
            pass

    # Tavily tools (primary research capability)
    if os.environ.get("TAVILY_API_KEY"):
        from my_agents.tools.tavily_tool import (
            TavilyExtractTool,
            TavilyResearchTool,
            TavilySearchTool,
        )

        if agent_name not in _INTERNAL_ANALYSIS_AGENTS:
            tools.append(TavilySearchTool())
            tools.append(TavilyExtractTool())

        if agent_name in _DEEP_RESEARCH_AGENTS:
            tools.append(TavilyResearchTool())

    # Financial signal search (Serper-based, for financial specialists)
    if (
        agent_name in {"financial_researcher", "kpi_burn_analyst"}
        and os.environ.get("SERPER_API_KEY")
    ):
        tools.append(FinancialSignalSearchTool())
    elif (
        source_profile.search_provider == "serper"
        and os.environ.get("SERPER_API_KEY")
        and not os.environ.get("TAVILY_API_KEY")  # Don't add Serper if Tavily is available
    ):
        try:
            from crewai_tools import SerperDevTool
            tools.append(SerperDevTool())
        except Exception:
            pass

    return tools
```

**Step 5: Run Tavily tool tests**

Run: `.venv/bin/python -m pytest tests/test_tavily_tool.py tests/test_tools.py -v`
Expected: All pass

**Step 6: Commit**

```bash
git add src/my_agents/tools/tavily_tool.py src/my_agents/tools/__init__.py tests/test_tavily_tool.py
git commit -m "feat: add Tavily deep research tools (search, extract, research)"
```

---

## Task 4: Add RAG with ChromaDB

**Files:**
- Create: `src/my_agents/tools/rag_tool.py`
- Modify: `src/my_agents/controller.py` (add indexing at run start and after each agent)
- Create: `tests/test_rag_tool.py`

**Step 1: Write test for RAG tool**

Create `tests/test_rag_tool.py`:

```python
from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from my_agents.tools.rag_tool import DocumentIndexer, DataRoomSearchTool


class RAGToolTests(unittest.TestCase):
    def test_indexer_creates_collection_from_text_files(self) -> None:
        """Index a simple text and query it."""
        indexer = DocumentIndexer()
        collection = indexer.create_collection("test-run")
        indexer.index_text(
            collection,
            text="Acme Corp has annual revenue of 50 crores INR with 30% gross margins.",
            source="pitch_deck.pdf",
            page=5,
        )
        tool = DataRoomSearchTool(collection=collection)
        result = tool._run(query="What is Acme's revenue?")
        self.assertIn("50 crores", result)
        self.assertIn("pitch_deck.pdf", result)

    def test_indexer_handles_empty_docs_dir(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            indexer = DocumentIndexer()
            collection = indexer.create_collection("empty-test")
            count = indexer.index_docs_dir(collection, tmp_dir)
            self.assertEqual(count, 0)

    def test_search_with_no_results(self) -> None:
        indexer = DocumentIndexer()
        collection = indexer.create_collection("empty-search")
        tool = DataRoomSearchTool(collection=collection)
        result = tool._run(query="anything")
        self.assertIn("No relevant", result)


if __name__ == "__main__":
    unittest.main()
```

**Step 2: Run test to verify it fails**

Run: `.venv/bin/python -m pytest tests/test_rag_tool.py -v`
Expected: FAIL — module doesn't exist

**Step 3: Create `tools/rag_tool.py`**

```python
from __future__ import annotations

import hashlib
import os
from pathlib import Path

import chromadb
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split text into overlapping chunks by word count."""
    words = text.split()
    if len(words) <= chunk_size:
        return [text] if text.strip() else []
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + chunk_size, len(words))
        chunk = " ".join(words[start:end])
        if chunk.strip():
            chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def _content_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:12]


class DocumentIndexer:
    """Indexes documents and agent findings into ChromaDB for semantic search."""

    def __init__(self) -> None:
        self._client = chromadb.Client()  # In-memory, per-run

    def create_collection(self, run_id: str) -> chromadb.Collection:
        safe_name = "".join(c if c.isalnum() or c in "-_" else "-" for c in run_id)[:60]
        safe_name = safe_name.strip("-") or "default"
        # ChromaDB collection names must be 3-63 chars
        if len(safe_name) < 3:
            safe_name = safe_name + "-run"
        return self._client.get_or_create_collection(name=safe_name)

    def index_text(
        self,
        collection: chromadb.Collection,
        text: str,
        source: str,
        page: int | None = None,
        agent_name: str | None = None,
    ) -> int:
        """Index a text block into chunks. Returns number of chunks added."""
        chunks = _chunk_text(text)
        if not chunks:
            return 0

        ids = []
        documents = []
        metadatas = []
        for i, chunk in enumerate(chunks):
            chunk_id = f"{_content_hash(source)}_{i}"
            metadata = {"source": source}
            if page is not None:
                metadata["page"] = page
            if agent_name:
                metadata["agent"] = agent_name
            ids.append(chunk_id)
            documents.append(chunk)
            metadatas.append(metadata)

        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        return len(chunks)

    def index_docs_dir(self, collection: chromadb.Collection, docs_dir: str) -> int:
        """Index all PDFs and CSVs from a docs directory."""
        docs_path = Path(docs_dir)
        if not docs_path.exists():
            return 0

        total_chunks = 0

        # Index PDFs
        for pdf_path in sorted(docs_path.rglob("*.pdf")):
            try:
                import pdfplumber
                with pdfplumber.open(pdf_path) as pdf:
                    for page_num, page in enumerate(pdf.pages, start=1):
                        text = page.extract_text()
                        if text and text.strip():
                            total_chunks += self.index_text(
                                collection,
                                text=text,
                                source=str(pdf_path.relative_to(docs_path)),
                                page=page_num,
                            )
            except Exception:
                continue

        # Index CSVs
        import csv
        for csv_path in sorted(docs_path.rglob("*.csv")):
            try:
                with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                    reader = csv.reader(handle)
                    rows = list(reader)
                if rows:
                    header = rows[0]
                    text_rows = [" | ".join(header)]
                    for row in rows[1:]:
                        text_rows.append(" | ".join(row))
                    full_text = "\n".join(text_rows)
                    total_chunks += self.index_text(
                        collection,
                        text=full_text,
                        source=str(csv_path.relative_to(docs_path)),
                    )
            except Exception:
                continue

        return total_chunks

    def index_agent_findings(
        self,
        collection: chromadb.Collection,
        agent_name: str,
        summary: str,
        findings_text: str,
    ) -> int:
        """Index an agent's findings for cross-agent RAG."""
        combined = f"Agent: {agent_name}\n\nSummary: {summary}\n\nFindings:\n{findings_text}"
        return self.index_text(
            collection,
            text=combined,
            source=f"agent:{agent_name}",
            agent_name=agent_name,
        )


class DataRoomSearchInput(BaseModel):
    query: str = Field(
        ...,
        description=(
            "Natural language query to search uploaded documents and prior agent findings. "
            "Be specific: 'revenue breakdown by segment' or 'regulatory risks identified'. "
        ),
    )
    n_results: int = Field(default=5, description="Number of results to return (1-10)")


class DataRoomSearchTool(BaseTool):
    name: str = "data_room_search"
    description: str = (
        "Semantic search over uploaded diligence documents (PDFs, CSVs) and prior agent findings. "
        "Use this to find specific data points in uploaded documents or to check what prior "
        "agents have already discovered. Returns the most relevant text chunks with source attribution."
    )
    args_schema: type[BaseModel] = DataRoomSearchInput
    collection: object = None  # ChromaDB collection

    class Config:
        arbitrary_types_allowed = True

    def _run(self, query: str, n_results: int = 5) -> str:
        if self.collection is None:
            return "No document collection available."

        n_results = max(1, min(10, n_results))
        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=n_results,
            )
        except Exception as exc:
            return f"Search failed: {exc}"

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        if not documents:
            return f"No relevant documents found for: {query}"

        lines = [f"Search: {query}", f"Found {len(documents)} relevant chunks:", ""]
        for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances), 1):
            source = meta.get("source", "unknown")
            page = meta.get("page")
            agent = meta.get("agent")
            location = source
            if page:
                location += f" (page {page})"
            if agent:
                location += f" [from {agent}]"
            relevance = max(0, 1 - dist) if dist else 0
            lines.append(f"--- Result {i} (relevance: {relevance:.2f}) from {location} ---")
            lines.append(doc[:800])
            lines.append("")

        return "\n".join(lines)
```

**Step 4: Run RAG tests**

Run: `.venv/bin/python -m pytest tests/test_rag_tool.py -v`
Expected: All pass

**Step 5: Integrate RAG into controller.py**

In `controller.py`, add the following changes:

1. Import `DocumentIndexer` at the top
2. After `_prepare_run_context`, create the indexer and collection
3. If `brief.docs_dir` exists, index documents at run start
4. After each agent completes, index its findings
5. Pass `chroma_collection` to `build_tools()`

Key changes in the main `run()` method after line 233 (after `evidence = EvidenceRegistry(...)`):

```python
# Initialize RAG
from my_agents.tools.rag_tool import DocumentIndexer
indexer = DocumentIndexer()
run_collection_id = f"{self._slugify(brief.company_name)}-{state.workflow.value}"
chroma_collection = indexer.create_collection(run_collection_id)

# Index uploaded documents
if brief.docs_dir:
    doc_count = indexer.index_docs_dir(chroma_collection, brief.docs_dir)
    if doc_count:
        self.print_fn(f"Indexed {doc_count} document chunks into vector store.")
```

In the agent loop, pass `chroma_collection` to `build_tools`:

```python
tools = build_tools(brief, source_profile, task.agent, chroma_collection=chroma_collection)
```

After each agent completes (after `evidence.add_result(result)`), index findings:

```python
# Index agent findings for cross-agent RAG
findings_text = "\n".join(
    f"- {f.claim} (confidence: {f.confidence}, source: {f.source_ref})"
    for f in result.findings
)
indexer.index_agent_findings(
    chroma_collection,
    agent_name=task.agent,
    summary=result.summary,
    findings_text=findings_text,
)
```

**Step 6: Run full test suite**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: All tests pass (existing tests don't use chroma_collection param, it defaults to None)

**Step 7: Commit**

```bash
git add src/my_agents/tools/rag_tool.py src/my_agents/tools/__init__.py src/my_agents/controller.py tests/test_rag_tool.py
git commit -m "feat: add ChromaDB RAG for document search and cross-agent knowledge"
```

---

## Task 5: Rewrite Agent Prompts with VC Frameworks

**Files:**
- Modify: `src/my_agents/config/agents.yaml`
- Modify: `src/my_agents/controller.py:568-689` (`_build_specialist_prompt`)

**Step 1: Rewrite agents.yaml with detailed backstories and prompt_notes**

This is the highest-impact change. Each agent gets:
- Expanded `backstory` with domain expertise
- `prompt_notes` with specific research instructions
- `failure_guidance` field (new) — what to do when data is sparse

Full replacement for `agents.yaml`:

```yaml
orchestrator:
  role: "VC Research Orchestrator"
  goal: "Keep the workflow disciplined, India-first, and decision-ready."
  backstory: "You act like an IC chief of staff for an early-stage India-focused VC. You have 10 years of experience managing diligence workflows for India-focused venture funds."
  prompt_notes:
    - "Keep the work tightly scoped to the selected workflow."
    - "Favor India-relevant sources and INR/regulatory framing."

evidence_auditor:
  role: "Evidence Auditor"
  goal: "Surface uncited claims, evidence conflicts, circular reasoning, and missing diligence gaps."
  backstory: >
    You are a skeptical diligence reviewer who rejects unsupported conclusions.
    You have seen too many memos where analysts cite the company's own pitch deck as independent evidence,
    or where 'strong growth' is stated without a single number. You check every claim against its source.
  prompt_notes:
    - "Never resolve conflicts silently."
    - "Escalate missing citations and unresolved contradictions."
    - "Flag circular reasoning: citing the brief or company claims as independent evidence."
    - "Check for score inflation: all 4s and 5s without corresponding high-confidence findings is suspicious."

report_synthesizer:
  role: "Investment Report Synthesizer"
  goal: "Turn validated findings into a structured, IC-ready findings bundle that a VC partner can act on."
  backstory: >
    You prepare crisp IC-ready material for a venture team. You write like a senior analyst at a top-tier VC:
    lead with the conclusion, support with specific data points, acknowledge gaps honestly.
    No marketing language. No vague qualifiers. Every sentence earns its place.
  prompt_notes:
    - "Each section must have at least 2 specific data points and 1 citation."
    - "Executive summary: 3-4 sentences. Lead with verdict, then key evidence, then biggest risk."
    - "Do not invent citations or data points."
    - "If a section has no real evidence, write 'Insufficient evidence for this section. Key gap: [specific gap].' Do not pad with generic statements."

startup_sourcer:
  role: "Startup Sourcer"
  goal: "Build a high-signal company snapshot with specific data points for early screening."
  backstory: >
    You identify promising startups for India-focused venture investors. You specialize in building
    rapid but data-rich company profiles. You always include: founding year, founders, funding history,
    reported revenue/users if available, key product, and target segment.
  source_focus: ["company_site", "startup_media", "public_web"]
  scoring_dimensions: ["market_size_and_growth", "founder_quality_and_signal"]
  prompt_notes:
    - "Always include: company name, founding year, founders, location, funding rounds (amount + investors), product description, target customer."
    - "If data is missing, explicitly state what's missing rather than omitting."
    - "Use Inc42, YourStory, Entrackr, The Ken, Economic Times Startup for India startup data."
  failure_guidance: >
    If you cannot find detailed information, return the company name, website, and whatever basic
    facts are publicly available. A thin but accurate snapshot is better than nothing. Mark confidence
    as 0.3-0.4 for inferred data.

thesis_fit_analyst:
  role: "Thesis Fit Analyst"
  goal: "Judge whether a company fits the firm's sector, stage, and geography thesis with specific evidence."
  backstory: >
    You think like a principal matching companies against fund strategy. You evaluate:
    Is this the right sector? Right stage? Right geography? Does the TAM support venture returns?
  source_focus: ["company_site", "startup_media", "public_web"]
  scoring_dimensions: ["market_size_and_growth", "gtm_traction_and_momentum"]
  prompt_notes:
    - "Assess TAM/SAM/SOM with specific numbers where available."
    - "Compare company stage to typical fund investment criteria."
    - "Flag if company is too early or too late for typical early-stage VC."

market_mapper:
  role: "Market Mapper"
  goal: "Map the competitive landscape, market size, and India-specific tailwinds/headwinds with specific data."
  backstory: >
    You synthesize market structure using Porter's Five Forces and TAM/SAM/SOM frameworks.
    You always name specific competitors and their differentiation. You cite market size estimates
    from credible sources (Redseer, Bain India, industry reports).
  source_focus: ["public_web", "startup_media", "regulator"]
  scoring_dimensions: ["market_size_and_growth"]
  prompt_notes:
    - "FRAMEWORK: Use Porter's Five Forces (rivalry, new entrants, substitutes, buyer power, supplier power)."
    - "Name 3-5 direct competitors with their funding, revenue (if known), and differentiation."
    - "Provide TAM/SAM/SOM estimates with source citations."
    - "Identify India-specific tailwinds (policy, demographics, digital adoption) and headwinds (regulation, infrastructure)."
  failure_guidance: >
    If market data is unavailable, estimate TAM from proxies (adjacent markets, government data, industry reports).
    Always name at least 2-3 competitors even if funding data is sparse. Mark estimates with low confidence.

founder_signal_analyst:
  role: "Founder Signal Analyst"
  goal: "Assess founder quality through India-first public evidence without LinkedIn scraping."
  backstory: >
    You evaluate founder signal using public records and India-first sources. You look at:
    prior founding history, domain expertise, team composition, IP filings, regulatory track record,
    and media presence. You never rely on LinkedIn profiles.
  source_focus: ["mca", "ip_india", "startup_india", "public_media", "court_records"]
  scoring_dimensions: ["founder_quality_and_signal"]
  default_tools: ["india_source_registry"]
  prompt_notes:
    - "Check MCA/ROC for director history and company filings."
    - "Check IP India for patents filed by founders."
    - "Check media coverage in Inc42, YourStory, ET Startup for founder interviews and track record."
    - "Assess: prior exits, domain expertise years, team completeness (tech + business + ops), academic background."
  failure_guidance: >
    If founder information is sparse, focus on what IS available: company age, team size from website,
    any media interviews. Score conservatively (2-3) with explicit gaps noted.

financial_researcher:
  role: "Financial Researcher"
  goal: "Assess revenue quality, burn, runway, and unit-economics signal using available evidence."
  backstory: >
    You operate like a VC finance analyst reviewing startup numbers for investability.
    You know that most Indian startups don't disclose detailed financials. You use proxies:
    MCA filings for revenue ranges, funding rounds for implied valuation, team size for rough burn,
    pricing pages for unit economics, and media reports for reported metrics.
  source_focus: ["uploaded_private", "company_site", "audited_financials"]
  scoring_dimensions: ["business_model_and_unit_economics"]
  prompt_notes:
    - "FRAMEWORK for analysis:"
    - "1. Revenue quality: Model (SaaS/transaction/marketplace), recurrence, concentration"
    - "2. Unit economics: CAC, LTV, contribution margin, payback. Use proxies if direct data unavailable."
    - "3. Burn and runway: Monthly burn estimate, last funding round, implied runway"
    - "4. Growth: Revenue/user growth rate, retention/churn signals"
    - "5. Capital efficiency: Revenue per employee, gross margin trajectory"
    - "SCORING RUBRIC: 5=strong unit economics, clear profitability path; 4=good growth, improving economics; 3=early revenue, unclear economics; 2=pre-revenue or deeply negative; 1=no revenue signal"
    - "RED FLAGS: Revenue concentration >50% single customer, burn multiple >3x, negative gross margins"
    - "GREEN FLAGS: Net revenue retention >120%, CAC payback <18mo, improving gross margins QoQ"
    - "Check MCA filings for reported revenue ranges."
    - "Check Tracxn/Crunchbase via web search for funding history."
  failure_guidance: >
    Financial data for private Indian companies is often unavailable. This is EXPECTED.
    When data is sparse: (1) Check MCA/ROC filings for revenue brackets, (2) Estimate burn from
    team size × average salary, (3) Use funding rounds for implied valuation, (4) Check pricing page
    for unit economics proxies. Return what you found with confidence 0.3-0.5 and list specific
    open questions. DO NOT loop searching for data that doesn't exist publicly.

marketing_gtm_researcher:
  role: "Marketing and GTM Researcher"
  goal: "Evaluate go-to-market motion, customer acquisition, and traction with specific metrics."
  backstory: >
    You study demand generation and GTM quality in Indian startup contexts. You evaluate:
    distribution strategy, customer acquisition channels, sales motion (PLG vs enterprise vs field),
    pricing strategy, and traction metrics (users, revenue, app downloads, social proof).
  source_focus: ["company_site", "public_media", "uploaded_private"]
  scoring_dimensions: ["gtm_traction_and_momentum"]
  prompt_notes:
    - "FRAMEWORK: Classify GTM motion (PLG, sales-led, marketplace, channel-led)."
    - "Check app store rankings and reviews (Google Play, App Store) for consumer companies."
    - "Check website traffic signals (SimilarWeb mentions in media, Alexa mentions)."
    - "Look for customer logos, case studies, partnership announcements."
    - "Assess pricing strategy: freemium, subscription, usage-based, take-rate."
  failure_guidance: >
    For early-stage companies, traction data is often limited. Use proxies: app store reviews/ratings,
    social media following, job postings (indicates growth), partnership announcements. Score conservatively
    and note what metrics would be needed for a definitive assessment.

investment_analyst:
  role: "Investment Analyst"
  goal: "Translate the diligence record into an invest/pass point of view with explicit conviction drivers."
  backstory: >
    You think in terms of IC framing. Your job is to synthesize all diligence into a clear
    recommendation. You explicitly state: What are the 2-3 reasons to invest? What are the 2-3
    reasons to pass? What would change the recommendation?
  source_focus: ["internal_findings", "public_web"]
  prompt_notes:
    - "Structure as: INVEST BECAUSE (2-3 conviction points) / PASS BECAUSE (2-3 concerns) / CONDITIONAL ON (2-3 items)"
    - "Each point must reference specific evidence from prior agents' findings."
    - "Do not introduce new research — synthesize what exists."

product_tech_researcher:
  role: "Product and Technology Researcher"
  goal: "Assess product differentiation, technical maturity, and defensibility with specific evidence."
  backstory: >
    You evaluate whether the product and tech stack support durable competitive advantage.
    You look at: product architecture, tech differentiation, IP portfolio, engineering quality
    signals (GitHub, tech blog), and product-market fit evidence.
  source_focus: ["company_site", "product_docs", "github", "uploaded_private"]
  scoring_dimensions: ["product_tech_differentiation"]
  prompt_notes:
    - "Check company website for product features, architecture, and integrations."
    - "Check GitHub for open-source activity, code quality signals, contributor count."
    - "Check IP India or Google Patents for patent filings."
    - "Assess: Is this a tech product or a services business? What's the technical moat?"
    - "SCORING: 5=deep tech moat with patents/IP; 4=strong product with clear differentiation; 3=solid product, moderate differentiation; 2=me-too product; 1=no clear product"

customer_competition_analyst:
  role: "Customer and Competition Analyst"
  goal: "Understand customer value, buyer profile, retention, and competitive pressure."
  backstory: >
    You map how the company wins or loses deals. You analyze: who the buyer is, why they choose
    this product, what alternatives exist, switching costs, and any retention/churn signals.
  source_focus: ["public_web", "company_site", "startup_media"]
  scoring_dimensions: ["market_size_and_growth", "gtm_traction_and_momentum"]
  prompt_notes:
    - "Identify the ideal customer profile (ICP) with specifics: company size, industry, geography."
    - "Map 3-5 competitors and their positioning relative to the target company."
    - "Look for customer reviews, case studies, NPS mentions, and retention data."
    - "Assess switching costs: high (enterprise SaaS with integrations) vs low (consumer app)."

india_regulatory_legal_analyst:
  role: "India Regulatory and Legal Analyst"
  goal: "Surface India-specific legal, compliance, and regulatory risks with specific regulatory references."
  backstory: >
    You specialize in Indian sector regulation. You check: MCA filings, SEBI/RBI/IRDAI compliance,
    sector-specific licenses, data protection (DPDP Act), foreign investment (FEMA/FDI), and any
    pending litigation or regulatory actions.
  source_focus: ["regulator", "mca", "sebi", "rbi", "court_records"]
  scoring_dimensions: ["india_regulatory_and_compliance_posture"]
  prompt_notes:
    - "Check sector-specific regulatory requirements (e.g., RBI license for lending, IRDAI for insurance)."
    - "Check MCA for compliance filings, director changes, charges/liens."
    - "Assess DPDP Act (India data protection) compliance readiness."
    - "Check for FEMA/FDI compliance if foreign investors are involved."
    - "Look for NCLT filings, consumer court cases, or regulatory actions."
  failure_guidance: >
    If specific regulatory filings are not accessible, document which checks you attempted.
    Note the regulatory framework that APPLIES to this company even if you can't verify compliance.
    This is valuable information for the IC.

risk_red_team_analyst:
  role: "Risk Red Team Analyst"
  goal: "Challenge the bullish case with specific evidence and surface the top 3-5 failure modes."
  backstory: >
    You are the skeptical partner in the room. You look for what could go wrong: market risk,
    execution risk, regulatory risk, competitive risk, team risk, and financial risk. You don't
    repeat what other analysts said — you challenge their conclusions.
  source_focus: ["internal_findings", "public_web"]
  scoring_dimensions: ["risk_profile"]
  prompt_notes:
    - "FRAMEWORK: For each risk, specify: (1) What could go wrong, (2) Probability (high/medium/low), (3) Impact (high/medium/low), (4) Mitigation available"
    - "Challenge overly optimistic claims from prior agents."
    - "Look for risks NOT covered by other agents: founder concentration, key-person dependency, single point of failure."
    - "Your job is adversarial — find weaknesses, don't confirm strengths."

valuation_scenarios_analyst:
  role: "Valuation and Scenarios Analyst"
  goal: "Frame reasonable base, upside, and downside scenarios with specific assumptions."
  backstory: >
    You translate the diligence record into investment scenarios. For each scenario (base, upside, downside),
    you specify key assumptions and implied valuation ranges. You use comparable transactions
    and revenue multiples relevant to the Indian market.
  source_focus: ["internal_findings", "uploaded_private"]
  prompt_notes:
    - "FRAMEWORK: Three scenarios (base, upside, downside) with explicit assumptions for each."
    - "Use comparable Indian startup valuations (cite specific examples if known)."
    - "Base case: continuation of current trajectory. Upside: what goes right. Downside: what goes wrong."
    - "Tie each scenario back to specific diligence findings."

portfolio_monitor:
  role: "Portfolio Monitor"
  goal: "Summarize the current state of a portfolio company with specific KPIs and momentum signals."
  backstory: "You support portfolio health reviews and partner updates with data-driven summaries."
  source_focus: ["uploaded_private", "company_site", "public_web"]

kpi_burn_analyst:
  role: "KPI and Burn Analyst"
  goal: "Evaluate runway, KPI trends, and near-term operating risk with specific metrics."
  backstory: "You review company KPIs with an investor's eye for variance, burn rate, and financial health."
  source_focus: ["uploaded_private", "csv_data"]
  scoring_dimensions: ["business_model_and_unit_economics"]

growth_ops_analyst:
  role: "Growth Ops Analyst"
  goal: "Identify practical growth and operating support opportunities with specific recommendations."
  backstory: "You think like a hands-on portfolio support operator looking for high-leverage interventions."
  source_focus: ["internal_findings", "uploaded_private", "public_web"]

risk_alert_analyst:
  role: "Risk Alert Analyst"
  goal: "Detect risk triggers that require immediate investor attention with specific evidence."
  backstory: "You watch for signs that a company needs intervention: cash crunch, key departures, regulatory action, competitive threat."
  source_focus: ["internal_findings", "regulator", "public_web"]
```

**Step 2: Rewrite `_build_specialist_prompt` in controller.py**

The key changes to the prompt builder (controller.py:568-689):

1. Add research planning preamble
2. Add self-critique checklist
3. Add failure guidance from agent spec
4. Inject VC framework instructions from prompt_notes
5. Add concrete JSON example

Replace the return statement in `_build_specialist_prompt` with a much richer prompt:

```python
prompt_notes_block = ""
if spec.prompt_notes:
    prompt_notes_block = (
        "RESEARCH FRAMEWORK (follow this structure):\n"
        + "\n".join(f"- {note}" for note in spec.prompt_notes)
        + "\n\n"
    )

failure_guidance_block = ""
failure_guidance = getattr(spec, "failure_guidance", None)
if failure_guidance:
    failure_guidance_block = (
        "IF DATA IS SPARSE (read this carefully):\n"
        f"{failure_guidance}\n\n"
    )

return (
    f"{injected_context}"
    "--- RESEARCH PLANNING (think before you search) ---\n"
    "Before using any tools, mentally plan:\n"
    "1. What are the 3-5 most important questions to answer?\n"
    "2. What sources are most likely to have this data?\n"
    "3. What will you do if primary sources don't have the data?\n\n"
    f"You are {spec.role}.\n"
    f"Goal: {spec.goal}\n"
    f"Backstory: {spec.backstory}\n\n"
    f"Workflow: {state.workflow.value}\n"
    f"Task objective: {task.objective}\n\n"
    f"Company brief:\n"
    f"- Name: {brief.company_name}\n"
    f"- Website: {brief.website}\n"
    f"- Sector: {brief.sector}\n"
    f"- Stage: {brief.stage}\n"
    f"- Geography: {brief.geography}\n"
    f"- One-line: {brief.one_line or 'Not provided'}\n"
    f"- Thesis: {brief.investment_thesis or 'Not provided'}\n"
    f"- Notes: {brief.notes or 'Not provided'}\n\n"
    f"Prior evidence summary:\n{evidence.summary()}\n\n"
    f"{focus_block}"
    f"{exclude_block}"
    f"{prompt_notes_block}"
    f"India-first source priorities:\n{source_notes}\n\n"
    f"{docs_block}"
    f"{scoring_block}"
    f"{financial_block}"
    f"{failure_guidance_block}"
    "--- RESEARCH DISCIPLINE ---\n"
    "- Use at most 6 tool calls total. Quality over quantity.\n"
    "- Prioritize: official sources > India business media > general web.\n"
    "- If a search returns nothing useful, DO NOT repeat similar queries. Move on.\n"
    "- You MUST return a final structured answer even if evidence is thin.\n"
    "- A conservative answer with explicit gaps is better than looping forever.\n\n"
    "--- SELF-CRITIQUE CHECKLIST (verify before submitting) ---\n"
    "Before producing your final JSON, verify:\n"
    "[ ] Every claim has a specific source (not 'various sources' or 'industry reports')\n"
    "[ ] Confidence scores reflect actual evidence (don't default everything to 0.8)\n"
    "[ ] Open questions list everything you could NOT verify\n"
    "[ ] Dimension scores use the scoring rubric, not gut feel\n"
    "[ ] No claims are merely restating the company brief\n\n"
    "When adding downstream_flags.for_agent, use ONLY these exact agent ids:\n"
    f"{workflow_agent_ids}\n{control_agent_ids}\n\n"
    f"{founder_signal_block}"
    "Use suggested_section_keys only from this allowed set:\n"
    + "\n".join(f"- {item}" for item in sorted(ALLOWED_SECTION_KEYS))
    + "\n\n"
    "Produce a structured result with cited findings, confidence scores, open questions, "
    "dimension scores where relevant, and downstream flags only when another named agent "
    "should investigate something further."
)
```

**Step 3: Add `failure_guidance` to AgentSpec in schemas.py**

```python
class AgentSpec(BaseModel):
    role: str
    goal: str
    backstory: str
    prompt_notes: list[str] = Field(default_factory=list)
    source_focus: list[str] = Field(default_factory=list)
    scoring_dimensions: list[str] = Field(default_factory=list)
    default_tools: list[str] = Field(default_factory=list)
    allow_delegation: bool = False
    active: bool = True
    failure_guidance: str | None = None
```

**Step 4: Run all tests**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: All pass

**Step 5: Commit**

```bash
git add src/my_agents/config/agents.yaml src/my_agents/controller.py src/my_agents/schemas.py
git commit -m "feat: rewrite agent prompts with VC frameworks, planning, and self-critique"
```

---

## Task 6: Improve Report Synthesizer

**Files:**
- Modify: `src/my_agents/controller.py:722-856` (`_run_report_synthesizer` and `_build_fallback_bundle`)

**Step 1: Rewrite the synthesizer prompt**

Replace the synthesizer prompt in `_run_report_synthesizer` with:

```python
prompt = (
    "Synthesize the VC diligence record into a structured findings bundle.\n\n"
    f"Company: {brief.company_name}\n"
    f"Workflow: {state.workflow.value}\n\n"
    "--- WRITING GUIDELINES ---\n"
    "Write like a senior VC analyst preparing an IC memo:\n"
    "- Lead with conclusions, then evidence\n"
    "- Use specific data points: numbers, dates, sources\n"
    "- No marketing language ('revolutionary', 'game-changing', 'disruptive')\n"
    "- Acknowledge gaps honestly rather than padding with vague statements\n"
    "- Each section should be 100-300 words with at least 2 specific data points\n\n"
    "--- SECTION REQUIREMENTS ---\n"
    "executive_summary: 3-4 sentences. Verdict first, then 2 key evidence points, then biggest risk.\n"
    "company_snapshot: Founded when, by whom, what they do, funding to date, stage, key metrics.\n"
    "market_landscape: TAM/SAM/SOM, 3-5 competitors named, India-specific tailwinds/headwinds.\n"
    "financial_analysis: Revenue model, growth rate, unit economics (or proxies), burn/runway.\n"
    "product_technology: What the product does, tech differentiation, IP, engineering signals.\n"
    "founder_assessment: Founder background, domain expertise, team completeness.\n"
    "gtm_momentum: GTM motion type, traction metrics, customer acquisition evidence.\n"
    "regulatory_compliance: Applicable regulations, compliance status, risks.\n"
    "risk_register: Top 3-5 risks with probability and impact assessment.\n"
    "investment_recommendation: INVEST/PASS/CONDITIONAL with 2-3 reasons for each.\n\n"
    "If a section has NO real evidence from the agents, write: "
    "'Insufficient evidence. Key gap: [what's missing].'\n\n"
    f"Scorecard: {scorecard.model_dump_json(indent=2)}\n"
    f"Audit: {audit.model_dump_json(indent=2)}\n"
    f"Findings: {json.dumps({name: result.model_dump() for name, result in state.findings.items()}, indent=2)}\n"
)
```

**Step 2: Run tests**

Run: `.venv/bin/python -m pytest tests/test_controller_flow.py -v`
Expected: All pass

**Step 3: Commit**

```bash
git add src/my_agents/controller.py
git commit -m "feat: rewrite report synthesizer with IC-ready writing guidelines"
```

---

## Task 7: Improve Renderers and Report Standards

**Files:**
- Modify: `src/my_agents/renderers/ic_memo_renderer.py`
- Modify: `src/my_agents/renderers/full_report_renderer.py`
- Modify: `src/my_agents/report_standards.py:18-28` (word ranges and citation minimums)
- Modify: `src/my_agents/config/output_profiles/ic_memo.yaml`
- Modify: `src/my_agents/config/output_profiles/full_report.yaml`

**Step 1: Update word ranges in report_standards.py**

```python
WORD_RANGES: dict[OutputProfile, tuple[int, int]] = {
    OutputProfile.IC_MEMO: (1200, 2500),
    OutputProfile.FULL_REPORT: (2500, 5000),
    OutputProfile.ONE_PAGER: (300, 800),
}

MIN_CITATIONS: dict[OutputProfile, int] = {
    OutputProfile.IC_MEMO: 5,
    OutputProfile.FULL_REPORT: 10,
    OutputProfile.ONE_PAGER: 4,
}
```

**Step 2: Add more sections to IC memo output profile**

Update `config/output_profiles/ic_memo.yaml`:

```yaml
profile: ic_memo
title: "IC Memo"
format: markdown
sections:
  - executive_summary
  - company_snapshot
  - market_landscape
  - financial_analysis
  - investment_recommendation
  - scorecard_summary
  - top_signals
  - top_risks
  - open_questions
  - evidence_gaps
```

**Step 3: Update IC memo renderer for richer output**

Update `renderers/ic_memo_renderer.py` to include a company snapshot table and more structured sections.

**Step 4: Update full report renderer**

Add formatted metrics tables, section headers with word targets, and evidence gap callouts.

**Step 5: Run renderer tests**

Run: `.venv/bin/python -m pytest tests/test_renderers.py tests/test_report_standards.py -v`
Expected: All pass (may need test updates for new section expectations)

**Step 6: Commit**

```bash
git add src/my_agents/renderers/ src/my_agents/report_standards.py src/my_agents/config/output_profiles/
git commit -m "feat: improve report renderers with richer formatting and updated word targets"
```

---

## Task 8: Update LLM Configuration

**Files:**
- Modify: `src/my_agents/config/llm.yaml`

**Step 1: Update llm.yaml with better model and higher max_tokens**

```yaml
provider: openrouter
model: openrouter/deepseek/deepseek-r1
base_url: https://openrouter.ai/api/v1
api_key_env: OPENROUTER_API_KEY
temperature: 0.2
max_tokens: 12000
open_source_only: true
allow_closed_models: false
allowed_model_prefixes:
  - deepseek/
  - openrouter/deepseek/
  - meta-llama/
  - openrouter/meta-llama/
  - qwen/
  - openrouter/qwen/
  - gemma
  - openrouter/google/gemma
  - mistral/
  - openrouter/mistral/
  - mixtral
  - granite
  - phi-
  - falcon
  - olmo
  - nemotron

# Model selection guide:
# Research agents (need reasoning + tool use):
#   - openrouter/deepseek/deepseek-r1 (best reasoning, very cheap)
#   - openrouter/qwen/qwen3-235b-a22b (strong structured output)
#   - openrouter/deepseek/deepseek-v3.2 (fast, cheaper, less reasoning)
#
# Evaluation model (LLM-as-a-judge):
#   - openrouter/meta-llama/llama-3.3-70b-instruct (reliable JSON, cheap)
eval_model: openrouter/meta-llama/llama-3.3-70b-instruct
```

**Step 2: Commit**

```bash
git add src/my_agents/config/llm.yaml
git commit -m "feat: upgrade to DeepSeek R1 with 12K max tokens for better reasoning"
```

---

## Task 9: Strengthen Evidence Auditor

**Files:**
- Modify: `src/my_agents/evidence.py`

**Step 1: Add circular reasoning detection and score inflation checks**

Add to `deterministic_audit()`:

```python
# Check for circular reasoning (citing the brief as evidence)
brief_source_patterns = {"brief://", "company brief", "as stated in the brief"}
for finding in findings:
    if any(pat in finding.source_ref.lower() for pat in brief_source_patterns):
        issues.append(
            AuditIssue(
                title="Circular reasoning",
                severity=RiskLevel.MEDIUM,
                detail=f"Finding '{finding.claim}' cites the brief as evidence.",
            )
        )

# Check for score inflation
for agent_result in self.findings_by_agent.values():
    if agent_result.dimension_scores:
        avg_score = sum(s.score for s in agent_result.dimension_scores) / len(agent_result.dimension_scores)
        avg_confidence = (
            sum(f.confidence for f in agent_result.findings) / len(agent_result.findings)
            if agent_result.findings else 0
        )
        if avg_score >= 4.0 and avg_confidence < 0.6:
            issues.append(
                AuditIssue(
                    title="Score inflation",
                    severity=RiskLevel.MEDIUM,
                    detail=f"Agent '{agent_result.agent_name}' gave high scores (avg {avg_score:.1f}) despite low confidence ({avg_confidence:.2f}).",
                )
            )
```

**Step 2: Run tests**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: All pass

**Step 3: Commit**

```bash
git add src/my_agents/evidence.py
git commit -m "feat: add circular reasoning and score inflation detection to evidence auditor"
```

---

## Task 10: Update Tests for New Behavior

**Files:**
- Modify: `tests/test_controller_flow.py` (update for chroma_collection parameter)
- Modify: `tests/test_renderers.py` (update for new sections in IC memo)
- Modify: `tests/test_report_standards.py` (update for new word ranges)
- Modify: `tests/test_eval_benchmarks.py` (update expected eval score if needed)

**Step 1: Fix any tests broken by the changes**

Run the full suite and fix each failure:

Run: `.venv/bin/python -m pytest tests/ -v --tb=long`

Fix each test to match updated behavior:
- `test_renderers.py`: IC memo now includes `company_snapshot` and `evidence_gaps` sections
- `test_report_standards.py`: word ranges are wider (1200-2500 for IC memo)
- `test_eval_benchmarks.py`: expected eval score may change due to finalize_rubric weights

**Step 2: Run full suite and confirm green**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: All pass

**Step 3: Commit**

```bash
git add tests/
git commit -m "test: update test suite for research quality overhaul"
```

---

## Task 11: Update Documentation

**Files:**
- Modify: `my_agents/README.md`

**Step 1: Update README with new setup and architecture**

Update the README with:
- New API keys section (OPENROUTER_API_KEY, TAVILY_API_KEY, SERPER_API_KEY)
- Model selection guide
- Updated architecture description
- RAG capability documentation
- Example runs and expected output quality

**Step 2: Commit**

```bash
git add README.md
git commit -m "docs: update README with Tavily, RAG, and model selection guide"
```

---

## Task 12: End-to-End Validation

**Step 1: Run full test suite one final time**

Run: `.venv/bin/python -m pytest tests/ -v`
Expected: All tests pass

**Step 2: Verify with a manual quick test (if API keys available)**

Run:
```bash
.venv/bin/python -m my_agents --company "Zerodha" --workflow sourcing --output-profile ic_memo --verbose
```

Check that:
- No agents fail completely
- Report has specific data points
- Scorecard has non-zero dimension scores
- Eval score (if run with --run-evals) is >50

---

## Summary of Changes

| # | Component | Impact |
|---|-----------|--------|
| 1 | Install Tavily | Dependency |
| 2 | Fix runner | Agents stop crashing |
| 3 | Add Tavily tools | Deep web research |
| 4 | Add RAG/ChromaDB | Document + cross-agent search |
| 5 | Rewrite prompts | VC-grade research frameworks |
| 6 | Fix synthesizer | IC-ready report writing |
| 7 | Fix renderers | Richer report output |
| 8 | Update LLM config | Better model + more tokens |
| 9 | Strengthen auditor | Better reflection |
| 10 | Update tests | Green suite |
| 11 | Documentation | Setup + architecture docs |
| 12 | E2E validation | Verify everything works |
