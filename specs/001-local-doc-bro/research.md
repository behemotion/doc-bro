# Research Document: DocBro Implementation

**Date**: 2025-09-25
**Feature**: Documentation Web Crawler with Local RAG

## Technology Decisions

### 1. Vector Database Selection
**Decision**: Qdrant
**Rationale**:
- Fully local deployment via Docker
- Production-ready with persistence
- Rich query API with filtering
- Supports large-scale vector operations (>1GB per project)
- Python client library with async support
**Alternatives considered**:
- ChromaDB: Less mature, performance issues at scale
- Weaviate: More complex setup, overkill for local use
- Pinecone: Cloud-only, violates local-first requirement

### 2. Embedding Model and Service
**Decision**: Ollama with mxbai-embed-large (default)
**Rationale**:
- Fully local inference, no API keys required
- Easy model switching via Ollama's model management
- mxbai-embed-large provides good quality/performance balance
- Support for multiple models (nomic-embed-text as alternative)
**Alternatives considered**:
- OpenAI embeddings: Requires API, not local
- Sentence-transformers direct: More complex model management
- Hugging Face inference: Heavier dependencies

### 3. Web Crawling Strategy
**Decision**: httpx + BeautifulSoup4 with async crawling
**Rationale**:
- httpx provides modern async HTTP with connection pooling
- BeautifulSoup4 is robust for HTML parsing
- Async allows efficient concurrent crawling with rate limiting
- Respects robots.txt and implements exponential backoff
**Alternatives considered**:
- Scrapy: Overkill for documentation crawling
- Playwright: Too heavy for simple HTML crawling
- requests + threading: Less efficient than async

### 4. MCP Server Implementation
**Decision**: FastAPI with WebSocket support
**Rationale**:
- Native async support matches crawler architecture
- WebSocket enables real-time agent communication
- Auto-generated OpenAPI documentation
- Lightweight and performant
**Alternatives considered**:
- Flask: No native async support
- Django: Too heavy for simple MCP server
- Raw websockets: Less structure and documentation

### 5. CLI Framework
**Decision**: Click with Rich for output formatting
**Rationale**:
- Click provides clean command structure and help generation
- Rich enables beautiful tables and progress bars
- Both are lightweight with minimal dependencies
- Excellent Python ecosystem integration
**Alternatives considered**:
- argparse: More verbose, less features
- Typer: Built on Click but adds complexity
- Fire: Too magical, less explicit

### 6. Database for Metadata
**Decision**: SQLite with aiosqlite
**Rationale**:
- Zero configuration, fully local
- Async support via aiosqlite
- Sufficient for project metadata and crawl sessions
- Easy backup and portability
**Alternatives considered**:
- PostgreSQL: Overkill for metadata
- JSON files: No query capabilities
- TinyDB: Limited async support

### 7. RAG Strategy Implementation
**Decision**: Multi-strategy approach with pluggable strategies
**Rationale**:
- Semantic search as base strategy
- Reranking with cross-encoder for quality
- Context expansion for comprehensive answers
- Query decomposition for complex questions
**Implementation approach**:
- Strategy pattern for easy extension
- Configurable per-project or per-query

### 8. Package Distribution
**Decision**: Python package with pyproject.toml, distributable via pip/uv/uvx
**Rationale**:
- Standard Python packaging
- uv/uvx support for modern Python workflows
- Easy installation with dependencies
- Cross-platform compatibility
**Setup approach**:
- Docker Compose for services (Qdrant, Redis)
- Python package for application
- Setup script for one-command installation

## Best Practices Research

### Web Crawling Best Practices
- Implement exponential backoff with jitter for retries
- Respect robots.txt and crawl-delay directives
- Use connection pooling for efficiency
- Implement circuit breaker for failing sites
- Store raw HTML for potential reprocessing
- Track crawl sessions for incremental updates

### Vector Database Best Practices
- Use namespaces/collections per project for isolation
- Implement chunking strategy (sliding window with overlap)
- Store metadata with vectors for filtering
- Use batch operations for efficiency
- Implement vector versioning for updates
- Regular compaction for performance

### RAG Implementation Best Practices
- Chunk size optimization (512-1024 tokens typical)
- Overlap between chunks (10-20%)
- Hybrid search (semantic + keyword) when possible
- Result reranking for quality
- Context window management
- Query expansion for better recall

### CLI Design Best Practices
- Consistent command naming (verb-noun)
- Comprehensive --help for all commands
- Progress indicators for long operations
- Structured output options (JSON, table)
- Sensible defaults with override flags
- Clear error messages with remediation hints

## Integration Patterns

### Ollama Integration
```python
# Pattern: Health check before operations
# Pattern: Model download on first use
# Pattern: Configurable model selection
# Pattern: Batch embedding for efficiency
```

### Qdrant Integration
```python
# Pattern: Collection per project
# Pattern: Async client with connection pooling
# Pattern: Optimistic concurrency control
# Pattern: Point batching for inserts
```

### MCP Protocol Implementation
```python
# Pattern: JSON-RPC over WebSocket
# Pattern: Session management per agent
# Pattern: Request/response correlation
# Pattern: Capability negotiation
```

## Performance Considerations

### Crawling Performance
- Target: 2-5 pages/second with rate limiting
- Memory: Stream large documents
- Parallelism: 5-10 concurrent connections
- Caching: Redis for deduplication

### Query Performance
- Target: <100ms for vector search
- Target: <500ms for RAG with reranking
- Optimization: Pre-compute embeddings
- Optimization: Cache frequent queries

### Storage Efficiency
- Compression for stored HTML
- Vector quantization if needed
- Incremental crawl updates
- Old session cleanup strategy

## Security Considerations

### Web Crawling Security
- User-agent identification
- Respect authentication boundaries
- No credential storage
- URL validation and sanitization

### Local Storage Security
- File permissions for databases
- No sensitive data in logs
- Secure MCP authentication (future)
- Input validation for all commands

## Resolved Clarifications

All NEEDS CLARIFICATION items from the specification have been resolved:
- ✅ Default outdated interval: 60 days
- ✅ CLI commands defined: crawl, list, query, rename, delete, recrawl, export, import, config, status
- ✅ Concurrent crawling: Single crawl only, queue others
- ✅ RAG strategies: Semantic search, reranking, context expansion, query decomposition
- ✅ Network failure handling: 5 retries with exponential backoff
- ✅ Tool name: "docbro" as CLI command

## Next Steps

With all technical decisions made and clarifications resolved, Phase 1 can proceed with:
1. Data model design based on identified entities
2. API contract generation for MCP server
3. CLI command contracts
4. Contract test generation
5. Quickstart guide creation