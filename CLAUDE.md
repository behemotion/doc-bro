# DocBro Development Guidelines

**Last Updated:** 2025-01-25

## Project Overview
DocBro is a documentation crawler and search tool with RAG (Retrieval-Augmented Generation) capabilities and MCP (Model Context Protocol) server integration for coding agents.

## Implementation Status
✅ **100% Complete** - Full UV/UVX installation feature implemented with TDD methodology

### Completed Components
- ✅ **UV/UVX Installation** - Single command installation with interactive setup wizard
- ✅ **Data Models** - Pydantic v2 with validation (4 new installation models)
- ✅ **Configuration Management** - XDG-compliant directories with atomic operations
- ✅ **Service Detection** - Async detection for Docker, Ollama, Redis, Qdrant
- ✅ **Setup Wizard** - Interactive CLI setup with Rich interface
- ✅ **Enhanced CLI** - New commands: setup, version --detailed, status --install
- ✅ **Database Service** - Async SQLite with full CRUD
- ✅ **Vector Store Service** - Qdrant integration
- ✅ **Embedding Service** - Ollama integration
- ✅ **RAG Search Service** - Multiple strategies
- ✅ **Documentation Crawler** - Rate limiting, robots.txt
- ✅ **MCP Server** - FastAPI with WebSocket
- ✅ **Docker Configuration** - Qdrant + Redis services
- ✅ **Comprehensive Testing** - 15+ tests following TDD approach

## Active Technologies
- **Python 3.13+** - Required for UVX installation
- **UV/UVX** - Package installer and runner
- **Qdrant 1.13.0** - Vector database (Docker)
- **Redis 7.2** - Cache and queue (Docker)
- **Ollama** - Local embeddings (mxbai-embed-large, nomic-embed-text)
- **SQLite** - Metadata storage (local)
- **FastAPI** - MCP server implementation
- **Click + Rich** - CLI with beautiful output and interactive setup
- **httpx + BeautifulSoup4** - Web crawling
- **pytest 8.x** - Test framework with async support
- **platformdirs** - XDG Base Directory specification
- **packaging** - Version validation
- Python 3.13+ (as specified in pyproject.toml) + Hatchling (build system), UV/UVX (installer), Click, Rich, Pydantic (004-however-there-is)
- N/A (packaging/configuration issue) (004-however-there-is)

## Project Structure
```
local-doc-bro/
├── src/
│   ├── models/         # Data models
│   │   ├── project.py      # Project, Page, CrawlSession models
│   │   ├── query_result.py # Search result models
│   │   └── installation.py # Installation context, service status, setup wizard
│   ├── services/       # Core services
│   │   ├── database.py     # SQLite database operations
│   │   ├── vector_store.py # Qdrant vector operations
│   │   ├── embeddings.py   # Ollama embedding service
│   │   ├── rag.py         # RAG search implementation
│   │   ├── crawler.py     # Web crawler service
│   │   ├── mcp_server.py  # MCP/FastAPI server
│   │   ├── config.py      # Configuration management (NEW)
│   │   ├── detection.py   # Service detection (NEW)
│   │   └── setup.py       # Setup wizard service (NEW)
│   ├── cli/
│   │   └── main.py        # Click CLI implementation (ENHANCED)
│   └── lib/
│       ├── config.py      # Configuration management
│       ├── logging.py     # Structured logging
│       └── docker_utils.py # Docker helpers
├── tests/
│   ├── unit/              # Unit tests for models
│   ├── contract/          # Contract tests (CLI interface)
│   └── integration/       # Integration tests (end-to-end)
├── .github/workflows/     # GitHub Actions (NEW)
│   └── release.yml        # Automated releases
├── docker/
│   └── docker-compose.yml # Qdrant + Redis
├── docbro                # CLI entry point
├── setup.sh              # Development setup script
├── run.sh               # Quick start script
└── pyproject.toml        # Python dependencies (UPDATED)
```

## Installation

### Primary Method: UVX (Recommended)
```bash
# Install DocBro globally
uvx install git+https://github.com/yourusername/local-doc-bro

# Run interactive setup wizard
docbro setup

# Check installation status
docbro status --install
```

### Development Setup
```bash
# Clone repository
git clone https://github.com/yourusername/local-doc-bro.git
cd local-doc-bro

# Run automated setup
./setup.sh

# Quick start for development
./run.sh
```

## Commands

### Installation & Setup Commands
```bash
# Interactive setup wizard
docbro setup

# Check installation status
docbro status --install

# Detailed version information
docbro version --detailed

# General system status
docbro status
```

### Core Documentation Commands
```bash
# Create a project
docbro create <name> --url <docs-url> --depth 2

# Crawl documentation
docbro crawl <name> --max-pages 100 --rate-limit 2.0

# Search documentation
docbro search "query" --project <name> --limit 10

# List projects
docbro list --status ready

# Remove project
docbro remove <name> --confirm
```

### MCP Server Commands
```bash
# Start MCP server for coding agents
docbro serve --port 8000

# Start with custom configuration
docbro serve --host 127.0.0.1 --port 8765
```

### Docker Services (Development)
```bash
# Start Qdrant and Redis
docker-compose -f docker/docker-compose.yml up -d

# Check service health
docker-compose -f docker/docker-compose.yml ps

# View logs
docker-compose -f docker/docker-compose.yml logs -f
```

### Testing
```bash
# Run all tests
pytest tests/ -v

# Run specific test categories
pytest tests/unit/ -v          # Unit tests
pytest tests/contract/ -v      # Contract tests
pytest tests/integration/ -v   # Integration tests

# Run with coverage
pytest --cov=src tests/
```

### Code Quality
```bash
# Format code
ruff format src/ tests/

# Check linting
ruff check src/ tests/

# Type checking (if mypy installed)
mypy src/
```

## Configuration

### XDG-Compliant Directories
DocBro follows XDG Base Directory specification:
- **Config**: `~/.config/docbro/` - installation.json, services.json
- **Data**: `~/.local/share/docbro/` - projects, databases
- **Cache**: `~/.cache/docbro/` - temporary files

### Environment Variables
```bash
# Service URLs
DOCBRO_QDRANT_URL=http://localhost:6333
DOCBRO_REDIS_URL=redis://localhost:6379
DOCBRO_OLLAMA_URL=http://localhost:11434

# Configuration
DOCBRO_DATABASE_PATH=./data/docbro.db
DOCBRO_EMBEDDING_MODEL=mxbai-embed-large
DOCBRO_LOG_LEVEL=INFO
```

## Code Style
- **Python**: Follow PEP 8 with 100 char line limit
- **Async/Await**: Use for all I/O operations
- **Type Hints**: Use throughout for better IDE support
- **Docstrings**: Google style for all public functions
- **Error Handling**: Proper exception hierarchy with custom errors
- **Logging**: Structured JSON logging with component tracking
- **Field Validation**: Pydantic v2 field validators for data integrity

## Testing Strategy
- **TDD Approach**: All features developed test-first
- **Comprehensive Coverage**: 15+ tests across unit/contract/integration
- **Model Testing**: Pydantic validation and serialization
- **Service Testing**: Async service detection and configuration
- **CLI Testing**: Command interfaces and error handling
- **Integration Testing**: End-to-end installation workflows

## Recent Implementation (003-uv-command-install)
- ✅ **UVX Installation** - Single command global installation
- ✅ **Interactive Setup Wizard** - Guided service detection and configuration
- ✅ **Enhanced CLI** - New setup, version, and status commands
- ✅ **Configuration Management** - XDG-compliant with atomic operations
- ✅ **Service Detection** - Async detection for all external services
- ✅ **Installation Models** - 4 new Pydantic models with validation
- ✅ **Comprehensive Testing** - TDD approach with full test coverage
- ✅ **Documentation Updates** - README and CLAUDE.md updated

## Architecture Benefits
- **Zero-Configuration Installation** - Works out of the box after `uvx install`
- **Cross-Platform** - XDG specification ensures proper directory usage
- **Robust Error Handling** - Comprehensive validation and user-friendly messages
- **Extensible** - Service detection easily extended for new dependencies
- **Maintainable** - Clear separation of concerns with service-oriented architecture

## Next Steps (Future Enhancements)
- [ ] Add more sophisticated crawling strategies
- [ ] Implement incremental crawl updates
- [ ] Add export functionality (JSON, Markdown)
- [ ] Enhanced MCP server with more endpoints
- [ ] Web UI interface (optional)
- [ ] More embedding model options
- [ ] Crawl scheduling and automation

<!-- MANUAL ADDITIONS START -->
<!-- MANUAL ADDITIONS END -->

# important-instruction-reminders
Do what has been asked; nothing more, nothing less.
NEVER create files unless they're absolutely necessary for achieving your goal.
ALWAYS prefer editing an existing file to creating a new one.
NEVER proactively create documentation files (*.md) or README files. Only create documentation files if explicitly requested by the User.
