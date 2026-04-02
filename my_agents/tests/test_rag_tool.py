from __future__ import annotations

import tempfile
import unittest

from my_agents.tools.rag_tool import (
    DataRoomSearchTool,
    DocumentIndexer,
    _chunk_text,
)


class ChunkTextTests(unittest.TestCase):
    def test_empty_string_returns_empty_list(self) -> None:
        self.assertEqual(_chunk_text(""), [])

    def test_whitespace_only_returns_empty_list(self) -> None:
        self.assertEqual(_chunk_text("   "), [])

    def test_short_text_returns_single_chunk(self) -> None:
        result = _chunk_text("hello world")
        self.assertEqual(len(result), 1)
        self.assertIn("hello world", result[0])

    def test_long_text_produces_overlapping_chunks(self) -> None:
        text = " ".join(f"word{i}" for i in range(100))
        chunks = _chunk_text(text, chunk_size=30, overlap=5)
        self.assertGreater(len(chunks), 1)


class RAGToolTests(unittest.TestCase):
    def test_indexer_creates_collection_and_searches(self) -> None:
        """Index text and query it."""
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

    def test_agent_findings_are_searchable(self) -> None:
        indexer = DocumentIndexer()
        collection = indexer.create_collection("findings-test")
        indexer.index_agent_findings(
            collection,
            agent_name="financial_researcher",
            summary="Revenue grew 50% YoY",
            findings_text="- Revenue: 50 crores (confidence: 0.8, source: MCA filing)",
        )
        tool = DataRoomSearchTool(collection=collection)
        result = tool._run(query="revenue growth")
        self.assertIn("financial_researcher", result)


if __name__ == "__main__":
    unittest.main()
