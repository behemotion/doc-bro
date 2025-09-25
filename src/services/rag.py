"""RAG (Retrieval-Augmented Generation) search service."""

import asyncio
import re
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
import logging
import hashlib

from ..models import QueryResult, QueryResponse
from ..lib.config import DocBroConfig
from ..lib.logger import get_component_logger
from .vector_store import VectorStoreService, VectorStoreError
from .embeddings import EmbeddingService, EmbeddingError


class RAGError(Exception):
    """RAG service operation error."""
    pass


class RAGSearchService:
    """RAG-powered search service combining semantic and traditional search."""

    def __init__(
        self,
        vector_store: VectorStoreService,
        embedding_service: EmbeddingService,
        config: Optional[DocBroConfig] = None
    ):
        """Initialize RAG search service."""
        self.vector_store = vector_store
        self.embedding_service = embedding_service
        self.config = config or DocBroConfig()
        self.logger = get_component_logger("rag")

        # Search configuration
        self.default_limit = 10
        self.default_score_threshold = 0.7
        self.chunk_size = 1000
        self.chunk_overlap = 100

        # Query cache
        self._query_cache: Dict[str, QueryResponse] = {}
        self._cache_ttl = 300  # 5 minutes

    async def search(
        self,
        query: str,
        collection_name: str,
        limit: int = 10,
        score_threshold: Optional[float] = None,
        strategy: str = "semantic",
        expand_context: bool = False,
        rerank: bool = False,
        filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search for relevant documents using RAG strategies."""
        if not query.strip():
            self.logger.warning("Empty query provided")
            return []

        start_time = datetime.utcnow()

        try:
            # Check cache
            cache_key = self._get_cache_key(query, collection_name, limit, strategy)
            if cache_key in self._query_cache:
                cached_response = self._query_cache[cache_key]
                if self._is_cache_valid(cached_response):
                    self.logger.debug("Cache hit for query", extra={
                        "query": query[:50],
                        "strategy": strategy
                    })
                    return cached_response.results

            # Choose search strategy
            if strategy == "semantic":
                results = await self._semantic_search(
                    query, collection_name, limit, score_threshold, filters
                )
            elif strategy == "hybrid":
                results = await self._hybrid_search(
                    query, collection_name, limit, score_threshold, filters
                )
            elif strategy == "advanced":
                results = await self._advanced_search(
                    query, collection_name, limit, score_threshold, filters
                )
            else:
                raise RAGError(f"Unknown search strategy: {strategy}")

            # Post-process results
            if expand_context:
                results = await self._expand_context(results)

            if rerank and len(results) > 1:
                results = await self._rerank_results(query, results)

            # Cache results
            took_ms = int((datetime.utcnow() - start_time).total_seconds() * 1000)
            response = QueryResponse(
                query=query,
                results=[QueryResult(**result) for result in results],
                total=len(results),
                limit=limit,
                took_ms=took_ms,
                strategy=strategy,
                filters=filters or {},
                timestamp=start_time
            )
            self._query_cache[cache_key] = response

            self.logger.info("Search completed", extra={
                "query": query[:50],
                "strategy": strategy,
                "results_count": len(results),
                "took_ms": took_ms
            })

            return results

        except Exception as e:
            self.logger.error("Search failed", extra={
                "query": query[:50],
                "strategy": strategy,
                "error": str(e)
            })
            raise RAGError(f"Search failed: {e}")

    async def _semantic_search(
        self,
        query: str,
        collection_name: str,
        limit: int,
        score_threshold: Optional[float],
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Perform semantic vector search."""
        try:
            # Create query embedding
            query_embedding = await self.embedding_service.create_embedding(query)

            # Perform vector search
            vector_results = await self.vector_store.search(
                collection_name=collection_name,
                query_embedding=query_embedding,
                limit=limit,
                score_threshold=score_threshold,
                filter_conditions=filters
            )

            # Convert to standard result format
            results = []
            for result in vector_results:
                metadata = result.get("metadata", {})

                query_result = {
                    "id": result["id"],
                    "url": metadata.get("url", ""),
                    "title": metadata.get("title", ""),
                    "content": metadata.get("content", ""),
                    "score": result["score"],
                    "project": metadata.get("project", ""),
                    "project_id": metadata.get("project_id", ""),
                    "page_id": result["id"],
                    "match_type": "semantic",
                    "query_terms": self._extract_query_terms(query)
                }
                results.append(query_result)

            return results

        except (VectorStoreError, EmbeddingError) as e:
            raise RAGError(f"Semantic search failed: {e}")

    async def _hybrid_search(
        self,
        query: str,
        collection_name: str,
        limit: int,
        score_threshold: Optional[float],
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Perform hybrid semantic + keyword search."""
        try:
            # Run semantic search
            semantic_results = await self._semantic_search(
                query, collection_name, limit * 2, score_threshold, filters
            )

            # Run keyword search (simulated via metadata filters)
            keyword_results = await self._keyword_search(
                query, collection_name, limit * 2, filters
            )

            # Combine and deduplicate results
            combined_results = self._combine_search_results(
                semantic_results, keyword_results, limit
            )

            return combined_results

        except Exception as e:
            raise RAGError(f"Hybrid search failed: {e}")

    async def _advanced_search(
        self,
        query: str,
        collection_name: str,
        limit: int,
        score_threshold: Optional[float],
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Perform advanced search with query decomposition."""
        try:
            # Decompose complex queries
            sub_queries = await self.decompose_query(query)

            if len(sub_queries) <= 1:
                # Fall back to semantic search for simple queries
                return await self._semantic_search(
                    query, collection_name, limit, score_threshold, filters
                )

            # Search for each sub-query
            all_results = []
            for sub_query in sub_queries:
                sub_results = await self._semantic_search(
                    sub_query, collection_name, limit, score_threshold, filters
                )
                all_results.extend(sub_results)

            # Aggregate and rank results
            aggregated_results = self._aggregate_sub_results(
                query, all_results, limit
            )

            return aggregated_results

        except Exception as e:
            raise RAGError(f"Advanced search failed: {e}")

    async def _keyword_search(
        self,
        query: str,
        collection_name: str,
        limit: int,
        filters: Optional[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Simulate keyword search using vector search with keyword matching."""
        # For now, this is a simplified implementation
        # In a full implementation, you might use a separate keyword index

        query_terms = self._extract_query_terms(query)

        # Create a simple filter for content containing query terms
        keyword_filters = filters or {}

        # This is a simplified approach - real keyword search would be more sophisticated
        try:
            # Use semantic search but with lower threshold to catch more results
            results = await self._semantic_search(
                query, collection_name, limit, 0.3, keyword_filters
            )

            # Filter results that contain query terms in content
            keyword_filtered = []
            for result in results:
                content = result.get("content", "").lower()
                if any(term.lower() in content for term in query_terms):
                    result["match_type"] = "keyword"
                    keyword_filtered.append(result)

            return keyword_filtered[:limit]

        except Exception as e:
            self.logger.warning("Keyword search failed", extra={"error": str(e)})
            return []

    def _combine_search_results(
        self,
        semantic_results: List[Dict[str, Any]],
        keyword_results: List[Dict[str, Any]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Combine semantic and keyword search results."""
        # Create a map to track unique results by ID
        result_map = {}

        # Add semantic results with higher weight
        for result in semantic_results:
            result_id = result["id"]
            if result_id not in result_map:
                result["hybrid_score"] = result["score"] * 0.7  # Semantic weight
                result["match_type"] = "hybrid_semantic"
                result_map[result_id] = result

        # Add keyword results with lower weight, boost if already exists
        for result in keyword_results:
            result_id = result["id"]
            if result_id in result_map:
                # Boost existing result
                existing = result_map[result_id]
                existing["hybrid_score"] = existing.get("hybrid_score", 0) + (result["score"] * 0.3)
                existing["match_type"] = "hybrid_both"
            else:
                result["hybrid_score"] = result["score"] * 0.3  # Keyword weight
                result["match_type"] = "hybrid_keyword"
                result_map[result_id] = result

        # Sort by hybrid score and return top results
        combined_results = list(result_map.values())
        combined_results.sort(key=lambda x: x.get("hybrid_score", 0), reverse=True)

        return combined_results[:limit]

    async def _expand_context(self, results: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Expand context around search results."""
        # This is a placeholder for context expansion
        # In a full implementation, you would retrieve surrounding content

        for result in results:
            # Add mock context for now
            content = result.get("content", "")
            if content:
                # Simulate context before and after
                words = content.split()
                if len(words) > 20:
                    mid_point = len(words) // 2
                    result["context_before"] = " ".join(words[max(0, mid_point-10):mid_point])
                    result["context_after"] = " ".join(words[mid_point:min(len(words), mid_point+10)])

        return results

    async def _rerank_results(
        self,
        query: str,
        results: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """Rerank results using more sophisticated scoring."""
        try:
            query_embedding = await self.embedding_service.create_embedding(query)

            for result in results:
                content = result.get("content", "")
                if content:
                    # Create embedding for the result content
                    content_embedding = await self.embedding_service.create_embedding(content)

                    # Calculate similarity
                    similarity = await self.embedding_service.similarity(
                        query_embedding, content_embedding
                    )

                    # Set rerank score
                    result["rerank_score"] = similarity

            # Sort by rerank score
            results.sort(key=lambda x: x.get("rerank_score", 0), reverse=True)

            return results

        except Exception as e:
            self.logger.warning("Reranking failed", extra={"error": str(e)})
            return results

    async def decompose_query(self, query: str) -> List[str]:
        """Decompose complex queries into simpler sub-queries."""
        # Simple query decomposition logic
        query = query.strip()

        # Split on common conjunctions
        decomposition_patterns = [
            r'\s+and\s+',
            r'\s+or\s+',
            r'\s*,\s*',
            r'\s*;\s*'
        ]

        sub_queries = [query]

        for pattern in decomposition_patterns:
            new_sub_queries = []
            for sub_query in sub_queries:
                parts = re.split(pattern, sub_query, flags=re.IGNORECASE)
                if len(parts) > 1:
                    new_sub_queries.extend([part.strip() for part in parts if part.strip()])
                else:
                    new_sub_queries.append(sub_query)
            sub_queries = new_sub_queries

        # Filter out very short sub-queries
        sub_queries = [q for q in sub_queries if len(q.split()) >= 2]

        # If decomposition resulted in only short queries, return original
        if not sub_queries:
            return [query]

        self.logger.debug("Query decomposed", extra={
            "original_query": query,
            "sub_queries": sub_queries
        })

        return sub_queries

    def _aggregate_sub_results(
        self,
        original_query: str,
        all_results: List[Dict[str, Any]],
        limit: int
    ) -> List[Dict[str, Any]]:
        """Aggregate results from sub-queries."""
        # Group results by ID and aggregate scores
        result_map = {}

        for result in all_results:
            result_id = result["id"]
            if result_id not in result_map:
                result_map[result_id] = result
                result_map[result_id]["sub_query_matches"] = 1
                result_map[result_id]["aggregated_score"] = result["score"]
            else:
                existing = result_map[result_id]
                existing["sub_query_matches"] += 1
                existing["aggregated_score"] = max(existing["aggregated_score"], result["score"])
                # Boost score for appearing in multiple sub-queries
                existing["aggregated_score"] *= (1 + existing["sub_query_matches"] * 0.1)

        # Sort by aggregated score
        aggregated_results = list(result_map.values())
        aggregated_results.sort(key=lambda x: x["aggregated_score"], reverse=True)

        return aggregated_results[:limit]

    def _extract_query_terms(self, query: str) -> List[str]:
        """Extract meaningful terms from query."""
        # Remove common stop words and extract terms
        stop_words = {
            "the", "a", "an", "and", "or", "but", "in", "on", "at", "to", "for",
            "of", "with", "by", "from", "up", "about", "into", "through", "during",
            "before", "after", "above", "below", "between", "among", "is", "are",
            "was", "were", "be", "been", "being", "have", "has", "had", "do", "does",
            "did", "will", "would", "could", "should", "may", "might", "must", "can"
        }

        # Extract words and filter
        words = re.findall(r'\b\w+\b', query.lower())
        terms = [word for word in words if word not in stop_words and len(word) > 2]

        return terms

    def _get_cache_key(
        self,
        query: str,
        collection_name: str,
        limit: int,
        strategy: str
    ) -> str:
        """Generate cache key for query."""
        content = f"{query}:{collection_name}:{limit}:{strategy}".encode('utf-8')
        return hashlib.sha256(content).hexdigest()

    def _is_cache_valid(self, response: QueryResponse) -> bool:
        """Check if cached response is still valid."""
        age = (datetime.utcnow() - response.timestamp).total_seconds()
        return age < self._cache_ttl

    async def index_documents(
        self,
        collection_name: str,
        documents: List[Dict[str, Any]],
        chunk_size: Optional[int] = None,
        chunk_overlap: Optional[int] = None
    ) -> int:
        """Index documents for search."""
        if not documents:
            return 0

        chunk_size = chunk_size or self.chunk_size
        chunk_overlap = chunk_overlap or self.chunk_overlap

        try:
            # Ensure collection exists
            if not await self.vector_store.collection_exists(collection_name):
                await self.vector_store.create_collection(collection_name)

            # Chunk and embed documents
            processed_documents = []

            for doc in documents:
                chunks = await self.chunk_document(
                    doc, chunk_size, chunk_overlap
                )

                for chunk in chunks:
                    # Create embedding for chunk content
                    embedding = await self.embedding_service.create_embedding(
                        chunk["content"]
                    )

                    processed_doc = {
                        "id": chunk["id"],
                        "embedding": embedding,
                        "metadata": {
                            "title": chunk["title"],
                            "content": chunk["content"],
                            "url": chunk["url"],
                            "project": chunk["project"],
                            "project_id": chunk.get("project_id", ""),
                            "chunk_index": chunk.get("chunk_index", 0),
                            "parent_id": doc["id"]
                        }
                    }
                    processed_documents.append(processed_doc)

            # Batch insert into vector store
            indexed_count = await self.vector_store.upsert_documents(
                collection_name, processed_documents
            )

            self.logger.info("Documents indexed", extra={
                "collection_name": collection_name,
                "original_documents": len(documents),
                "chunks_indexed": indexed_count
            })

            return indexed_count

        except Exception as e:
            self.logger.error("Failed to index documents", extra={
                "collection_name": collection_name,
                "documents_count": len(documents),
                "error": str(e)
            })
            raise RAGError(f"Failed to index documents: {e}")

    async def chunk_document(
        self,
        document: Dict[str, Any],
        chunk_size: int = 1000,
        overlap: int = 50
    ) -> List[Dict[str, Any]]:
        """Split document into chunks for indexing."""
        content = document.get("content", "")
        if not content:
            return []

        # Simple chunking by character count with overlap
        chunks = []
        chunk_index = 0
        start = 0

        while start < len(content):
            end = start + chunk_size

            # Try to break at word boundary
            if end < len(content):
                # Look for last space within reasonable distance
                for i in range(end, max(start + chunk_size - 100, start), -1):
                    if content[i].isspace():
                        end = i
                        break

            chunk_content = content[start:end].strip()
            if chunk_content:
                # Generate a UUID for the chunk
                import uuid
                chunk_id = str(uuid.uuid4())

                chunk = {
                    "id": chunk_id,
                    "title": document.get("title", ""),
                    "content": chunk_content,
                    "url": document.get("url", ""),
                    "project": document.get("project", ""),
                    "project_id": document.get("project_id", ""),
                    "chunk_index": chunk_index,
                    "parent_id": document["id"]
                }
                chunks.append(chunk)

            # Move start position with overlap
            start = max(start + chunk_size - overlap, end)
            chunk_index += 1

        return chunks

    async def search_multi_project(
        self,
        query: str,
        project_names: List[str],
        limit: int = 15,
        strategy: str = "semantic"
    ) -> List[Dict[str, Any]]:
        """Search across multiple projects."""
        all_results = []

        # Search each project
        for project_name in project_names:
            collection_name = f"project_{project_name}"

            try:
                if await self.vector_store.collection_exists(collection_name):
                    project_results = await self.search(
                        query=query,
                        collection_name=collection_name,
                        limit=limit,
                        strategy=strategy
                    )
                    all_results.extend(project_results)

            except Exception as e:
                self.logger.warning("Failed to search project", extra={
                    "project_name": project_name,
                    "error": str(e)
                })
                continue

        # Sort all results by score and limit
        all_results.sort(key=lambda x: x.get("score", 0), reverse=True)
        return all_results[:limit]

    def clear_cache(self) -> int:
        """Clear query cache."""
        cache_size = len(self._query_cache)
        self._query_cache.clear()

        self.logger.info("Query cache cleared", extra={
            "cleared_entries": cache_size
        })

        return cache_size