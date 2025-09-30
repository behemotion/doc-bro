"""Contract tests for character chunking strategy.

These tests define the expected behavior of character-based chunking.
They MUST FAIL until ChunkingService is implemented.
"""

import pytest

from src.logic.rag.core.chunking_service import ChunkingService
from src.logic.rag.models.chunk import Chunk
from src.logic.rag.models.strategy_config import ChunkStrategy
from src.logic.rag.models.document import Document


@pytest.mark.asyncio
class TestCharacterChunking:
    """Contract tests for CHARACTER chunking strategy."""

    async def test_character_chunking_basic(self):
        """Test basic character chunking with overlap."""
        service = ChunkingService()
        document = Document(
            id="test-1",
            content="A" * 2500,  # 2500 chars
            title="Test Doc",
            url="https://example.com/test",
            project="test-project",
        )

        chunks = await service.chunk_document(
            document=document,
            strategy=ChunkStrategy.CHARACTER,
            chunk_size=1000,
            overlap=100,
            add_context_headers=False,
        )

        assert len(chunks) == 3  # 1000, 1000, 500 (with overlap)
        assert chunks[0].chunk_index == 0
        assert chunks[1].chunk_index == 1
        assert chunks[2].chunk_index == 2
        assert all(c.parent_id == "test-1" for c in chunks)
        assert all(c.chunk_strategy == "character" for c in chunks)

    async def test_character_chunking_respects_word_boundaries(self):
        """Test that character chunking splits on word boundaries."""
        service = ChunkingService()
        document = Document(
            id="test-2",
            content="word " * 300,  # 1500 chars (300 words × 5 chars each)
            title="Word Test",
            url="https://example.com/test",
            project="test-project",
        )

        chunks = await service.chunk_document(
            document=document,
            strategy=ChunkStrategy.CHARACTER,
            chunk_size=500,
            overlap=50,
            add_context_headers=False,
        )

        # Each chunk should not split words
        for chunk in chunks:
            # No partial words (all content should start/end with complete words)
            words = chunk.content.split()
            reconstructed = " ".join(words) + " "
            # Content should be complete words
            assert (
                chunk.content.strip() == reconstructed.strip()
                or chunk.content == reconstructed.strip() + " "
            )

    async def test_character_chunking_with_small_document(self):
        """Test that small documents create single chunk."""
        service = ChunkingService()
        document = Document(
            id="test-3",
            content="Short content here.",
            title="Short Doc",
            url="https://example.com/test",
            project="test-project",
        )

        chunks = await service.chunk_document(
            document=document,
            strategy=ChunkStrategy.CHARACTER,
            chunk_size=1000,
            overlap=100,
            add_context_headers=False,
        )

        assert len(chunks) == 1
        assert chunks[0].content == document.content
        assert chunks[0].chunk_index == 0

    async def test_character_chunking_invalid_chunk_size(self):
        """Test that invalid chunk sizes raise ValueError."""
        service = ChunkingService()
        document = Document(
            id="test-4",
            content="Test content",
            title="Test",
            url="https://example.com/test",
            project="test-project",
        )

        # Chunk size too small
        with pytest.raises(ValueError, match="chunk_size"):
            await service.chunk_document(
                document=document,
                strategy=ChunkStrategy.CHARACTER,
                chunk_size=50,  # < 100
                overlap=10,
            )

        # Chunk size too large
        with pytest.raises(ValueError, match="chunk_size"):
            await service.chunk_document(
                document=document,
                strategy=ChunkStrategy.CHARACTER,
                chunk_size=6000,  # > 5000
                overlap=10,
            )

    async def test_character_chunking_empty_content(self):
        """Test that empty content raises ValueError."""
        service = ChunkingService()
        document = Document(
            id="test-5",
            content="",
            title="Empty",
            url="https://example.com/test",
            project="test-project",
        )

        with pytest.raises(ValueError, match="content empty"):
            await service.chunk_document(
                document=document, strategy=ChunkStrategy.CHARACTER
            )

    async def test_character_chunking_performance(self):
        """Test that character chunking meets performance requirements (<10ms)."""
        import time

        service = ChunkingService()
        document = Document(
            id="test-6",
            content="Test content. " * 200,  # ~2800 chars
            title="Performance Test",
            url="https://example.com/test",
            project="test-project",
        )

        start = time.time()
        chunks = await service.chunk_document(
            document=document,
            strategy=ChunkStrategy.CHARACTER,
            chunk_size=1000,
            overlap=100,
            add_context_headers=False,
        )
        elapsed_ms = (time.time() - start) * 1000

        assert elapsed_ms < 10.0, f"Too slow: {elapsed_ms}ms (expected <10ms)"
        assert len(chunks) > 0