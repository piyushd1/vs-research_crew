from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from my_agents.tools.tavily_tool import (
    TavilyExtractTool,
    TavilyResearchTool,
    TavilySearchTool,
)


class TavilyToolIdentityTests(unittest.TestCase):
    """Verify each tool exists and has the correct name."""

    def test_search_tool_name(self) -> None:
        tool = TavilySearchTool()
        self.assertEqual(tool.name, "tavily_search")

    def test_extract_tool_name(self) -> None:
        tool = TavilyExtractTool()
        self.assertEqual(tool.name, "tavily_extract")

    def test_research_tool_name(self) -> None:
        tool = TavilyResearchTool()
        self.assertEqual(tool.name, "tavily_research")


class TavilyMissingKeyTests(unittest.TestCase):
    """All tools must return a clear message when TAVILY_API_KEY is absent."""

    def _env_without_tavily(self) -> dict[str, str]:
        env = os.environ.copy()
        env.pop("TAVILY_API_KEY", None)
        return env

    def test_search_missing_key(self) -> None:
        with patch.dict(os.environ, self._env_without_tavily(), clear=True):
            tool = TavilySearchTool()
            result = tool._run(query="test query")
        self.assertEqual(result, "TAVILY_API_KEY is not configured.")

    def test_extract_missing_key(self) -> None:
        with patch.dict(os.environ, self._env_without_tavily(), clear=True):
            tool = TavilyExtractTool()
            result = tool._run(url="https://example.com")
        self.assertEqual(result, "TAVILY_API_KEY is not configured.")

    def test_research_missing_key(self) -> None:
        with patch.dict(os.environ, self._env_without_tavily(), clear=True):
            tool = TavilyResearchTool()
            result = tool._run(topic="AI startups India")
        self.assertEqual(result, "TAVILY_API_KEY is not configured.")


class TavilyBuildToolsIntegrationTests(unittest.TestCase):
    """Verify build_tools includes tavily_search for non-internal agents when key is set.

    NOTE: This test validates the *tool objects* themselves; the actual
    wiring into build_tools will be done in a separate task. We import
    build_tools but only test that the Tavily tools are importable and
    well-formed enough to be added to any tool list.
    """

    def test_tavily_tools_are_instantiable_with_key_set(self) -> None:
        """When TAVILY_API_KEY is present the tools can be constructed and
        would be suitable for inclusion in a build_tools result."""
        with patch.dict(os.environ, {"TAVILY_API_KEY": "test-key"}, clear=False):
            search = TavilySearchTool()
            extract = TavilyExtractTool()
            research = TavilyResearchTool()

        self.assertEqual(search.name, "tavily_search")
        self.assertEqual(extract.name, "tavily_extract")
        self.assertEqual(research.name, "tavily_research")

        # Verify they are BaseTool instances (compatible with build_tools list)
        from crewai.tools import BaseTool

        self.assertIsInstance(search, BaseTool)
        self.assertIsInstance(extract, BaseTool)
        self.assertIsInstance(research, BaseTool)


if __name__ == "__main__":
    unittest.main()
