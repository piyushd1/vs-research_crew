from __future__ import annotations

import csv
from pathlib import Path

from crewai.tools import BaseTool
import pdfplumber
from pydantic import BaseModel, Field

from my_agents.configuration import canonicalize_profile_key


SECTOR_SOURCE_HINTS = {
    "agritech": [
        "Ministry of Agriculture, NABARD, eNAM, and Agri Stack policy references",
        "State agriculture departments, mandi data, and FPO ecosystem references",
        "On-ground distribution, field deployment, and procurement evidence",
    ],
    "climate": [
        "MNRE, state power regulators, and public energy transition policy references",
        "Project approvals, public infrastructure references, and deployment signals",
    ],
    "consumer": [
        "App Store, Google Play, creator communities, and consumer review evidence",
        "Indian commerce, retail, and internet media",
    ],
    "cybersecurity": [
        "CERT-In, RBI, SEBI, and NPCI cyber guidance where applicable",
        "Product docs, trust centers, GitHub, and security disclosures",
    ],
    "d2c": [
        "Brand websites, catalogues, and pricing surfaces",
        "Marketplace listings and review signals from Indian commerce channels",
        "FSSAI, Legal Metrology, BIS, GST, and claim-compliance evidence",
    ],
    "deeptech": [
        "IP India, Google Scholar, arXiv, GitHub, and technical benchmark evidence",
        "MeitY, ISRO, IN-SPACe, DRDO, BIS, and certification bodies where relevant",
    ],
    "edtech": [
        "UGC, AICTE, NCVET, NSDC, and state board references",
        "Outcome evidence, learner reviews, and institutional partnerships",
    ],
    "fintech": [
        "RBI, SEBI, NPCI, and MCA / ROC references",
        "Regulated entity disclosures and rail-level ecosystem evidence",
        "NBFC, P2P lending, digital lending guidelines, and FLDG norms",
        "Credit bureau signals, UPI/BBPS adoption, and co-lending evidence",
    ],
    "healthtech": [
        "CDSCO, MoHFW, NHA, ABDM, NABH, NABL, and provider partner references",
        "Clinical validation and healthcare ecosystem evidence",
    ],
    "logistics": [
        "GST, e-way bill, FASTag, DGFT, and logistics policy references",
        "Warehouse, fleet, and corridor footprint evidence",
    ],
    "marketplaces": [
        "Buyer and seller app-store, review, and assortment signals",
        "ONDC and commerce ecosystem references where relevant",
    ],
    "proptech": [
        "RERA, municipal approvals, project records, and housing market references",
        "Developer, broker, and lender partnership evidence",
    ],
    "saas_ai": [
        "Product docs, pricing pages, trust centers, and changelogs",
        "GitHub, benchmark artifacts, customer case studies, and integration ecosystems",
    ],
    "generic": [
        "Company website, product documentation, and public filings",
        "Indian startup media (Inc42, YourStory, Entrackr, The Ken, ET Startup)",
        "Government and regulatory disclosures relevant to the sector",
        "MCA / ROC filings, industry reports, and press coverage",
    ],
}


class DirectoryManifestInput(BaseModel):
    path: str = Field(..., description="Directory path to inspect.")


class DirectoryManifestTool(BaseTool):
    name: str = "directory_manifest"
    description: str = "Lists PDF and CSV files in a data room directory."
    args_schema: type[BaseModel] = DirectoryManifestInput
    docs_root: str | None = None

    def _resolve_root(self, path: str) -> Path:
        candidate = Path(path)
        if candidate.exists():
            return candidate
        if self.docs_root:
            docs_root = Path(self.docs_root)
            if path.strip() in {".", "./", "/data", "/data_room", "data", "docs"}:
                return docs_root
            relative_candidate = docs_root / path.lstrip("./")
            if relative_candidate.exists():
                return relative_candidate
            return docs_root
        return candidate

    def _run(self, path: str) -> str:
        root = self._resolve_root(path)
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
    args_schema: type[BaseModel] = PDFExcerptInput
    docs_root: str | None = None

    def _resolve_path(self, path: str) -> Path:
        candidate = Path(path)
        if candidate.exists():
            return candidate
        if self.docs_root:
            docs_root = Path(self.docs_root)
            if candidate.name:
                relative_candidate = docs_root / candidate.name
                if relative_candidate.exists():
                    return relative_candidate
            nested_matches = (
                sorted(docs_root.rglob(candidate.name)) if candidate.name else []
            )
            if nested_matches:
                return nested_matches[0]
        return candidate

    def _run(self, path: str, max_pages: int = 3) -> str:
        pdf_path = self._resolve_path(path)
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
    args_schema: type[BaseModel] = CSVPreviewInput
    docs_root: str | None = None

    def _resolve_path(self, path: str) -> Path:
        candidate = Path(path)
        if candidate.exists():
            return candidate
        if self.docs_root:
            docs_root = Path(self.docs_root)
            if candidate.name:
                relative_candidate = docs_root / candidate.name
                if relative_candidate.exists():
                    return relative_candidate
            nested_matches = (
                sorted(docs_root.rglob(candidate.name)) if candidate.name else []
            )
            if nested_matches:
                return nested_matches[0]
        return candidate

    def _run(self, path: str, rows: int = 5) -> str:
        csv_path = self._resolve_path(path)
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
    description: str = (
        "Returns India-first public source guidance for the given workflow and agent."
    )
    args_schema: type[BaseModel] = IndiaSourceRegistryInput

    def _run(self, workflow: str, sector: str, agent_name: str) -> str:
        canonical_sector = canonicalize_profile_key(sector) or sector
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
        sector_specific = SECTOR_SOURCE_HINTS.get(
            canonical_sector, SECTOR_SOURCE_HINTS.get("generic", [])
        )
        lines = [
            f"Workflow: {workflow}",
            f"Sector: {canonical_sector}",
            f"Agent: {agent_name}",
            "India-first source order:",
            *[f"- {item}" for item in common],
        ]
        if sector_specific:
            lines.extend(["Sector-specific source hints:"])
            lines.extend(f"- {item}" for item in sector_specific)
        if agent_name == "founder_signal_analyst":
            lines.extend(["Founder signal fallback hierarchy:"])
            lines.extend(f"- {item}" for item in founder_signal)
        return "\n".join(lines)
