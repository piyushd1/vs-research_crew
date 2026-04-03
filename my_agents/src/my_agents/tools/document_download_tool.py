"""Tool that lets agents download financial documents (PDFs, CSVs) from
the web, save them to the run directory, extract text, and index into
the ChromaDB vector store so the synthesizer can use them.

Designed for:
- Annual reports from BSE/NSE investor relations pages
- MCA financial statements
- Company-published PDFs (pitch decks, press kits)
- Quarterly results PDFs
"""
from __future__ import annotations

import hashlib
import os
import re
from pathlib import Path
from typing import Any
from urllib import error, parse, request

from crewai.tools import BaseTool
from pydantic import BaseModel, ConfigDict, Field


class DocumentDownloadInput(BaseModel):
    url: str = Field(
        ...,
        description=(
            "Direct URL to a PDF or CSV document to download. "
            "Must end in .pdf or .csv, or be a URL that serves a document. "
            "Example: 'https://www.bseindia.com/bseplus/AnnualReport/123456/5001234560.pdf'"
        ),
    )
    description: str = Field(
        default="",
        description=(
            "Brief description of what this document is (e.g., 'FY2024 Annual Report', "
            "'Q3 Quarterly Results', 'Investor Presentation')."
        ),
    )


class DocumentDownloadTool(BaseTool):
    """Downloads a PDF/CSV from a URL, saves it to the run's downloads/
    directory, extracts text, and indexes into the ChromaDB vector store.

    Returns a summary of what was extracted so the agent can use the data.
    """

    name: str = "download_document"
    description: str = (
        "Downloads a financial document (PDF or CSV) from a URL, saves it locally, "
        "extracts its text content, and indexes it for semantic search. "
        "Use this when you find a link to an annual report, quarterly results, "
        "investor presentation, or any other useful document during research. "
        "The extracted content becomes searchable via data_room_search. "
        "Returns a summary of the extracted content."
    )
    args_schema: type[BaseModel] = DocumentDownloadInput

    # These are set by the controller when building tools
    downloads_dir: str | None = None
    chroma_collection: Any = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _safe_filename(self, url: str) -> str:
        """Generate a safe filename from a URL."""
        parsed = parse.urlparse(url)
        path = parsed.path.rstrip("/")
        basename = path.split("/")[-1] if "/" in path else path
        # Clean the filename
        basename = re.sub(r"[^\w.\-]", "_", basename)
        if not basename or basename == "_":
            url_hash = hashlib.md5(url.encode()).hexdigest()[:10]
            basename = f"document_{url_hash}.pdf"
        # Ensure it has an extension
        if not any(basename.lower().endswith(ext) for ext in (".pdf", ".csv", ".xlsx")):
            basename += ".pdf"
        return basename

    def _download_file(self, url: str, dest: Path) -> Path:
        """Download a file from URL to the destination path."""
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
        }
        req = request.Request(url, headers=headers, method="GET")
        with request.urlopen(req, timeout=45) as response:
            dest.write_bytes(response.read())
        return dest

    def _extract_pdf_text(self, path: Path) -> str:
        """Extract all text from a PDF using pdfplumber."""
        try:
            import pdfplumber

            pages_text: list[str] = []
            with pdfplumber.open(path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if text and text.strip():
                        pages_text.append(f"[Page {page_num}]\n{text}")
            return "\n\n".join(pages_text) if pages_text else "No text extracted from PDF."
        except Exception as exc:
            return f"PDF text extraction failed: {exc}"

    def _extract_csv_text(self, path: Path) -> str:
        """Read CSV and return as formatted text."""
        import csv

        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.reader(handle)
                rows = list(reader)
            if not rows:
                return "CSV is empty."
            header = rows[0]
            text_rows = [" | ".join(header)]
            for row in rows[1:]:
                text_rows.append(" | ".join(row))
            return "\n".join(text_rows)
        except Exception as exc:
            return f"CSV extraction failed: {exc}"

    def _index_into_rag(self, text: str, source_name: str) -> int:
        """Index extracted text into ChromaDB collection. Returns chunk count."""
        if self.chroma_collection is None:
            return 0
        try:
            from my_agents.tools.rag_tool import DocumentIndexer

            indexer = DocumentIndexer()
            return indexer.index_text(
                self.chroma_collection,
                text=text,
                source=f"downloaded:{source_name}",
            )
        except Exception:
            return 0

    def _run(self, url: str, description: str = "") -> str:
        # Validate we have a downloads directory
        if not self.downloads_dir:
            return "Download directory not configured. Cannot save documents."

        downloads_path = Path(self.downloads_dir)
        downloads_path.mkdir(parents=True, exist_ok=True)

        # Generate safe filename
        filename = self._safe_filename(url)
        dest_path = downloads_path / filename

        # Download the file
        try:
            self._download_file(url, dest_path)
        except error.URLError as exc:
            return f"Download failed for {url}: {exc}"
        except Exception as exc:
            return f"Download error: {exc}"

        file_size = dest_path.stat().st_size
        if file_size == 0:
            dest_path.unlink(missing_ok=True)
            return f"Downloaded file is empty (0 bytes): {url}"

        size_kb = file_size / 1024
        desc_label = f" ({description})" if description else ""

        # Extract text based on file type
        if dest_path.suffix.lower() == ".csv":
            extracted_text = self._extract_csv_text(dest_path)
        else:
            extracted_text = self._extract_pdf_text(dest_path)

        if not extracted_text or extracted_text.startswith("No text") or extracted_text.startswith("PDF text"):
            return (
                f"Downloaded {filename}{desc_label} ({size_kb:.0f} KB) but could not extract text. "
                f"The file may be a scanned image PDF. Saved to: {dest_path}"
            )

        # Index into RAG
        chunks_indexed = self._index_into_rag(extracted_text, filename)

        # Return a summary of the extracted content
        preview = extracted_text[:3000]
        lines = [
            f"Downloaded and indexed: {filename}{desc_label}",
            f"Size: {size_kb:.0f} KB | Text extracted: {len(extracted_text)} chars | RAG chunks: {chunks_indexed}",
            f"Saved to: {dest_path}",
            "",
            "Content preview:",
            preview,
        ]
        if len(extracted_text) > 3000:
            lines.append(f"\n[... truncated, {len(extracted_text) - 3000} more chars. Use data_room_search to query specific data.]")

        return "\n".join(lines)
