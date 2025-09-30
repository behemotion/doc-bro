"""Fast multi-signal reranking service."""

from datetime import datetime

from src.logic.rag.models.search_result import RerankSignals, SearchResult
from src.logic.rag.models.strategy_config import RerankWeights


class RerankingService:
    """Fast reranking using multiple signals (no embeddings)."""

    async def rerank(
        self,
        query: str,
        results: list[SearchResult],
        weights: RerankWeights | None = None,
    ) -> list[SearchResult]:
        """Rerank search results using multiple signals.

        Args:
            query: Original search query
            results: List of search results to rerank
            weights: Optional custom signal weights

        Returns:
            Reranked results sorted by rerank_score

        Raises:
            ValueError: If results empty or weights invalid
        """
        if not results:
            raise ValueError("Cannot rerank: results empty")

        # Use default weights if not provided
        weights = weights or RerankWeights()

        # Validate weights
        if not weights.validate_sum():
            raise ValueError("Weights must sum to 1.0 (within 0.01 tolerance)")

        # Calculate signals and rerank score for each result
        reranked = []
        for result in results:
            signals = self.calculate_signals(query, result)

            # Calculate weighted rerank score
            rerank_score = (
                signals.vector_score * weights.vector_score
                + signals.term_overlap * weights.term_overlap
                + signals.title_match * weights.title_match
                + signals.freshness * weights.freshness
            )

            # Update result with reranking info
            result.rerank_score = rerank_score
            result.rerank_signals = {
                "vector_score": signals.vector_score,
                "term_overlap": signals.term_overlap,
                "title_match": signals.title_match,
                "freshness": signals.freshness,
            }

            reranked.append(result)

        # Sort by rerank_score descending
        reranked.sort(key=lambda r: r.rerank_score or 0.0, reverse=True)

        return reranked

    def calculate_signals(self, query: str, result: SearchResult) -> RerankSignals:
        """Calculate individual reranking signals for a result.

        Args:
            query: Search query
            result: Single search result

        Returns:
            RerankSignals with all signal values (0.0-1.0)
        """
        # Signal 1: Vector score (already normalized 0-1)
        vector_score = result.score

        # Signal 2: Term overlap (fraction of query terms in content)
        query_terms = set(query.lower().split())
        content_terms = set(result.content.lower().split())
        term_overlap = (
            len(query_terms & content_terms) / max(len(query_terms), 1)
            if query_terms
            else 0.0
        )

        # Signal 3: Title match (fraction of query terms in title)
        title_terms = set(result.title.lower().split())
        title_match = (
            len(query_terms & title_terms) / max(len(query_terms), 1)
            if query_terms
            else 0.0
        )

        # Signal 4: Freshness (temporal decay)
        # For now, we'll use a neutral value since we don't have indexed_at
        # In a real implementation, this would use result.indexed_at
        freshness = 0.5  # Neutral value

        # If the result has metadata with a date, we could use it:
        # days_old = (datetime.now() - result.indexed_at).days
        # freshness = max(0.0, 1.0 - days_old / 365.0)

        return RerankSignals(
            vector_score=vector_score,
            term_overlap=term_overlap,
            title_match=title_match,
            freshness=freshness,
        )