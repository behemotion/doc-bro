"""RAG metrics tracking for performance monitoring.

This module tracks search and indexing performance metrics including latency,
cache hit rates, and strategy distribution.
"""

import time
from collections import defaultdict
from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field

from src.core.lib_logger import get_logger

logger = get_logger(__name__)


class MetricsSummary(BaseModel):
    """Summary of RAG performance metrics."""

    searches_total: int = Field(description="Total number of searches performed")
    avg_latency_ms: float = Field(description="Average search latency")
    p50_latency_ms: float = Field(description="Median latency (50th percentile)")
    p95_latency_ms: float = Field(description="95th percentile latency")
    p99_latency_ms: float = Field(description="99th percentile latency")
    cache_hit_rate: float = Field(ge=0.0, le=1.0, description="Embedding cache hit rate")
    strategy_distribution: dict[str, int] = Field(
        description="Count of searches by strategy"
    )
    # Quality metrics (optional, populated by RAGQualityMetrics)
    mrr_score: float | None = Field(default=None, description="Mean Reciprocal Rank")
    precision_at_5: float | None = Field(default=None, description="Precision at k=5")
    recall_at_10: float | None = Field(default=None, description="Recall at k=10")
    ndcg_at_10: float | None = Field(default=None, description="NDCG at k=10")


class RAGMetrics:
    """Performance metrics tracker for RAG operations.

    Tracks search latency, cache performance, and strategy usage.
    """

    def __init__(self):
        """Initialize metrics tracker."""
        self._search_latencies: list[float] = []
        self._indexing_latencies: list[float] = []
        self._strategy_counts: dict[str, int] = defaultdict(int)
        self._query_lengths: list[int] = []
        self._result_counts: list[int] = []
        self._cache_hits = 0
        self._cache_misses = 0
        self._start_time = time.time()

    def record_search(
        self,
        strategy: str,
        latency_ms: float,
        result_count: int,
        query: str,
        cache_hit: bool = False,
    ) -> None:
        """Record a search operation.

        Args:
            strategy: Search strategy used (semantic, hybrid, advanced, fusion)
            latency_ms: Search latency in milliseconds
            result_count: Number of results returned
            query: Search query string
            cache_hit: Whether embedding cache was hit
        """
        self._search_latencies.append(latency_ms)
        self._strategy_counts[strategy] += 1
        self._query_lengths.append(len(query))
        self._result_counts.append(result_count)

        if cache_hit:
            self._cache_hits += 1
        else:
            self._cache_misses += 1

        logger.debug(
            f"Search recorded: strategy={strategy}, latency={latency_ms}ms, "
            f"results={result_count}, query_len={len(query)}"
        )

    def record_indexing(
        self, document_count: int, latency_ms: float, chunk_count: int
    ) -> None:
        """Record an indexing operation.

        Args:
            document_count: Number of documents indexed
            latency_ms: Indexing latency in milliseconds
            chunk_count: Number of chunks created
        """
        self._indexing_latencies.append(latency_ms)
        logger.debug(
            f"Indexing recorded: docs={document_count}, "
            f"chunks={chunk_count}, latency={latency_ms}ms"
        )

    def get_summary(self) -> MetricsSummary:
        """Get metrics summary.

        Returns:
            MetricsSummary with current metrics
        """
        if not self._search_latencies:
            return MetricsSummary(
                searches_total=0,
                avg_latency_ms=0.0,
                p50_latency_ms=0.0,
                p95_latency_ms=0.0,
                p99_latency_ms=0.0,
                cache_hit_rate=0.0,
                strategy_distribution={},
            )

        sorted_latencies = sorted(self._search_latencies)
        total_searches = len(sorted_latencies)

        # Calculate percentiles
        p50_idx = int(total_searches * 0.50)
        p95_idx = int(total_searches * 0.95)
        p99_idx = int(total_searches * 0.99)

        # Calculate cache hit rate
        total_cache_ops = self._cache_hits + self._cache_misses
        cache_hit_rate = (
            self._cache_hits / total_cache_ops if total_cache_ops > 0 else 0.0
        )

        return MetricsSummary(
            searches_total=total_searches,
            avg_latency_ms=sum(self._search_latencies) / total_searches,
            p50_latency_ms=sorted_latencies[p50_idx],
            p95_latency_ms=sorted_latencies[min(p95_idx, total_searches - 1)],
            p99_latency_ms=sorted_latencies[min(p99_idx, total_searches - 1)],
            cache_hit_rate=cache_hit_rate,
            strategy_distribution=dict(self._strategy_counts),
        )

    def reset(self) -> None:
        """Reset all metrics."""
        self._search_latencies.clear()
        self._indexing_latencies.clear()
        self._strategy_counts.clear()
        self._query_lengths.clear()
        self._result_counts.clear()
        self._cache_hits = 0
        self._cache_misses = 0
        self._start_time = time.time()
        logger.info("Metrics reset")

    def get_uptime_seconds(self) -> float:
        """Get uptime since metrics started tracking.

        Returns:
            Uptime in seconds
        """
        return time.time() - self._start_time
