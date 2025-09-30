"""Chunk model for RAG operations."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class Chunk(BaseModel):
    """Represents a document chunk with metadata."""

    id: str = Field(description="Unique chunk identifier")
    content: str = Field(
        min_length=10, max_length=5000, description="Chunk text content"
    )
    title: str = Field(default="", description="Document title")
    url: str = Field(default="", description="Source URL")
    project: str = Field(default="", description="Project name")
    chunk_index: int = Field(ge=0, description="Position in document")
    parent_id: str = Field(description="Parent document ID")

    # Metadata
    context_header: str | None = Field(
        default=None, description="Contextual header prepended to content"
    )
    hierarchy: list[tuple[int, str]] = Field(
        default_factory=list, description="Document section hierarchy"
    )
    chunk_strategy: str = Field(
        default="character", description="Chunking strategy used"
    )
    created_at: datetime = Field(default_factory=datetime.now)

    class Config:
        """Pydantic v2 configuration."""

        json_schema_extra = {
            "example": {
                "id": "chunk-123",
                "content": "Docker is a containerization platform...",
                "title": "Docker Guide",
                "url": "https://docs.docker.com/get-started/",
                "project": "docker-docs",
                "chunk_index": 0,
                "parent_id": "doc-456",
                "context_header": "[Document: Docker Guide | Section: Getting Started | Project: docker-docs]",
                "hierarchy": [(1, "Getting Started"), (2, "Introduction")],
                "chunk_strategy": "character",
            }
        }