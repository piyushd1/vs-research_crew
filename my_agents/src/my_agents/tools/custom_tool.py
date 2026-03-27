from __future__ import annotations

import csv
from pathlib import Path
from typing import Type

import pdfplumber
from crewai.tools import BaseTool
from pydantic import BaseModel, Field


class DirectoryManifestInput(BaseModel):
    path: str = Field(..., description="Directory path to inspect.")


class DirectoryManifestTool(BaseTool):
    name: str = "directory_manifest"
    description: str = "Lists PDF and CSV files in a data room directory."
    args_schema: Type[BaseModel] = DirectoryManifestInput

    def _run(self, path: str) -> str:
        root = Path(path)
        if not root.exists():
            return f"Directory not found: {path}"
        files = sorted(
            str(item)
            for item in root.rglob("*")
            if item.is_file() and item.suffix.lower() in {".pdf", ".csv"}
        )
        return "\n".join(files) if files else "No supported files found."


class PDFExcerptInput(BaseModel):
    path: str = Field(..., description="Path to a PDF file.")
    max_pages: int = Field(3, description="Maximum number of pages to read.")


class PDFExcerptTool(BaseTool):
    name: str = "pdf_excerpt"
    description: str = "Extracts text from the first few pages of a PDF file."
    args_schema: Type[BaseModel] = PDFExcerptInput

    def _run(self, path: str, max_pages: int = 3) -> str:
        pdf_path = Path(path)
        if not pdf_path.exists():
            return f"PDF not found: {path}"
        output: list[str] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages[:max_pages]:
                output.append(page.extract_text() or "")
        return "\n".join(output).strip() or "No text extracted."


class CSVPreviewInput(BaseModel):
    path: str = Field(..., description="Path to a CSV file.")
    rows: int = Field(5, description="How many rows to preview.")


class CSVPreviewTool(BaseTool):
    name: str = "csv_preview"
    description: str = "Returns CSV headers and a small preview for diligence review."
    args_schema: Type[BaseModel] = CSVPreviewInput

    def _run(self, path: str, rows: int = 5) -> str:
        csv_path = Path(path)
        if not csv_path.exists():
            return f"CSV not found: {path}"
        with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
            reader = csv.reader(handle)
            data = list(reader)
        if not data:
            return "CSV is empty."
        header = data[0]
        sample_rows = data[1 : rows + 1]
        rendered_rows = [" | ".join(row) for row in sample_rows]
        return "\n".join(
            [
                f"Headers: {' | '.join(header)}",
                "Sample rows:",
                *rendered_rows,
            ]
        )


class IndiaSourceRegistryInput(BaseModel):
    workflow: str = Field(..., description="Workflow name.")
    sector: str = Field(..., description="Sector being analyzed.")
    agent_name: str = Field(..., description="Specialist agent name.")


class IndiaSourceRegistryTool(BaseTool):
    name: str = "india_source_registry"
    description: str = "Returns India-first public source guidance for the given workflow and agent."
    args_schema: Type[BaseModel] = IndiaSourceRegistryInput

    def _run(self, workflow: str, sector: str, agent_name: str) -> str:
        founder_signal = [
            "MCA / ROC filings",
            "IP India",
            "SEBI / BSE / NSE disclosures",
            "Startup India / DPIIT",
            "Inc42 / YourStory / Entrackr / ET Startup / The Ken",
            "GitHub",
            "Google Scholar / Semantic Scholar",
            "NCLT / IBC / public court databases",
        ]
        common = [
            "Company website and product pages",
            "Government and regulatory filings",
            "Audited financials and uploaded data room documents",
            "Indian business media and startup databases",
        ]
        lines = [
            f"Workflow: {workflow}",
            f"Sector: {sector}",
            f"Agent: {agent_name}",
            "India-first source order:",
            *[f"- {item}" for item in common],
        ]
        if agent_name == "founder_signal_analyst":
            lines.extend(["Founder signal fallback hierarchy:"])
            lines.extend(f"- {item}" for item in founder_signal)
        return "\n".join(lines)
