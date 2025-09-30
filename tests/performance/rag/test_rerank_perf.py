"""Performance tests for reranking service.

Performance requirement: Reranking 10 results must complete in <50ms

This test validates that the fast multi-signal reranking implementation
meets the performance target which is 95% faster than the old embedding-based
reranking (which took 1000-1500ms).
"""

import asyncio
import time
import pytest
from src.logic.rag.core.reranking_service import RerankingService
from src.logic.rag.models.search_result import SearchResult
from src.logic.rag.models.strategy_config import RerankWeights


@pytest.fixture
def reranking_service():
    """Create reranking service instance."""
    return RerankingService()


@pytest.fixture
def sample_results():
    """Create sample search results for testing."""
    results = []
    for i in range(10):
        result = SearchResult(
            id=f"doc-{i}",
            url=f"https://example.com/doc-{i}",
            title=f"Docker Guide Part {i}",
            content=f"This document covers Docker installation and security practices for containers. "
                   f"It includes best practices for production deployments. Document number {i}.",
            score=0.9 - (i * 0.05),  # Decreasing scores
            project="docker-docs",
            match_type="semantic"
        )
        results.append(result)
    return results


@pytest.mark.asyncio
async def test_rerank_performance_target(reranking_service, sample_results):
    """Test reranking 10 results completes in <50ms."""
    query = "docker security best practices"

    # Warmup run
    await reranking_service.rerank(query, sample_results[:])

    # Timed run
    start = time.perf_counter()
    reranked = await reranking_service.rerank(query, sample_results[:])
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Verify performance requirement
    assert elapsed_ms < 50.0, f"Reranking took {elapsed_ms:.2f}ms, expected <50ms"

    # Verify results
    assert len(reranked) == 10
    assert all(r.rerank_score is not None for r in reranked)
    assert all(r.rerank_signals is not None for r in reranked)


@pytest.mark.asyncio
async def test_rerank_performance_average(reranking_service, sample_results):
    """Test average reranking performance over multiple runs."""
    query = "docker security"
    runs = 10
    timings = []

    for _ in range(runs):
        start = time.perf_counter()
        await reranking_service.rerank(query, sample_results[:])
        elapsed_ms = (time.perf_counter() - start) * 1000
        timings.append(elapsed_ms)

    avg_ms = sum(timings) / len(timings)
    max_ms = max(timings)
    min_ms = min(timings)

    # Average should be well under target
    assert avg_ms < 50.0, f"Average reranking time {avg_ms:.2f}ms exceeds 50ms"

    # Even slowest run should be under target
    assert max_ms < 50.0, f"Slowest run {max_ms:.2f}ms exceeds 50ms"

    print(f"\nReranking performance: avg={avg_ms:.2f}ms, min={min_ms:.2f}ms, max={max_ms:.2f}ms")


@pytest.mark.asyncio
async def test_rerank_performance_with_custom_weights(reranking_service, sample_results):
    """Test reranking performance with custom weights."""
    query = "docker installation"

    custom_weights = RerankWeights(
        vector_score=0.6,
        term_overlap=0.2,
        title_match=0.1,
        freshness=0.1
    )

    start = time.perf_counter()
    reranked = await reranking_service.rerank(query, sample_results[:], custom_weights)
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 50.0, f"Reranking with custom weights took {elapsed_ms:.2f}ms"
    assert len(reranked) == 10


@pytest.mark.asyncio
async def test_rerank_performance_different_sizes(reranking_service):
    """Test reranking performance scales linearly with result count."""
    query = "docker"
    timings = {}

    for size in [5, 10, 20, 50]:
        results = [
            SearchResult(
                id=f"doc-{i}",
                url=f"https://example.com/doc-{i}",
                title=f"Document {i}",
                content=f"Content for document {i}",
                score=0.9,
                project="test",
                match_type="semantic"
            )
            for i in range(size)
        ]

        start = time.perf_counter()
        await reranking_service.rerank(query, results)
        elapsed_ms = (time.perf_counter() - start) * 1000
        timings[size] = elapsed_ms

    # 10 results should be under 50ms
    assert timings[10] < 50.0, f"10 results took {timings[10]:.2f}ms"

    # Performance should scale roughly linearly
    # 20 results should be < 2x the time of 10 results
    if timings[10] > 0:
        ratio = timings[20] / timings[10]
        assert ratio < 2.5, f"Performance scaling issue: {ratio:.2f}x for 2x results"

    print(f"\nScaling: 5={timings[5]:.2f}ms, 10={timings[10]:.2f}ms, "
          f"20={timings[20]:.2f}ms, 50={timings[50]:.2f}ms")


@pytest.mark.asyncio
async def test_rerank_performance_concurrent(reranking_service, sample_results):
    """Test concurrent reranking operations don't degrade performance."""
    query = "docker"
    concurrent_requests = 5

    async def timed_rerank():
        start = time.perf_counter()
        await reranking_service.rerank(query, sample_results[:])
        return (time.perf_counter() - start) * 1000

    # Run concurrent reranking operations
    timings = await asyncio.gather(*[timed_rerank() for _ in range(concurrent_requests)])

    # Each operation should still be under 50ms
    for i, elapsed_ms in enumerate(timings):
        assert elapsed_ms < 50.0, f"Concurrent request {i} took {elapsed_ms:.2f}ms"

    avg_ms = sum(timings) / len(timings)
    print(f"\nConcurrent reranking: avg={avg_ms:.2f}ms across {concurrent_requests} requests")


@pytest.mark.asyncio
async def test_rerank_performance_p95_latency(reranking_service, sample_results):
    """Test P95 latency meets requirements."""
    query = "docker"
    runs = 100
    timings = []

    for _ in range(runs):
        start = time.perf_counter()
        await reranking_service.rerank(query, sample_results[:])
        elapsed_ms = (time.perf_counter() - start) * 1000
        timings.append(elapsed_ms)

    timings.sort()
    p50 = timings[50]
    p95 = timings[95]
    p99 = timings[99]

    # P95 should be well under target
    assert p95 < 50.0, f"P95 latency {p95:.2f}ms exceeds 50ms"

    print(f"\nLatency percentiles: P50={p50:.2f}ms, P95={p95:.2f}ms, P99={p99:.2f}ms")


@pytest.mark.asyncio
async def test_rerank_performance_long_query(reranking_service, sample_results):
    """Test performance with long queries."""
    # Simulate a complex multi-part query
    long_query = "docker installation security best practices production deployment containers orchestration monitoring logging troubleshooting performance optimization"

    start = time.perf_counter()
    reranked = await reranking_service.rerank(long_query, sample_results[:])
    elapsed_ms = (time.perf_counter() - start) * 1000

    assert elapsed_ms < 50.0, f"Long query reranking took {elapsed_ms:.2f}ms"
    assert len(reranked) == 10


@pytest.mark.asyncio
async def test_rerank_performance_long_content(reranking_service):
    """Test performance with long document content."""
    query = "docker"

    # Create results with long content
    long_content = "Docker security best practices. " * 100  # ~3000 chars

    results = [
        SearchResult(
            id=f"doc-{i}",
            url=f"https://example.com/doc-{i}",
            title=f"Document {i}",
            content=long_content,
            score=0.9,
            project="test",
            match_type="semantic"
        )
        for i in range(10)
    ]

    start = time.perf_counter()
    await reranking_service.rerank(query, results)
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Should still meet performance target even with long content
    assert elapsed_ms < 50.0, f"Long content reranking took {elapsed_ms:.2f}ms"


@pytest.mark.asyncio
async def test_rerank_zero_overhead_for_empty_results(reranking_service):
    """Test reranking empty results has minimal overhead."""
    query = "docker"

    start = time.perf_counter()
    reranked = await reranking_service.rerank(query, [])
    elapsed_ms = (time.perf_counter() - start) * 1000

    # Should be nearly instant
    assert elapsed_ms < 5.0, f"Empty results reranking took {elapsed_ms:.2f}ms"
    assert len(reranked) == 0