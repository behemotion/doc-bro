"""Quick verification tests for Phase 1 implementations."""

import pytest

from src.logic.rag.core.chunking_service import ChunkingService
from src.logic.rag.core.reranking_service import RerankingService
from src.logic.rag.models.chunk import Chunk
from src.logic.rag.models.document import Document
from src.logic.rag.models.search_result import SearchResult
from src.logic.rag.models.strategy_config import ChunkStrategy, RerankWeights


class TestLRUCache:
    """Test LRU cache enhancement in EmbeddingService."""

    def test_embedding_service_has_lru_fields(self):
        """Verify EmbeddingService has LRU cache fields."""
        from src.services.embeddings import EmbeddingService

        service = EmbeddingService()

        # Check LRU-specific fields exist
        assert hasattr(service, "_cache_max_size")
        assert hasattr(service, "_cache_evictions")
        assert service._cache_max_size == 10000


class TestChunkingService:
    """Test ChunkingService implementation."""

    @pytest.mark.asyncio
    async def test_character_chunking_basic(self):
        """Test basic character chunking."""
        service = ChunkingService()
        document = Document(
            id="test-1",
            content="This is a test document. " * 50,  # ~1250 chars
            title="Test Document",
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

        assert len(chunks) > 1
        assert all(isinstance(c, Chunk) for c in chunks)
        assert chunks[0].chunk_index == 0
        assert chunks[0].parent_id == "test-1"
        assert chunks[0].chunk_strategy == "character"

    @pytest.mark.asyncio
    async def test_contextual_headers_added(self):
        """Test that contextual headers are added."""
        service = ChunkingService()
        document = Document(
            id="test-2",
            content="Test content for header verification.",
            title="Test Document",
            url="https://example.com/test",
            project="test-project",
        )

        chunks = await service.chunk_document(
            document=document,
            strategy=ChunkStrategy.CHARACTER,
            chunk_size=1000,
            overlap=100,
            add_context_headers=True,
        )

        assert len(chunks) == 1
        assert chunks[0].context_header is not None
        assert "Test Document" in chunks[0].context_header
        assert "test-project" in chunks[0].context_header
        assert chunks[0].content.startswith("[")

    @pytest.mark.asyncio
    async def test_hierarchy_extraction(self):
        """Test HTML hierarchy extraction."""
        service = ChunkingService()
        html = """
        <h1>Main Title</h1>
        <p>Content</p>
        <h2>Subsection</h2>
        <p>More content</p>
        """

        hierarchy = await service.extract_hierarchy(html)

        assert len(hierarchy) == 2
        assert hierarchy[0] == (1, "Main Title")
        assert hierarchy[1] == (2, "Subsection")


class TestFastReranker:
    """Test FastReranker implementation."""

    @pytest.mark.asyncio
    async def test_rerank_basic(self):
        """Test basic reranking functionality."""
        service = RerankingService()
        query = "docker installation"

        results = [
            SearchResult(
                id="1",
                title="Docker Guide",
                content="Installing docker is simple and straightforward",
                score=0.6,
                url="https://example.com/1",
                project="docs",
                match_type="semantic",
            ),
            SearchResult(
                id="2",
                title="Unrelated Article",
                content="This talks about docker installation in detail",
                score=0.8,
                url="https://example.com/2",
                project="docs",
                match_type="semantic",
            ),
        ]

        reranked = await service.rerank(query, results)

        # Verify reranking was applied
        assert len(reranked) == 2
        assert all(r.rerank_score is not None for r in reranked)
        assert all(r.rerank_signals is not None for r in reranked)

    @pytest.mark.asyncio
    async def test_rerank_signals_calculation(self):
        """Test individual signal calculation."""
        service = RerankingService()
        query = "test query"

        result = SearchResult(
            id="1",
            title="Test",
            content="Query content here with test",
            score=0.7,
            url="https://example.com",
            project="test",
            match_type="semantic",
        )

        signals = service.calculate_signals(query, result)

        # Verify all signals are calculated
        assert 0.0 <= signals.vector_score <= 1.0
        assert 0.0 <= signals.term_overlap <= 1.0
        assert 0.0 <= signals.title_match <= 1.0
        assert 0.0 <= signals.freshness <= 1.0

    @pytest.mark.asyncio
    async def test_custom_weights(self):
        """Test custom reranking weights."""
        service = RerankingService()
        query = "test"

        results = [
            SearchResult(
                id="1",
                title="Perfect Title Match Test",
                content="Content",
                score=0.5,
                url="https://example.com",
                project="test",
                match_type="semantic",
            )
        ]

        custom_weights = RerankWeights(
            vector_score=0.2, term_overlap=0.2, title_match=0.5, freshness=0.1
        )

        reranked = await service.rerank(query, results, weights=custom_weights)

        assert reranked[0].rerank_score is not None
        # Title match should have significant impact due to heavy weight

    @pytest.mark.asyncio
    async def test_rerank_weights_validation(self):
        """Test that invalid weights are rejected."""
        service = RerankingService()

        results = [
            SearchResult(
                id="1",
                title="Test",
                content="Content",
                score=0.5,
                url="https://example.com",
                project="test",
                match_type="semantic",
            )
        ]

        # Weights don't sum to 1.0
        invalid_weights = RerankWeights(
            vector_score=0.5, term_overlap=0.5, title_match=0.5, freshness=0.5
        )

        with pytest.raises(ValueError, match="must sum to 1.0"):
            await service.rerank("query", results, weights=invalid_weights)


class TestStrategyEnums:
    """Test strategy enum definitions."""

    def test_search_strategy_enum(self):
        """Test SearchStrategy enum."""
        from src.logic.rag.models.strategy_config import SearchStrategy

        assert SearchStrategy.SEMANTIC.value == "semantic"
        assert SearchStrategy.HYBRID.value == "hybrid"
        assert SearchStrategy.ADVANCED.value == "advanced"
        assert SearchStrategy.FUSION.value == "fusion"

    def test_chunk_strategy_enum(self):
        """Test ChunkStrategy enum."""
        from src.logic.rag.models.strategy_config import ChunkStrategy

        assert ChunkStrategy.CHARACTER.value == "character"
        assert ChunkStrategy.SEMANTIC.value == "semantic"


class TestModels:
    """Test Pydantic model definitions."""

    def test_chunk_model(self):
        """Test Chunk model validation."""
        chunk = Chunk(
            id="chunk-1",
            content="Test content here.",
            chunk_index=0,
            parent_id="doc-1",
        )

        assert chunk.id == "chunk-1"
        assert chunk.chunk_index == 0
        assert chunk.chunk_strategy == "character"

    def test_search_result_model(self):
        """Test SearchResult model."""
        result = SearchResult(
            id="result-1",
            url="https://example.com",
            title="Test",
            content="Content",
            score=0.85,
            project="test",
            match_type="semantic",
        )

        assert result.id == "result-1"
        assert result.score == 0.85
        assert result.rerank_score is None  # Not reranked yet

    def test_rerank_weights_validation_method(self):
        """Test RerankWeights validation."""
        valid_weights = RerankWeights(
            vector_score=0.5, term_overlap=0.3, title_match=0.1, freshness=0.1
        )
        assert valid_weights.validate_sum() is True

        invalid_weights = RerankWeights(
            vector_score=0.5, term_overlap=0.5, title_match=0.5, freshness=0.5
        )
        assert invalid_weights.validate_sum() is False