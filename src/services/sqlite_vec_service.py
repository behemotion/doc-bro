"""SQLite-vec vector store service implementation."""

import json
import logging
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import aiosqlite

from src.core.config import DocBroConfig
from src.models.sqlite_vec_config import SQLiteVecConfiguration

# Try to import sqlite_vec
try:
    import sqlite_vec

    SQLITE_VEC_AVAILABLE = True
except ImportError:
    sqlite_vec = None
    SQLITE_VEC_AVAILABLE = False


logger = logging.getLogger(__name__)


def detect_sqlite_vec() -> Tuple[bool, str]:
    """Detect if sqlite-vec extension is available."""
    if not SQLITE_VEC_AVAILABLE:
        return False, "sqlite-vec not installed. Run: uv pip install --system sqlite-vec"

    try:
        # Test loading the extension
        conn = sqlite3.connect(":memory:")

        # Check if enable_load_extension is available
        if not hasattr(conn, 'enable_load_extension'):
            conn.close()
            return False, (
                "SQLite was compiled without extension support. "
                "For full SQLite-vec functionality, consider using Qdrant instead. "
                "Run 'docbro init --vector-store qdrant' to use Qdrant."
            )

        try:
            conn.enable_load_extension(True)
        except AttributeError:
            conn.close()
            return False, "SQLite enable_load_extension not available"
        except Exception as e:
            conn.close()
            return False, f"Failed to enable extensions: {e}"

        try:
            sqlite_vec.load(conn)
        except Exception as e:
            conn.close()
            return False, f"Failed to load sqlite-vec extension: {e}"

        conn.enable_load_extension(False)

        # Get version
        try:
            cursor = conn.execute("SELECT vec_version()")
            version = cursor.fetchone()[0]
        except Exception as e:
            conn.close()
            return False, f"Failed to get sqlite-vec version: {e}"

        conn.close()
        return True, f"sqlite-vec {version} available"
    except Exception as e:
        return False, f"Failed to load sqlite-vec: {e}"


class SQLiteVecService:
    """SQLite-vec vector store service."""

    def __init__(self, config: DocBroConfig):
        """Initialize SQLite-vec service."""
        self.config = config
        self.data_dir = Path(config.data_dir)
        self.connections: Dict[str, aiosqlite.Connection] = {}
        self.initialized = False

        # Create SQLite-vec configuration
        self.vec_config = SQLiteVecConfiguration(
            enabled=True,
            database_path=self.data_dir / "default" / "vectors.db",
            data_directory=self.data_dir,
        )

    def detect_extension(self) -> Tuple[bool, str]:
        """Detect if sqlite-vec extension is available."""
        return detect_sqlite_vec()

    def check_sqlite_version(self) -> Tuple[bool, str]:
        """Check SQLite version compatibility."""
        version = sqlite3.sqlite_version_info

        if version >= (3, 41, 0):
            return True, f"SQLite {sqlite3.sqlite_version} is fully compatible"
        elif version >= (3, 37, 0):
            return True, f"SQLite {sqlite3.sqlite_version} is compatible with limited features"
        else:
            return False, f"SQLite {sqlite3.sqlite_version} is too old. Requires 3.37+"

    def is_extension_available(self) -> bool:
        """Check if extension is available."""
        available, _ = self.detect_extension()
        return available

    def get_installation_suggestion(self) -> str:
        """Get installation suggestion for missing extension."""
        available, message = self.detect_extension()

        if not available and "compiled without extension support" in message:
            return (
                "SQLite extension support issue detected:\n"
                "  • Your Python's SQLite3 was compiled without extension support\n"
                "  • This is common on macOS with certain Python installations\n\n"
                "Solutions:\n"
                "  1. Use Qdrant instead: docbro init --vector-store qdrant --force\n"
                "  2. Or install Python with Homebrew: brew install python@3.13\n"
                "  3. Or use UV's managed Python: uv python install 3.12 (requires updating project)\n\n"
                "Qdrant provides better performance for large document collections."
            )
        else:
            return (
                "To install sqlite-vec:\n"
                "  1. Run: uv pip install --system sqlite-vec\n"
                "  2. Run: docbro services setup --service sqlite-vec\n"
            )

    async def initialize(self) -> None:
        """Initialize the SQLite-vec service."""
        if self.initialized:
            return

        # Check extension availability
        available, message = self.detect_extension()
        if not available:
            raise RuntimeError(f"SQLite-vec extension not available: {message}")

        # Check SQLite version
        version_ok, version_msg = self.check_sqlite_version()
        if not version_ok:
            raise RuntimeError(f"SQLite version issue: {version_msg}")

        logger.info(f"SQLite-vec initialized: {message}, {version_msg}")
        self.initialized = True

    async def _get_connection(self, collection: str) -> aiosqlite.Connection:
        """Get or create connection for a collection."""
        if collection not in self.connections:
            # Create project directory
            project_dir = self.data_dir / "projects" / self._sanitize_name(collection)
            project_dir.mkdir(parents=True, exist_ok=True)

            # Create database path
            db_path = project_dir / "vectors.db"

            # Open connection
            conn = await aiosqlite.connect(str(db_path))
            await conn.execute("PRAGMA journal_mode = WAL")
            await conn.execute("PRAGMA foreign_keys = ON")

            # Load sqlite-vec extension
            try:
                await conn.enable_load_extension(True)
            except AttributeError:
                await conn.close()
                raise RuntimeError("SQLite was compiled without extension support")
            except Exception as e:
                await conn.close()
                raise RuntimeError(f"Failed to enable extensions: {e}")

            try:
                await conn.load_extension(sqlite_vec.__file__)
            except Exception as e:
                await conn.close()
                raise RuntimeError(f"Failed to load sqlite-vec extension: {e}")

            await conn.enable_load_extension(False)

            self.connections[collection] = conn

        return self.connections[collection]

    def _sanitize_name(self, name: str) -> str:
        """Sanitize project name for file system."""
        # Convert to lowercase and replace problematic characters
        safe_name = name.lower()
        for char in ["-", ".", "/", "\\", " "]:
            safe_name = safe_name.replace(char, "_")
        return safe_name

    async def create_collection(self, name: str, vector_size: int = 1024) -> None:
        """Create a new collection for vectors."""
        conn = await self._get_connection(name)

        # Create virtual table for vectors
        await conn.execute(
            f"""
            CREATE VIRTUAL TABLE IF NOT EXISTS vectors USING vec0(
                content_embedding FLOAT[{vector_size}],
                +doc_id TEXT,
                +chunk_index INTEGER,
                +page_url TEXT,
                +metadata JSON,
                +created_at TEXT
            )
            """
        )

        # Create indexes
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_vectors_doc_id ON vectors(doc_id)"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_vectors_page_url ON vectors(page_url)"
        )

        await conn.commit()
        logger.info(f"Created collection: {name} with {vector_size} dimensions")

    async def upsert_document(
        self,
        collection: str,
        doc_id: str,
        embedding: List[float],
        metadata: Dict[str, Any],
    ) -> None:
        """Insert or update a document with its embedding."""
        conn = await self._get_connection(collection)

        # Convert embedding to JSON string
        embedding_str = json.dumps(embedding)

        # Convert metadata to JSON
        metadata_str = json.dumps(metadata)

        # Delete existing document if present
        await conn.execute("DELETE FROM vectors WHERE doc_id = ?", (doc_id,))

        # Insert new document
        await conn.execute(
            """
            INSERT INTO vectors (
                content_embedding, doc_id, chunk_index, page_url, metadata, created_at
            ) VALUES (?, ?, ?, ?, ?, datetime('now'))
            """,
            (
                embedding_str,
                doc_id,
                metadata.get("chunk_index", 0),
                metadata.get("page_url", ""),
                metadata_str,
            ),
        )

        await conn.commit()

    async def search(
        self, collection: str, query_embedding: List[float], limit: int = 10
    ) -> List[Dict[str, Any]]:
        """Search for similar documents."""
        conn = await self._get_connection(collection)

        # Convert query embedding to JSON
        query_str = json.dumps(query_embedding)

        # Perform KNN search
        cursor = await conn.execute(
            f"""
            SELECT doc_id, distance, metadata
            FROM vectors
            WHERE content_embedding MATCH ?
            ORDER BY distance
            LIMIT ?
            """,
            (query_str, limit),
        )

        results = []
        async for row in cursor:
            doc_id, distance, metadata_str = row
            # Convert distance to similarity score (1 - normalized_distance)
            score = max(0.0, 1.0 - (distance / 2.0))  # Assuming cosine distance

            results.append(
                {
                    "doc_id": doc_id,
                    "score": score,
                    "metadata": json.loads(metadata_str) if metadata_str else {},
                }
            )

        return results

    async def delete_document(self, collection: str, doc_id: str) -> bool:
        """Delete a document from the collection."""
        conn = await self._get_connection(collection)

        cursor = await conn.execute(
            "DELETE FROM vectors WHERE doc_id = ?", (doc_id,)
        )
        await conn.commit()

        return cursor.rowcount > 0

    async def delete_collection(self, name: str) -> bool:
        """Delete an entire collection."""
        # Close connection if exists
        if name in self.connections:
            await self.connections[name].close()
            del self.connections[name]

        # Delete database file
        project_dir = self.data_dir / "projects" / self._sanitize_name(name)
        db_path = project_dir / "vectors.db"

        if db_path.exists():
            db_path.unlink()
            # Try to remove directory if empty
            try:
                project_dir.rmdir()
            except OSError:
                pass  # Directory not empty

            logger.info(f"Deleted collection: {name}")
            return True

        return False

    async def get_collection_stats(self, name: str) -> Dict[str, Any]:
        """Get statistics about a collection."""
        try:
            conn = await self._get_connection(name)

            # Count vectors
            cursor = await conn.execute("SELECT COUNT(*) FROM vectors")
            count = (await cursor.fetchone())[0]

            # Get database file size
            project_dir = self.data_dir / "projects" / self._sanitize_name(name)
            db_path = project_dir / "vectors.db"
            disk_usage = db_path.stat().st_size if db_path.exists() else 0

            return {
                "name": name,
                "vector_count": count,
                "vector_dimensions": self.vec_config.vector_dimensions,
                "disk_usage_bytes": disk_usage,
            }
        except Exception as e:
            logger.error(f"Failed to get stats for {name}: {e}")
            return {
                "name": name,
                "vector_count": 0,
                "vector_dimensions": self.vec_config.vector_dimensions,
                "disk_usage_bytes": 0,
            }

    async def cleanup(self) -> None:
        """Clean up vector store connections (alias for close)."""
        await self.close()

    async def close(self) -> None:
        """Close all connections."""
        for conn in self.connections.values():
            await conn.close()
        self.connections.clear()
        self.initialized = False

    async def collection_exists(self, collection_name: str) -> bool:
        """Check if collection exists."""
        try:
            project_dir = self.data_dir / "projects" / self._sanitize_name(collection_name)
            db_path = project_dir / "vectors.db"
            return db_path.exists()
        except Exception:
            return False

    async def list_collections(self) -> List[str]:
        """List all collections."""
        collections = []
        try:
            projects_dir = self.data_dir / "projects"
            if projects_dir.exists():
                for project_dir in projects_dir.iterdir():
                    if project_dir.is_dir():
                        db_path = project_dir / "vectors.db"
                        if db_path.exists():
                            collections.append(project_dir.name)
        except Exception as e:
            logger.error(f"Failed to list collections: {e}")
        return collections

    async def upsert_documents(
        self,
        collection_name: str,
        documents: List[Dict[str, Any]],
        batch_size: int = 100
    ) -> int:
        """Upsert multiple documents with batching."""
        upserted_count = 0
        try:
            for doc in documents:
                await self.upsert_document(
                    collection_name,
                    doc["id"],
                    doc["embedding"],
                    doc.get("metadata", {})
                )
                upserted_count += 1
        except Exception as e:
            logger.error(f"Failed to upsert documents: {e}")
            raise
        return upserted_count

    async def get_document(
        self,
        collection_name: str,
        document_id: str
    ) -> Optional[Dict[str, Any]]:
        """Get a specific document by ID."""
        try:
            conn = await self._get_connection(collection_name)
            cursor = await conn.execute(
                "SELECT content_embedding, metadata FROM vectors WHERE doc_id = ?",
                (document_id,)
            )
            row = await cursor.fetchone()
            if row:
                embedding_str, metadata_str = row
                return {
                    "id": document_id,
                    "embedding": json.loads(embedding_str),
                    "metadata": json.loads(metadata_str) if metadata_str else {}
                }
        except Exception as e:
            logger.error(f"Failed to get document {document_id}: {e}")
        return None

    async def delete_documents(
        self,
        collection_name: str,
        document_ids: List[str]
    ) -> int:
        """Delete multiple documents from the collection."""
        deleted_count = 0
        try:
            for doc_id in document_ids:
                if await self.delete_document(collection_name, doc_id):
                    deleted_count += 1
        except Exception as e:
            logger.error(f"Failed to delete documents: {e}")
        return deleted_count

    async def count_documents(self, collection_name: str) -> int:
        """Count documents in collection."""
        try:
            stats = await self.get_collection_stats(collection_name)
            return stats.get("vector_count", 0)
        except Exception as e:
            logger.error(f"Failed to count documents in {collection_name}: {e}")
            return 0

    async def health_check(self) -> tuple[bool, str]:
        """Check vector store health."""
        if not self.initialized:
            return False, "Vector store not initialized"

        try:
            available, message = self.detect_extension()
            if not available:
                return False, f"SQLite-vec extension not available: {message}"

            # Test basic operation
            collections = await self.list_collections()
            return True, f"Healthy - {len(collections)} collections"
        except Exception as e:
            return False, f"Health check failed: {e}"

    async def add_embeddings(
        self,
        collection_name: str,
        embeddings: List[List[float]],
        ids: List[str],
        metadatas: Optional[List[Dict[str, Any]]] = None
    ) -> int:
        """Add embeddings to collection (compatibility method).

        This method provides compatibility with code expecting an add_embeddings interface.
        It internally uses upsert_documents for the actual implementation.
        """
        documents = []
        for i, (embedding, doc_id) in enumerate(zip(embeddings, ids)):
            metadata = metadatas[i] if metadatas and i < len(metadatas) else {}
            documents.append({
                "id": doc_id,
                "embedding": embedding,
                "metadata": metadata
            })

        return await self.upsert_documents(collection_name, documents)