from __future__ import annotations

import os
from pathlib import Path

from my_agents.schemas import Brief, SourcePriorityConfig


def build_tools(
    brief: Brief,
    source_profile: SourcePriorityConfig,
    agent_name: str,
) -> list[object]:
    from my_agents.tools.custom_tool import (
        CSVPreviewTool,
        DirectoryManifestTool,
        IndiaSourceRegistryTool,
        PDFExcerptTool,
    )

    tools: list[object] = [
        IndiaSourceRegistryTool(),
    ]

    if brief.docs_dir:
        docs_path = Path(brief.docs_dir)
        if docs_path.exists():
            tools.extend([DirectoryManifestTool(), PDFExcerptTool(), CSVPreviewTool()])

    if source_profile.search_provider == "serper" and os.environ.get("SERPER_API_KEY"):
        try:
            from crewai_tools import SerperDevTool

            tools.append(SerperDevTool())
        except Exception:
            pass

    return tools
