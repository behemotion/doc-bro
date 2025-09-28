# DocBro Dependencies

**Last Updated:** 2025-09-27

This document lists all dependencies used by DocBro, including version requirements and purposes.

## Core Runtime Dependencies

### Required Dependencies
These packages are required for DocBro to function:

| Package | Version | Purpose |
|---------|---------|---------|
| `click` | ≥8.1.0 | Command-line interface framework |
| `rich` | ≥14.1.0 | Beautiful terminal output and formatting |
| `qdrant-client` | ≥1.7.0 | Vector database client for document search |
| `fastapi` | ≥0.117.0 | Web framework for MCP server |
| `uvicorn` | ≥0.20.0 | ASGI server for FastAPI |
| `pydantic` | ≥2.11.0 | Data validation and settings management |
| `pydantic-settings` | ≥2.0.0 | Configuration management |
| `aiosqlite` | ≥0.19.0 | Async SQLite interface for metadata storage |
| `httpx` | ≥0.24.0 | Async HTTP client for web crawling |
| `beautifulsoup4` | ≥4.13.0 | HTML parsing for documentation extraction |
| `platformdirs` | ≥3.0.0 | Cross-platform directory management |
| `packaging` | ≥23.0 | Version parsing and package management |
| `docker` | ≥6.0.0 | Docker API client for service management |
| `psutil` | ≥5.9.0 | System and process utilities |
| `pyyaml` | ≥6.0.0 | YAML configuration file parsing |
| `sqlite-vec` | ≥0.1.6 | **Vector search SQLite extension** |

### Vector Storage Options

DocBro supports two vector storage backends:

#### SQLite-vec (Local)
- **Package**: `sqlite-vec` ≥0.1.6
- **Type**: Local vector database
- **Benefits**: No external dependencies, embedded storage
- **Requirements**: Python with SQLite extension support
- **Use case**: Single-user, local development

#### Qdrant (Scalable)
- **Package**: `qdrant-client` ≥1.7.0
- **Type**: External vector database service
- **Benefits**: Scalable, production-ready, clustering support
- **Requirements**: Docker or external Qdrant service
- **Use case**: Production deployments, team usage

## Development Dependencies

### Testing Framework
| Package | Version | Purpose |
|---------|---------|---------|
| `pytest` | ≥8.4.0 | Test framework |
| `pytest-asyncio` | ≥1.2.0 | Async test support |
| `pytest-mock` | ≥3.14.0 | Mocking utilities |
| `pytest-env` | ≥1.1.0 | Environment variable management |
| `pytest-timeout` | ≥2.3.0 | Test timeout handling |
| `pytest-cov` | ≥4.0.0 | Code coverage reporting |
| `pytest-benchmark` | ≥4.0.0 | Performance testing |

### Code Quality Tools
| Package | Version | Purpose |
|---------|---------|---------|
| `black` | ≥25.9.0 | Code formatting |
| `ruff` | ≥0.13.0 | Linting and code analysis |
| `mypy` | ≥1.18.0 | Static type checking |
| `types-beautifulsoup4` | ≥4.12.0 | Type stubs for BeautifulSoup |
| `freezegun` | ≥1.2.0 | Time mocking for tests |

## External Service Dependencies

These services are optional but recommended for full functionality:

### Required for Vector Search
- **Qdrant**: Vector database service
  - **Version**: 1.15.1+
  - **Installation**: `docker run -p 6333:6333 qdrant/qdrant`
  - **Alternative**: Use SQLite-vec for local development

### Required for Embeddings
- **Ollama**: Local embeddings server
  - **Version**: Latest
  - **Installation**: [ollama.com](https://ollama.com/)
  - **Model**: `mxbai-embed-large` (recommended)

### Required for Service Management
- **Docker**: Container runtime
  - **Version**: 20.10+
  - **Purpose**: Running Qdrant and other services
  - **Installation**: [docker.com](https://docker.com/)

## Python Version Requirements

- **Minimum**: Python 3.13+
- **Recommended**: Python 3.13.6+ (for SQLite extension support)
- **UV**: Latest version for package management

### Python Feature Requirements
- **Async/await support**: Core async functionality
- **SQLite extension loading**: Required for SQLite-vec
- **Type hints**: Development and runtime type checking

## Installation Methods

### UV (Recommended)
```bash
# Global installation
uv tool install git+https://github.com/behemotion/doc-bro
docbro --help

# With specific Python version (install then run)
uv tool install --python 3.13 git+https://github.com/behemotion/doc-bro
docbro init
```

### Development Setup
```bash
# Clone repository
git clone https://github.com/behemotion/doc-bro.git
cd doc-bro

# Install dependencies
uv sync --extra dev

# Run tests
uv run pytest tests/ -v
```

## Recent Updates

### sqlite-vec 0.1.6 (November 20, 2024)
- Latest stable release
- Improved performance and stability
- Enhanced compatibility with SQLite 3.49+
- Updated from previous requirement of ≥0.1.3

### Pre-release Versions Available
- `sqlite-vec` 0.1.7a2 (January 10, 2025) - Pre-release
- `sqlite-vec` 0.1.7a1 (January 10, 2025) - Pre-release

## Troubleshooting Dependencies

### SQLite Extension Issues
If you encounter SQLite extension loading errors:
1. Use UV-managed Python 3.13.6+ which has extension support
2. Or switch to Qdrant: `docbro init --vector-store qdrant`

### Missing Dependencies
```bash
# Check system requirements
docbro --health

# Reinstall with latest dependencies
uv sync --upgrade
```

### Version Conflicts
```bash
# Check current versions
uv pip list | grep -E "(sqlite-vec|qdrant|ollama)"

# Force update specific package
uv pip install --upgrade sqlite-vec
```