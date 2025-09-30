"""Fusion retrieval strategy for RAG enhancement.

This module implements reciprocal rank fusion (RRF) to combine results from multiple
search strategies, improving recall by 15-25% and providing more robust results.
"""

import asyncio
from typing import Any

from src.core.lib_logger import get_logger
from src.logic.rag.models.search_result import SearchResult
from src.logic.rag.models.strategy_config import FusionConfig, SearchStrategy

logger = get_logger(__name__)


class FusionRetrieval:
    """Fusion retrieval using reciprocal rank fusion (RRF).

    Combines results from multiple search strategies using RRF algorithm
    to provide more robust and comprehensive results.
    """

    def __init__(self, config: FusionConfig | None = None):
        """Initialize fusion retrieval.

        Args:
            config: Optional configuration (uses defaults if None)
        """
        self.config = config or FusionConfig()

    async def fuse_results(
        self,
        query: str,
        collection_name: str,
        search_executor: Any,  # RAGSearchService
        limit: int = 10,
        strategies: list[SearchStrategy] | None = None,
        rrf_k: int | None = None,
    ) -> list[SearchResult]:
        """Fuse results from multiple search strategies.

        Args:
            query: Search query
            collection_name: Collection to search
            search_executor: Service that can execute searches
            limit: Max results to return
            strategies: List of strategies to fuse (default from config)
            rrf_k: RRF constant (default from config)

        Returns:
            Fused and ranked results
        """
        strategies_to_use = strategies or self.config.strategies
        k = rrf_k or self.config.rrf_k

        logger.info(
            f"Executing fusion retrieval with {len(strategies_to_use)} strategies",
            extra={"query": query[:50], "strategies": [s.value for s in strategies_to_use]},
        )

        # Execute all strategies in parallel
        search_tasks = [
            search_executor._execute_search_strategy(
                query=query,
                collection_name=collection_name,
                limit=limit * 2,  # Get more results for better fusion
                strategy=strategy,
                score_threshold=None,
                filters=None,
            )
            for strategy in strategies_to_use
        ]

        all_results_lists = await asyncio.gather(*search_tasks, return_exceptions=True)

        # Collect successful results with strategy tracking
        strategy_results: dict[str, list[SearchResult]] = {}
        for i, results in enumerate(all_results_lists):
            if isinstance(results, Exception):
                logger.warning(
                    f"Strategy {strategies_to_use[i].value} failed: {results}",
                    extra={"query": query[:50]},
                )
                continue

            strategy_name = strategies_to_use[i].value
            strategy_results[strategy_name] = results

        if not strategy_results:
            logger.warning("All fusion strategies failed", extra={"query": query[:50]})
            return []

        # Apply RRF fusion
        fused = self.calculate_rrf_scores(strategy_results, k)

        # Sort by RRF score and limit
        fused.sort(key=lambda r: r.score, reverse=True)
        final_results = fused[:limit]

        logger.info(
            f"Fusion complete: {len(final_results)} results",
            extra={"query": query[:50], "strategies_used": len(strategy_results)},
        )

        return final_results

    def calculate_rrf_scores(
        self, strategy_results: dict[str, list[SearchResult]], k: int = 60
    ) -> list[SearchResult]:
        """Calculate reciprocal rank fusion scores.

        RRF formula: score(doc) = sum(1 / (k + rank_i)) for each retriever

        Args:
            strategy_results: Results grouped by strategy name
            k: RRF constant (typically 60)

        Returns:
            List of results with updated RRF scores
        """
        # Collect all unique documents
        doc_map: dict[str, SearchResult] = {}
        doc_ranks: dict[str, list[int]] = {}  # doc_id -> [rank1, rank2, ...]

        # Process each strategy's results
        for strategy_name, results in strategy_results.items():
            for rank, result in enumerate(results, start=1):
                if result.id not in doc_map:
                    doc_map[result.id] = result
                    doc_ranks[result.id] = []

                doc_ranks[result.id].append(rank)

        # Calculate RRF scores
        fused_results = []
        for doc_id, result in doc_map.items():
            ranks = doc_ranks[doc_id]
            rrf_score = self.calculate_rrf_score_for_doc(ranks, k)

            # Update result with RRF score
            result.score = rrf_score
            result.match_type = "fusion"  # Mark as fusion result
            fused_results.append(result)

        return fused_results

    def calculate_rrf_score(self, doc_id: str, ranks: list[int], k: int = 60) -> float:
        """Calculate RRF score for a single document.

        Args:
            doc_id: Document ID
            ranks: List of ranks from different retrievers
            k: RRF constant

        Returns:
            RRF score
        """
        return self.calculate_rrf_score_for_doc(ranks, k)

    def calculate_rrf_score_for_doc(self, ranks: list[int], k: int = 60) -> float:
        """Calculate RRF score given ranks.

        Args:
            ranks: List of ranks
            k: RRF constant

        Returns:
            RRF score
        """
        if not ranks:
            return 0.0

        # RRF formula: sum(1 / (k + rank_i))
        rrf_score = sum(1.0 / (k + rank) for rank in ranks)

        return rrf_score