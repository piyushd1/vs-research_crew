from __future__ import annotations

import csv
import hashlib
from pathlib import Path
import re
from typing import Any

import chromadb
from crewai.tools import BaseTool
import pdfplumber
from pydantic import BaseModel, ConfigDict, Field


def _chunk_text(text: str, chunk_size: int = 500, overlap: int = 50) -> list[str]:
    """Split *text* into overlapping chunks by word count.

    Returns an empty list when *text* is empty or whitespace-only.
    """
    if not text or not text.strip():
        return []

    words = text.split()
    if len(words) <= chunk_size:
        return [text.strip()]

    chunks: list[str] = []
    start = 0
    while start < len(words):
        end = start + chunk_size
        chunk = " ".join(words[start:end])
        chunks.append(chunk)
        start += chunk_size - overlap
    return chunks


def _sanitize_collection_name(name: str) -> str:
    """Sanitize *name* to a valid ChromaDB collection name (3-63 chars, alphanumeric + dashes)."""
    sanitized = re.sub(r"[^a-zA-Z0-9-]", "-", name)
    # Collapse consecutive dashes
    sanitized = re.sub(r"-{2,}", "-", sanitized)
    # Strip leading/trailing dashes
    sanitized = sanitized.strip("-")
    # Ensure minimum length of 3
    if len(sanitized) < 3:
        sanitized = sanitized + "-" * (3 - len(sanitized)) + "col"
    # Truncate to 63 characters
    sanitized = sanitized[:63]
    # Strip trailing dashes after truncation
    sanitized = sanitized.rstrip("-")
    # Ensure still at least 3 chars after rstrip
    if len(sanitized) < 3:
        sanitized = sanitized + "col"
    return sanitized


class DocumentIndexer:
    """Manages ChromaDB collections for indexing data-room documents and agent findings."""

    def __init__(self) -> None:
        self.client = chromadb.Client()

    def create_collection(self, run_id: str) -> chromadb.Collection:
        """Create or retrieve a ChromaDB collection for *run_id*."""
        name = _sanitize_collection_name(run_id)
        return self.client.get_or_create_collection(name=name)

    def index_text(
        self,
        collection: chromadb.Collection,
        text: str,
        source: str,
        page: int | None = None,
        agent_name: str | None = None,
    ) -> int:
        """Chunk *text* and add to *collection* with metadata. Returns chunk count."""
        chunks = _chunk_text(text)
        if not chunks:
            return 0

        ids: list[str] = []
        documents: list[str] = []
        metadatas: list[dict[str, Any]] = []

        for idx, chunk in enumerate(chunks):
            doc_id = hashlib.sha256(f"{source}:{idx}".encode()).hexdigest()
            meta: dict[str, Any] = {"source": source}
            if page is not None:
                meta["page"] = page
            if agent_name:
                meta["agent"] = agent_name
            ids.append(doc_id)
            documents.append(chunk)
            metadatas.append(meta)

        collection.add(ids=ids, documents=documents, metadatas=metadatas)
        return len(chunks)

    def index_docs_dir(self, collection: chromadb.Collection, docs_dir: str) -> int:
        """Index all PDFs and CSVs from *docs_dir*. Returns total chunk count."""
        root = Path(docs_dir)
        if not root.exists():
            return 0

        total = 0

        # Index PDFs (all pages)
        for pdf_path in sorted(root.rglob("*.pdf")):
            try:
                with pdfplumber.open(pdf_path) as pdf:
                    for page_num, page in enumerate(pdf.pages, start=1):
                        page_text = page.extract_text() or ""
                        if page_text.strip():
                            total += self.index_text(
                                collection,
                                text=page_text,
                                source=str(pdf_path.name),
                                page=page_num,
                            )
            except Exception:
                continue

        # Index CSVs
        for csv_path in sorted(root.rglob("*.csv")):
            try:
                with csv_path.open("r", encoding="utf-8-sig", newline="") as handle:
                    reader = csv.reader(handle)
                    rows = list(reader)
                if rows:
                    text = "\n".join(" | ".join(row) for row in rows)
                    total += self.index_text(
                        collection,
                        text=text,
                        source=str(csv_path.name),
                    )
            except Exception:
                continue

        return total

    def index_agent_findings(
        self,
        collection: chromadb.Collection,
        agent_name: str,
        summary: str,
        findings_text: str,
    ) -> int:
        """Index agent output for cross-agent RAG. Returns chunk count."""
        combined = f"[{agent_name}] Summary: {summary}\n\n{findings_text}"
        return self.index_text(
            collection,
            text=combined,
            source=f"agent:{agent_name}",
            agent_name=agent_name,
        )


class DataRoomSearchInput(BaseModel):
    query: str = Field(..., description="Semantic search query.")
    n_results: int = Field(
        5,
        ge=1,
        le=10,
        description="Number of results to return (1-10).",
    )


class DataRoomSearchTool(BaseTool):
    """Semantic search over uploaded diligence documents and prior agent findings."""

    name: str = "data_room_search"
    description: str = (
        "Semantic search over uploaded diligence documents (PDFs, CSVs) "
        "and prior agent findings."
    )
    args_schema: type[BaseModel] = DataRoomSearchInput
    collection: Any = None

    model_config = ConfigDict(arbitrary_types_allowed=True)

    def _run(self, query: str, n_results: int = 5) -> str:
        if self.collection is None:
            return f"No relevant documents found for: {query}"

        try:
            count = self.collection.count()
        except Exception:
            count = 0

        if count == 0:
            return f"No relevant documents found for: {query}"

        # Clamp n_results to available documents
        actual_n = min(n_results, count)

        results = self.collection.query(
            query_texts=[query],
            n_results=actual_n,
        )

        documents = results.get("documents", [[]])[0]
        metadatas = results.get("metadatas", [[]])[0]
        distances = results.get("distances", [[]])[0]

        if not documents:
            return f"No relevant documents found for: {query}"

        lines: list[str] = [f"Search results for: {query}\n"]
        for i, (doc, meta, dist) in enumerate(zip(documents, metadatas, distances), 1):
            source = meta.get("source", "unknown")
            relevance = round(1.0 / (1.0 + dist), 3)
            attribution_parts = [f"source: {source}"]
            if "page" in meta:
                attribution_parts.append(f"page: {meta['page']}")
            if "agent" in meta:
                attribution_parts.append(f"agent: {meta['agent']}")
            attribution_parts.append(f"relevance: {relevance}")
            attribution = " | ".join(attribution_parts)

            lines.append(f"[{i}] ({attribution})")
            # Truncate long chunks for readability
            snippet = doc[:500] + "..." if len(doc) > 500 else doc
            lines.append(snippet)
            lines.append("")

        return "\n".join(lines).strip()
