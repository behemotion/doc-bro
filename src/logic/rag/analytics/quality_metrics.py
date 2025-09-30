"""RAG quality metrics tracking for result relevance monitoring.

This module tracks quality metrics like MRR, precision, recall, and NDCG
based on user feedback and relevance judgments.
"""

import math
from collections import defaultdict
from typing import Any

from pydantic import BaseModel, Field

from src.core.lib_logger import get_logger

logger = get_logger(__name__)


class FeedbackEntry(BaseModel):
    """User feedback for a search query."""

    query: str = Field(description="Search query")
    result_ids: list[str] = Field(description="Returned result IDs in order")
    clicked_ids: list[str] = Field(
        default_factory=list, description="IDs clicked by user"
    )
    user_rating: int | None = Field(
        default=None, ge=1, le=5, description="Optional user rating (1-5)"
    )


class RAGQualityMetrics:
    """Quality metrics tracker for RAG search results.

    Tracks user feedback and calculates relevance metrics like MRR,
    precision, recall, and NDCG.
    """

    def __init__(self):
        """Initialize quality metrics tracker."""
        self._feedback_entries: list[FeedbackEntry] = []
        self._query_performance: dict[str, list[float]] = defaultdict(list)

    def record_user_feedback(
        self,
        query: str,
        result_ids: list[str],
        clicked_ids: list[str],
        user_rating: int | None = None,
    ) -> None:
        """Record user feedback for a search query.

        Args:
            query: Search query string
            result_ids: Result IDs returned (in order)
            clicked_ids: Result IDs clicked by user
            user_rating: Optional user rating 1-5
        """
        entry = FeedbackEntry(
            query=query,
            result_ids=result_ids,
            clicked_ids=clicked_ids,
            user_rating=user_rating,
        )
        self._feedback_entries.append(entry)

        # Calculate MRR for this query
        mrr = self._calculate_mrr_single(result_ids, clicked_ids)
        self._query_performance[query].append(mrr)

        logger.debug(
            f"Feedback recorded: query='{query}', "
            f"results={len(result_ids)}, clicks={len(clicked_ids)}, mrr={mrr:.3f}"
        )

    def calculate_mrr(self) -> float:
        """Calculate Mean Reciprocal Rank across all feedback.

        MRR is the average of reciprocal ranks of first relevant result.
        Range: 0.0 to 1.0, higher is better.

        Returns:
            MRR score
        """
        if not self._feedback_entries:
            return 0.0

        reciprocal_ranks = []
        for entry in self._feedback_entries:
            rr = self._calculate_mrr_single(entry.result_ids, entry.clicked_ids)
            reciprocal_ranks.append(rr)

        return sum(reciprocal_ranks) / len(reciprocal_ranks)

    def _calculate_mrr_single(
        self, result_ids: list[str], clicked_ids: list[str]
    ) -> float:
        """Calculate reciprocal rank for a single query.

        Args:
            result_ids: Returned result IDs in order
            clicked_ids: Clicked result IDs

        Returns:
            Reciprocal rank (1/rank of first clicked result, or 0)
        """
        if not clicked_ids:
            return 0.0

        # Find rank of first clicked result (1-indexed)
        for rank, result_id in enumerate(result_ids, start=1):
            if result_id in clicked_ids:
                return 1.0 / rank

        return 0.0

    def calculate_precision_at_k(self, k: int = 5) -> float:
        """Calculate Precision@k across all feedback.

        Precision@k = (relevant results in top-k) / k
        Range: 0.0 to 1.0, higher is better.

        Args:
            k: Number of top results to consider

        Returns:
            Precision@k score
        """
        if not self._feedback_entries:
            return 0.0

        precisions = []
        for entry in self._feedback_entries:
            top_k = entry.result_ids[:k]
            relevant_in_top_k = len(
                [rid for rid in top_k if rid in entry.clicked_ids]
            )
            precision = relevant_in_top_k / k
            precisions.append(precision)

        return sum(precisions) / len(precisions)

    def calculate_recall_at_k(self, k: int = 10) -> float:
        """Calculate Recall@k across all feedback.

        Recall@k = (relevant results in top-k) / (total relevant results)
        Range: 0.0 to 1.0, higher is better.

        Args:
            k: Number of top results to consider

        Returns:
            Recall@k score
        """
        if not self._feedback_entries:
            return 0.0

        recalls = []
        for entry in self._feedback_entries:
            if not entry.clicked_ids:
                continue

            top_k = entry.result_ids[:k]
            relevant_in_top_k = len(
                [rid for rid in top_k if rid in entry.clicked_ids]
            )
            total_relevant = len(entry.clicked_ids)
            recall = relevant_in_top_k / total_relevant if total_relevant > 0 else 0.0
            recalls.append(recall)

        return sum(recalls) / len(recalls) if recalls else 0.0

    def calculate_ndcg_at_k(self, k: int = 10) -> float:
        """Calculate Normalized Discounted Cumulative Gain@k.

        NDCG@k accounts for position of relevant results with logarithmic
        discount. Range: 0.0 to 1.0, higher is better.

        Args:
            k: Number of top results to consider

        Returns:
            NDCG@k score
        """
        if not self._feedback_entries:
            return 0.0

        ndcg_scores = []
        for entry in self._feedback_entries:
            if not entry.clicked_ids:
                continue

            # Calculate DCG
            dcg = 0.0
            for i, result_id in enumerate(entry.result_ids[:k]):
                if result_id in entry.clicked_ids:
                    # Binary relevance: 1 if clicked, 0 otherwise
                    relevance = 1
                    # Discount by log2(position + 1)
                    dcg += relevance / math.log2(i + 2)  # i+2 because i is 0-indexed

            # Calculate ideal DCG (all relevant results at top)
            num_relevant = min(len(entry.clicked_ids), k)
            idcg = sum(1.0 / math.log2(i + 2) for i in range(num_relevant))

            # NDCG = DCG / IDCG
            ndcg = dcg / idcg if idcg > 0 else 0.0
            ndcg_scores.append(ndcg)

        return sum(ndcg_scores) / len(ndcg_scores) if ndcg_scores else 0.0

    def get_feedback_count(self) -> int:
        """Get total number of feedback entries.

        Returns:
            Number of feedback entries
        """
        return len(self._feedback_entries)

    def get_click_through_rate(self) -> float:
        """Calculate overall click-through rate.

        CTR = (queries with clicks) / (total queries)

        Returns:
            Click-through rate (0.0 to 1.0)
        """
        if not self._feedback_entries:
            return 0.0

        queries_with_clicks = sum(
            1 for entry in self._feedback_entries if entry.clicked_ids
        )
        return queries_with_clicks / len(self._feedback_entries)

    def reset(self) -> None:
        """Reset all quality metrics."""
        self._feedback_entries.clear()
        self._query_performance.clear()
        logger.info("Quality metrics reset")
