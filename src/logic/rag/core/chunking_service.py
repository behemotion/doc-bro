"""Chunking service for RAG operations."""

import asyncio
import re
import uuid
from datetime import datetime

from bs4 import BeautifulSoup

from src.lib.lib_logger import get_logger
from src.logic.rag.models.chunk import Chunk
from src.logic.rag.models.document import Document
from src.logic.rag.models.strategy_config import ChunkStrategy
from src.logic.rag.utils.contextual_headers import add_contextual_header
from src.services.embeddings import EmbeddingService

logger = get_logger(__name__)


class ChunkingService:
    """Service for chunking documents with multiple strategies."""

    def __init__(self, embedding_service: EmbeddingService | None = None):
        """Initialize chunking service.

        Args:
            embedding_service: Optional embedding service for semantic chunking
        """
        self.embedding_service = embedding_service
        self._semantic_chunker = None

    async def chunk_document(
        self,
        document: Document,
        strategy: ChunkStrategy,
        chunk_size: int = 1000,
        overlap: int = 100,
        add_context_headers: bool = True,
    ) -> list[Chunk]:
        """Chunk a document using specified strategy.

        Args:
            document: Document to chunk
            strategy: Chunking strategy (CHARACTER or SEMANTIC)
            chunk_size: Maximum chunk size in characters
            overlap: Overlap between chunks for CHARACTER strategy
            add_context_headers: Whether to add contextual headers

        Returns:
            List of chunks

        Raises:
            ValueError: If document content is empty or chunk_size invalid
        """
        # Validate inputs
        if not document.content or not document.content.strip():
            raise ValueError("Document content empty")

        if chunk_size < 100 or chunk_size > 5000:
            raise ValueError(
                f"chunk_size must be between 100 and 5000, got {chunk_size}"
            )

        # Extract hierarchy if we need context headers
        hierarchy = []
        if add_context_headers and "<" in document.content:
            hierarchy = await self.extract_hierarchy(document.content)

        # Apply chunking strategy
        if strategy == ChunkStrategy.CHARACTER:
            chunks = await self._chunk_character(
                document, chunk_size, overlap
            )
        elif strategy == ChunkStrategy.SEMANTIC:
            # Try semantic chunking with fallback
            chunks = await self._chunk_semantic_with_fallback(
                document, chunk_size, overlap
            )
        else:
            raise ValueError(f"Unknown chunking strategy: {strategy}")

        # Add contextual headers if requested
        if add_context_headers:
            chunks = [
                add_contextual_header(chunk, document, hierarchy) for chunk in chunks
            ]

        return chunks

    async def _chunk_character(
        self, document: Document, chunk_size: int, overlap: int
    ) -> list[Chunk]:
        """Character-based chunking with word boundary respect.

        Args:
            document: Document to chunk
            chunk_size: Maximum chunk size
            overlap: Overlap between chunks

        Returns:
            List of chunks
        """
        chunks = []
        content = document.content
        chunk_index = 0
        position = 0

        while position < len(content):
            # Extract chunk
            end_position = position + chunk_size

            # If not at the end, try to break at word boundary
            if end_position < len(content):
                # Look for last space within chunk
                chunk_text = content[position:end_position]
                last_space = chunk_text.rfind(" ")

                if last_space > 0:
                    # Break at word boundary
                    end_position = position + last_space
                    chunk_text = content[position:end_position].strip()
                else:
                    # No space found, use full chunk
                    chunk_text = chunk_text.strip()
            else:
                # Last chunk
                chunk_text = content[position:].strip()

            # Create chunk
            if chunk_text:
                chunk = Chunk(
                    id=f"{document.id}-chunk-{chunk_index}",
                    content=chunk_text,
                    title=document.title,
                    url=document.url,
                    project=document.project,
                    chunk_index=chunk_index,
                    parent_id=document.id,
                    chunk_strategy="character",
                    created_at=datetime.now(),
                )
                chunks.append(chunk)
                chunk_index += 1

            # Move position forward (with overlap)
            position = end_position - overlap if end_position < len(content) else len(content)

        return chunks

    async def extract_hierarchy(self, html_content: str) -> list[tuple[int, str]]:
        """Extract heading hierarchy from HTML content.

        Args:
            html_content: HTML string with heading tags

        Returns:
            List of (level, heading_text) tuples
        """
        try:
            soup = BeautifulSoup(html_content, "html.parser")
            hierarchy = []

            # Find all h1-h6 tags
            for heading in soup.find_all(re.compile("^h[1-6]$")):
                level = int(heading.name[1])  # Extract number from 'h1', 'h2', etc.
                text = heading.get_text(strip=True)
                if text:
                    hierarchy.append((level, text))

            return hierarchy

        except Exception:
            # If HTML parsing fails, return empty hierarchy
            return []

    async def _chunk_semantic_with_fallback(
        self, document: Document, chunk_size: int, overlap: int
    ) -> list[Chunk]:
        """Semantic chunking with fallback to character chunking.

        Args:
            document: Document to chunk
            chunk_size: Maximum chunk size
            overlap: Overlap for fallback

        Returns:
            List of chunks (semantic or character-based on fallback)
        """
        # Check if we have embedding service
        if not self.embedding_service:
            logger.warning(
                "No embedding service available - falling back to character chunking"
            )
            return await self._chunk_character(document, chunk_size, overlap)

        # Initialize semantic chunker if needed
        if not self._semantic_chunker:
            from src.logic.rag.strategies.semantic_chunker import SemanticChunker
            from src.logic.rag.models.strategy_config import SemanticChunkingConfig

            self._semantic_chunker = SemanticChunker(
                self.embedding_service, SemanticChunkingConfig()
            )

        try:
            # Try semantic chunking
            chunks = await self._semantic_chunker.chunk_document(document, chunk_size, overlap)
            logger.info(
                f"Semantic chunking succeeded for document {document.id}: {len(chunks)} chunks"
            )
            return chunks

        except asyncio.TimeoutError:
            # Timeout - fall back to character chunking
            logger.warning(
                f"Semantic chunking timeout for document {document.id} - falling back to character chunking"
            )
            return await self._chunk_character(document, chunk_size, overlap)

        except Exception as e:
            # Other errors - fall back to character chunking
            logger.error(
                f"Semantic chunking error for document {document.id}: {e} - falling back to character chunking"
            )
            return await self._chunk_character(document, chunk_size, overlap)