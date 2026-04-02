from __future__ import annotations

import json
import os
from urllib import error, request

from crewai.tools import BaseTool
from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Input schemas
# ---------------------------------------------------------------------------


class TavilySearchInput(BaseModel):
    query: str = Field(
        ...,
        description=(
            "Search query string. ALWAYS include the company name and 'India' in your query "
            "to get India-relevant results. Example: '\"Razorpay\" India revenue funding'."
        ),
    )
    search_depth: str = Field(
        "advanced",
        description="Search depth: 'basic' or 'advanced'.",
    )


class TavilyExtractInput(BaseModel):
    url: str = Field(..., description="URL to extract content from.")


class TavilyResearchInput(BaseModel):
    topic: str = Field(
        ...,
        description=(
            "Research topic or question. ALWAYS include the company name and 'India' context. "
            "Example: '\"Zerodha\" India fintech market position revenue growth'."
        ),
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TAVILY_SEARCH_URL = "https://api.tavily.com/search"
_TAVILY_EXTRACT_URL = "https://api.tavily.com/extract"


def _get_api_key() -> str | None:
    return os.environ.get("TAVILY_API_KEY") or None


def _post_json(url: str, payload: dict, timeout: int = 30) -> dict:
    """POST *payload* as JSON to *url* and return the decoded response."""
    data = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Tools
# ---------------------------------------------------------------------------


class TavilySearchTool(BaseTool):
    """Deep web search via the Tavily Search API."""

    name: str = "tavily_search"
    description: str = (
        "Deep web search for Indian startup and company research. Returns up to 8 results "
        "with title, URL, content snippet, and relevance score. Always include 'India' in "
        "your query to get India-relevant results."
    )
    args_schema: type[BaseModel] = TavilySearchInput

    def _run(self, query: str, search_depth: str = "advanced") -> str:
        api_key = _get_api_key()
        if not api_key:
            return "TAVILY_API_KEY is not configured."

        # Auto-append India context if not already present
        india_query = query if "india" in query.lower() else f"{query} India"

        payload = {
            "api_key": api_key,
            "query": india_query,
            "search_depth": search_depth,
            "max_results": 8,
        }
        try:
            data = _post_json(_TAVILY_SEARCH_URL, payload)
        except error.URLError as exc:
            return f"Tavily search request failed: {exc}"

        results = data.get("results", [])
        if not results:
            return f"No results found for: {query}"

        lines: list[str] = [f"Tavily search results for: {query}"]
        for item in results:
            title = item.get("title", "Untitled")
            url = item.get("url", "")
            content = item.get("content", "")
            score = item.get("score", "")
            lines.append(f"- {title} | {url} (score: {score})")
            if content:
                lines.append(f"  {content}")
        return "\n".join(lines)


class TavilyExtractTool(BaseTool):
    """Extracts full page content from a URL via the Tavily Extract API."""

    name: str = "tavily_extract"
    description: str = (
        "Extracts the full textual content of a web page using Tavily. "
        "Returns up to 8000 characters of extracted content."
    )
    args_schema: type[BaseModel] = TavilyExtractInput

    def _run(self, url: str) -> str:
        api_key = _get_api_key()
        if not api_key:
            return "TAVILY_API_KEY is not configured."

        payload = {
            "api_key": api_key,
            "urls": [url],
        }
        try:
            data = _post_json(_TAVILY_EXTRACT_URL, payload)
        except error.URLError as exc:
            return f"Tavily extract request failed: {exc}"

        results = data.get("results", [])
        if not results:
            return f"No content extracted from: {url}"

        raw_content = results[0].get("raw_content", "")
        if not raw_content:
            raw_content = results[0].get("content", "")

        truncated = raw_content[:8000]
        lines = [
            f"Extracted content from: {url}",
            f"Length: {len(raw_content)} chars (showing first {len(truncated)})",
            "",
            truncated,
        ]
        return "\n".join(lines)


class TavilyResearchTool(BaseTool):
    """Comprehensive research on a topic via Tavily advanced search."""

    name: str = "tavily_research"
    description: str = (
        "Comprehensive research on an Indian company or market topic. Uses advanced search "
        "with up to 10 results and an AI-generated summary. Always include 'India' in "
        "your topic to get India-relevant results."
    )
    args_schema: type[BaseModel] = TavilyResearchInput

    def _run(self, topic: str) -> str:
        api_key = _get_api_key()
        if not api_key:
            return "TAVILY_API_KEY is not configured."

        # Auto-append India context if not already present
        india_topic = topic if "india" in topic.lower() else f"{topic} India"

        payload = {
            "api_key": api_key,
            "query": india_topic,
            "search_depth": "advanced",
            "max_results": 10,
            "include_answer": True,
        }
        try:
            data = _post_json(_TAVILY_SEARCH_URL, payload)
        except error.URLError as exc:
            return f"Tavily research request failed: {exc}"

        lines: list[str] = [f"Research results for: {topic}"]

        answer = data.get("answer")
        if answer:
            lines.append("")
            lines.append("Summary:")
            lines.append(answer)

        results = data.get("results", [])
        if results:
            lines.append("")
            lines.append("Sources:")
            for item in results:
                title = item.get("title", "Untitled")
                url = item.get("url", "")
                content = item.get("content", "")
                score = item.get("score", "")
                lines.append(f"- {title} | {url} (score: {score})")
                if content:
                    lines.append(f"  {content}")
        elif not answer:
            lines.append(f"No results found for: {topic}")

        return "\n".join(lines)
