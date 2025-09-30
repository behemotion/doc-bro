"""Strategy configuration models for RAG operations."""

from enum import Enum

from pydantic import BaseModel, Field


class SearchStrategy(str, Enum):
    """Search strategy options."""

    SEMANTIC = "semantic"
    HYBRID = "hybrid"
    ADVANCED = "advanced"
    FUSION = "fusion"


class ChunkStrategy(str, Enum):
    """Chunking strategy options."""

    CHARACTER = "character"
    SEMANTIC = "semantic"


class RerankWeights(BaseModel):
    """Configurable weights for reranking signals."""

    vector_score: float = Field(default=0.5, ge=0.0, le=1.0)
    term_overlap: float = Field(default=0.3, ge=0.0, le=1.0)
    title_match: float = Field(default=0.1, ge=0.0, le=1.0)
    freshness: float = Field(default=0.1, ge=0.0, le=1.0)

    def validate_sum(self) -> bool:
        """Validate that weights sum to approximately 1.0."""
        total = (
            self.vector_score + self.term_overlap + self.title_match + self.freshness
        )
        return abs(total - 1.0) < 0.01  # Allow floating point tolerance


class SemanticChunkingConfig(BaseModel):
    """Configuration for semantic chunking strategy."""

    similarity_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
        description="Minimum similarity for grouping sentences",
    )
    max_chunk_size: int = Field(
        default=1500,
        ge=500,
        le=3000,
        description="Maximum chunk size in characters",
    )
    timeout: float = Field(
        default=5.0, gt=0.0, description="Timeout in seconds before fallback"
    )


class QueryTransformConfig(BaseModel):
    """Configuration for query transformation."""

    max_variations: int = Field(
        default=5, ge=1, le=10, description="Maximum query variations to generate"
    )
    synonym_dict_path: str | None = Field(
        default=None, description="Path to custom synonym dictionary"
    )
    enable_simplification: bool = Field(
        default=True, description="Enable stop word removal"
    )
    enable_reformulation: bool = Field(
        default=True, description="Enable question reformulation"
    )


class FusionConfig(BaseModel):
    """Configuration for fusion retrieval."""

    rrf_k: int = Field(default=60, ge=1, description="RRF constant for rank fusion")
    strategies: list[SearchStrategy] = Field(
        default_factory=lambda: [SearchStrategy.SEMANTIC, SearchStrategy.HYBRID],
        description="Strategies to fuse",
    )