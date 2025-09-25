# DocBro - Documentation Web Crawler

A powerful CLI tool that crawls documentation websites, creates vector databases, and provides RAG-powered search capabilities for developers and coding agents.

## Features

- **Smart Crawling**: Web crawler with configurable depth for documentation sites
- **Vector Database**: Qdrant integration for efficient semantic search
- **RAG Search**: Advanced retrieval-augmented generation with multiple strategies
- **MCP Server**: Connect coding agents like Claude Code via Model Context Protocol
- **Project Management**: Organize multiple documentation projects
- **Local-First**: Fully local operation with Ollama embeddings
- **Docker Integration**: Containerized data services with local ML models

## Quick Start

### Prerequisites

1. **Data Services (Docker)**:
```bash
cd docker && docker-compose up -d
```

2. **Ollama (Local)**:
```bash
./scripts/setup-ollama.sh
```

### Installation

```bash
# Using UV/UVX (recommended)
uvx install docbro

# From source
git clone https://github.com/yourusername/docbro
cd docbro
pip install -e .
```

### Basic Usage

```bash
# Crawl documentation
docbro crawl --url https://docs.python.org/3/ --name python-docs --depth 2

# Search documentation
docbro query "async function" --project python-docs

# List projects
docbro list

# Start MCP server for coding agents
docbro serve --port 8765
```

## Architecture

- **Language**: Python 3.13.7
- **Vector DB**: Qdrant 1.13.0 (Docker)
- **Queue**: Redis 7.2 (Docker)
- **Embeddings**: Ollama (Local)
- **Web Framework**: FastMCP 2.0 + FastAPI
- **CLI**: Click + Rich

## Development

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Code formatting
black src/ tests/
ruff check src/ tests/

# Type checking
mypy src/
```

## License

MIT License - see LICENSE file for details.

## Contributing

See CONTRIBUTING.md for development setup and guidelines.