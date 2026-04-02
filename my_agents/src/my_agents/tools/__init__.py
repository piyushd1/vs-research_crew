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
        and not os.environ.get("TAVILY_API_KEY")  # Don't double-up if Tavily is available
    ):
        try:
            from crewai_tools import SerperDevTool
            tools.append(SerperDevTool())
        except Exception:
            pass

    return tools
