from __future__ import annotations

import os
import types
import unittest
from unittest.mock import patch

from my_agents.schemas import Brief, SourcePriorityConfig
from my_agents.tools import build_tools


class DummySerperDevTool:
    name = "search_the_internet_with_serper"


class ToolSelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.brief = Brief(company_name="Razorpay", website="https://razorpay.com", sector="fintech")
        self.source_profile = SourcePriorityConfig(
            profile="fintech",
            tiers={"company_site": 1},
            search_provider="serper",
        )

    def test_financial_researcher_uses_financial_signal_tool(self) -> None:
        with patch.dict(os.environ, {"SERPER_API_KEY": "test-key"}, clear=False):
            tools = build_tools(self.brief, self.source_profile, "financial_researcher")
        tool_names = [getattr(tool, "name", type(tool).__name__) for tool in tools]
        self.assertIn("financial_signal_search", tool_names)
        self.assertNotIn("search_the_internet_with_serper", tool_names)

    def test_non_financial_agent_uses_generic_serper_tool(self) -> None:
        dummy_module = types.SimpleNamespace(SerperDevTool=DummySerperDevTool)
        with patch.dict(os.environ, {"SERPER_API_KEY": "test-key"}, clear=False):
            with patch.dict("sys.modules", {"crewai_tools": dummy_module}):
                tools = build_tools(self.brief, self.source_profile, "market_mapper")
        tool_names = [getattr(tool, "name", type(tool).__name__) for tool in tools]
        self.assertIn("search_the_internet_with_serper", tool_names)
        self.assertNotIn("financial_signal_search", tool_names)


if __name__ == "__main__":
    unittest.main()
