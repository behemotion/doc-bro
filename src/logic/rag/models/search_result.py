"""Search result models for RAG operations."""

from typing import Any

from pydantic import BaseModel, Field


class RerankSignals(BaseModel):
    """Individual reranking signals."""

    vector_score: float = Field(ge=0.0, le=1.0, description="Original similarity score")
    term_overlap: float = Field(
        ge=0.0, le=1.0, description="Fraction of query terms in content"
    )
    title_match: float = Field(
        ge=0.0, le=1.0, description="Fraction of query terms in title"
    )
    freshness: float = Field(
        ge=0.0, le=1.0, description="Temporal relevance (newer=1.0)"
    )


class SearchResult(BaseModel):
    """Represents a search result with optional reranking."""

    id: str = Field(description="Result document/chunk ID")
    url: str = Field(description="Source URL")
    title: str = Field(description="Document title")
    content: str = Field(description="Result content")
    score: float = Field(ge=0.0, le=1.0, description="Original similarity score")
    project: str = Field(description="Project name")
    match_type: str = Field(
        description="Match type: semantic, keyword, hybrid_both, fusion"
    )

    # Reranking
    rerank_score: float | None = Field(
        default=None,
        ge=0.0,
        le=1.0,
        description="Reranked score if reranking applied",
    )
    rerank_signals: dict[str, float] | None = Field(
        default=None, description="Individual reranking signal scores"
    )

    # Context
    context_header: str | None = Field(
        default=None, description="Contextual header from chunk"
    )
    query_terms: list[str] = Field(
        default_factory=list, description="Query terms that matched"
    )

    class Config:
        """Pydantic v2 configuration."""

        json_schema_extra = {
            "example": {
                "id": "chunk-123",
                "url": "https://docs.docker.com/get-started/",
                "title": "Docker Guide",
                "content": "Docker is a containerization platform...",
                "score": 0.85,
                "project": "docker-docs",
                "match_type": "semantic",
                "rerank_score": 0.92,
                "rerank_signals": {
                    "vector_score": 0.85,
                    "term_overlap": 0.8,
                    "title_match": 1.0,
                    "freshness": 0.95,
                },
                "context_header": "[Document: Docker Guide | Section: Getting Started]",
                "query_terms": ["docker", "installation"],
            }
        }