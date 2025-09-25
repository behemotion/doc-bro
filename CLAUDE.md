# DocBro Development Guidelines

**Last Updated:** 2025-01-25

## Project Overview
DocBro is a documentation crawler and search tool with RAG (Retrieval-Augmented Generation) capabilities and MCP (Model Context Protocol) server integration for coding agents.

## Implementation Status
✅ **90% Complete** - Core functionality implemented and tested following TDD methodology

### Completed Components
- ✅ Data Models (Pydantic v2 with validation)
- ✅ Database Service (Async SQLite with full CRUD)
- ✅ Vector Store Service (Qdrant integration)
- ✅ Embedding Service (Ollama integration)
- ✅ RAG Search Service (Multiple strategies)
- ✅ Documentation Crawler (Rate limiting, robots.txt)
- ✅ MCP Server (FastAPI with WebSocket)
- ✅ CLI Interface (Rich tables and progress)
- ✅ Docker Configuration
- ✅ Setup and Run Scripts

## Active Technologies
- **Python 3.13.5** - Latest stable with async/await
- **Qdrant 1.13.0** - Vector database (Docker)
- **Redis 7.2** - Cache and queue (Docker)
- **Ollama** - Local embeddings (mxbai-embed-large, nomic-embed-text)
- **SQLite** - Metadata storage (local)
- **FastAPI** - MCP server implementation
- **Click + Rich** - CLI with beautiful output
- **httpx + BeautifulSoup4** - Web crawling
- **pytest 8.x** - Test framework with async support
- Python 3.11+ + Qdrant (vector database), Ollama (embeddings), MCP protocol server, Click (CLI), BeautifulSoup4 (web crawling) (001-local-doc-bro)
- Qdrant vector database for embeddings, SQLite for metadata, local filesystem for project managemen (001-local-doc-bro)
- Python 3.13 (as clarified) + uv/uvx tool, Click (CLI), existing DocBro dependencies (003-uv-command-install)
- Local filesystem for config/data, GitHub releases for distribution (003-uv-command-install)

## Project Structure
```
local-doc-bro/
├── src/
│   ├── models/         # Data models (Project, Page, CrawlSession, QueryResult)
│   ├── services/       # Core services
│   │   ├── database.py    # SQLite database operations
│   │   ├── vector_store.py # Qdrant vector operations
│   │   ├── embeddings.py  # Ollama embedding service
│   │   ├── rag.py        # RAG search implementation
│   │   ├── crawler.py    # Web crawler service
│   │   └── mcp_server.py # MCP/FastAPI server
│   ├── cli/
│   │   └── main.py    # Click CLI implementation
│   └── lib/
│       ├── config.py   # Configuration management
│       ├── logging.py  # Structured logging
│       └── docker_utils.py # Docker helpers
├── tests/
│   ├── contract/      # Contract tests (TDD)
│   └── integration/   # Integration tests
├── docker/
│   └── docker-compose.yml # Qdrant + Redis
├── docbro            # CLI entry point
├── setup.sh          # Setup script
├── run.sh           # Quick start script
└── pyproject.toml    # Python dependencies
```

## Commands

### Setup and Installation
```bash
# Initial setup
./setup.sh

# Quick start services
./run.sh

# Install Python dependencies
pip install -e .
```

### Docker Services
```bash
# Start Qdrant and Redis
docker-compose -f docker/docker-compose.yml up -d

# Check service health
docker-compose -f docker/docker-compose.yml ps

# View logs
docker-compose -f docker/docker-compose.yml logs -f
```

### CLI Usage
```bash
# Create a project
./docbro create <name> --url <docs-url> --depth 2

# Crawl documentation
./docbro crawl <name> --max-pages 100 --rate-limit 2.0

# Search documentation
./docbro search "query" --project <name> --limit 10

# List projects
./docbro list --status ready

# Check system status
./docbro status

# Start MCP server
./docbro serve --port 8000

# Remove project
./docbro remove <name> --confirm
```

### Testing
```bash
# Run all tests
pytest tests/

# Run contract tests
pytest tests/contract/ -v

# Run specific test
pytest tests/contract/test_cli_list.py -v

# Run with coverage
pytest --cov=src tests/
```

### Linting and Formatting
```bash
# Check code style
ruff check src/ tests/

# Format code
ruff format src/ tests/

# Type checking (if mypy installed)
mypy src/
```

## Code Style
- **Python**: Follow PEP 8 with 100 char line limit
- **Async/Await**: Use for all I/O operations
- **Type Hints**: Use throughout for better IDE support
- **Docstrings**: Google style for all public functions
- **Error Handling**: Proper exception hierarchy with custom errors
- **Logging**: Structured JSON logging with component tracking

## Configuration
Configuration is managed via environment variables and `DocBroConfig` class:

```python
# Environment variables
DOCBRO_DATABASE_PATH=./data/docbro.db
DOCBRO_QDRANT_URL=http://localhost:6333
DOCBRO_REDIS_URL=redis://localhost:6379
DOCBRO_OLLAMA_URL=http://localhost:11434
DOCBRO_EMBEDDING_MODEL=mxbai-embed-large
DOCBRO_LOG_LEVEL=INFO
```

## Testing Strategy
- **TDD Approach**: All tests written first, then implementation
- **Contract Tests**: API and CLI interface contracts
- **Integration Tests**: End-to-end workflows
- **Mocking**: External services mocked for unit tests
- **Async Testing**: pytest-asyncio for async code

## Recent Changes
- 003-uv-command-install: Added Python 3.13 (as clarified) + uv/uvx tool, Click (CLI), existing DocBro dependencies
- 001-local-doc-bro: Added Python 3.11+ + Qdrant (vector database), Ollama (embeddings), MCP protocol server, Click (CLI), BeautifulSoup4 (web crawling)
- Implemented complete core functionality (90% feature complete)

## Next Steps (Remaining 10%)
- [ ] Add more sophisticated crawling strategies
- [ ] Implement incremental crawl updates
- [ ] Add export functionality (JSON, Markdown)
- [ ] Enhance MCP server with more endpoints
- [ ] Add authentication for production MCP
- [ ] Create web UI (optional)
- [ ] Add more embedding model options
- [ ] Implement crawl scheduling

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->
