"""Contract tests for VectorStoreOperation interface."""

import pytest
from typing import List, Dict, Any, Protocol
from pathlib import Path

from src.services.sqlite_vec_service import SQLiteVecService
from src.services.vector_store import VectorStoreService
from src.models.vector_store_types import VectorStoreProvider


class VectorStoreOperation(Protocol):
    """Protocol defining the vector store interface contract."""

    async def initialize(self) -> None:
        """Initialize the vector store."""
        ...

    async def create_collection(self, name: str, vector_size: int = 1024) -> None:
        """Create a new collection/table for vectors."""
        ...

    async def upsert_document(
        self, collection: str, doc_id: str, embedding: List[float], metadata: Dict[str, Any]
    ) -> None:
        """Insert or update a document with its embedding."""
        ...

    async def search(
        self, collection: str, query_embedding: List[float], limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for similar documents."""
        ...

    async def delete_document(self, collection: str, doc_id: str) -> bool:
        """Delete a document from the collection."""
        ...

    async def delete_collection(self, name: str) -> bool:
        """Delete an entire collection."""
        ...

    async def get_collection_stats(self, name: str) -> Dict[str, Any]:
        """Get statistics about a collection."""
        ...


class TestVectorStoreInterface:
    """Test that all vector store implementations follow the same interface."""

    @pytest.fixture
    def sqlite_vec_service(self, tmp_path):
        """Create SQLiteVecService instance."""
        from src.core.config import DocBroConfig

        config = DocBroConfig(
            database_path=str(tmp_path / "test.db"),
            data_dir=str(tmp_path / "data"),
            vector_store_provider=VectorStoreProvider.SQLITE_VEC,
        )
        return SQLiteVecService(config)

    @pytest.fixture
    def qdrant_service(self, tmp_path):
        """Create QdrantService instance."""
        from src.core.config import DocBroConfig

        config = DocBroConfig(
            database_path=str(tmp_path / "test.db"),
            data_dir=str(tmp_path / "data"),
            vector_store_provider=VectorStoreProvider.QDRANT,
        )
        return VectorStoreService(config)

    def test_sqlite_vec_implements_interface(self, sqlite_vec_service):
        """Test that SQLiteVecService implements VectorStoreOperation interface."""
        # Check all required methods exist
        assert hasattr(sqlite_vec_service, "initialize")
        assert hasattr(sqlite_vec_service, "create_collection")
        assert hasattr(sqlite_vec_service, "upsert_document")
        assert hasattr(sqlite_vec_service, "search")
        assert hasattr(sqlite_vec_service, "delete_document")
        assert hasattr(sqlite_vec_service, "delete_collection")
        assert hasattr(sqlite_vec_service, "get_collection_stats")

        # Check methods are callable
        assert callable(sqlite_vec_service.initialize)
        assert callable(sqlite_vec_service.create_collection)
        assert callable(sqlite_vec_service.upsert_document)
        assert callable(sqlite_vec_service.search)
        assert callable(sqlite_vec_service.delete_document)
        assert callable(sqlite_vec_service.delete_collection)
        assert callable(sqlite_vec_service.get_collection_stats)

    def test_qdrant_implements_interface(self, qdrant_service):
        """Test that VectorStoreService (Qdrant) implements VectorStoreOperation interface."""
        # Check all required methods exist
        assert hasattr(qdrant_service, "initialize")
        assert hasattr(qdrant_service, "create_collection")
        assert hasattr(qdrant_service, "upsert_document")
        assert hasattr(qdrant_service, "search")
        assert hasattr(qdrant_service, "delete_document")
        assert hasattr(qdrant_service, "delete_collection")
        assert hasattr(qdrant_service, "get_collection_stats")

    @pytest.mark.asyncio
    async def test_initialize_contract(self, sqlite_vec_service):
        """Test initialize method contract."""
        # Should not raise exception
        await sqlite_vec_service.initialize()

        # Should be idempotent (can call multiple times)
        await sqlite_vec_service.initialize()

    @pytest.mark.asyncio
    async def test_create_collection_contract(self, sqlite_vec_service):
        """Test create_collection method contract."""
        await sqlite_vec_service.initialize()

        # Should accept name and optional vector_size
        await sqlite_vec_service.create_collection("test_collection")
        await sqlite_vec_service.create_collection("test_collection_768", vector_size=768)

        # Should handle duplicate creation gracefully
        await sqlite_vec_service.create_collection("test_collection")

    @pytest.mark.asyncio
    async def test_upsert_document_contract(self, sqlite_vec_service):
        """Test upsert_document method contract."""
        await sqlite_vec_service.initialize()
        await sqlite_vec_service.create_collection("test_collection")

        # Should accept all required parameters
        embedding = [0.1] * 1024
        metadata = {"title": "Test Doc", "url": "http://example.com"}

        await sqlite_vec_service.upsert_document(
            collection="test_collection",
            doc_id="doc1",
            embedding=embedding,
            metadata=metadata,
        )

        # Should handle updates (upsert)
        metadata["updated"] = True
        await sqlite_vec_service.upsert_document(
            collection="test_collection",
            doc_id="doc1",
            embedding=embedding,
            metadata=metadata,
        )

    @pytest.mark.asyncio
    async def test_search_contract(self, sqlite_vec_service):
        """Test search method contract."""
        await sqlite_vec_service.initialize()
        await sqlite_vec_service.create_collection("test_collection")

        # Insert test document
        embedding = [0.1] * 1024
        await sqlite_vec_service.upsert_document(
            collection="test_collection",
            doc_id="doc1",
            embedding=embedding,
            metadata={"title": "Test"},
        )

        # Should return list of results
        query_embedding = [0.1] * 1024
        results = await sqlite_vec_service.search(
            collection="test_collection", query_embedding=query_embedding, limit=5
        )

        assert isinstance(results, list)
        if results:  # If results exist
            assert "doc_id" in results[0]
            assert "score" in results[0]
            assert "metadata" in results[0]

    @pytest.mark.asyncio
    async def test_delete_document_contract(self, sqlite_vec_service):
        """Test delete_document method contract."""
        await sqlite_vec_service.initialize()
        await sqlite_vec_service.create_collection("test_collection")

        # Insert then delete
        embedding = [0.1] * 1024
        await sqlite_vec_service.upsert_document(
            collection="test_collection",
            doc_id="doc1",
            embedding=embedding,
            metadata={},
        )

        # Should return boolean indicating success
        result = await sqlite_vec_service.delete_document(
            collection="test_collection", doc_id="doc1"
        )
        assert isinstance(result, bool)

        # Should handle non-existent document
        result = await sqlite_vec_service.delete_document(
            collection="test_collection", doc_id="nonexistent"
        )
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_delete_collection_contract(self, sqlite_vec_service):
        """Test delete_collection method contract."""
        await sqlite_vec_service.initialize()
        await sqlite_vec_service.create_collection("test_collection")

        # Should return boolean indicating success
        result = await sqlite_vec_service.delete_collection("test_collection")
        assert isinstance(result, bool)

        # Should handle non-existent collection
        result = await sqlite_vec_service.delete_collection("nonexistent")
        assert isinstance(result, bool)

    @pytest.mark.asyncio
    async def test_get_collection_stats_contract(self, sqlite_vec_service):
        """Test get_collection_stats method contract."""
        await sqlite_vec_service.initialize()
        await sqlite_vec_service.create_collection("test_collection")

        # Should return dictionary with stats
        stats = await sqlite_vec_service.get_collection_stats("test_collection")

        assert isinstance(stats, dict)
        assert "name" in stats
        assert "vector_count" in stats
        assert "vector_dimensions" in stats