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

1. **Docker Services** (Qdrant + Redis):
```bash
docker-compose -f docker/docker-compose.yml up -d
```

2. **Ollama** (for embeddings):
```bash
# Install Ollama if not already installed
curl -fsSL https://ollama.com/install.sh | sh

# Pull the embedding model
ollama pull mxbai-embed-large
```

### Installation

```bash
# Clone the repository
git clone https://github.com/yourusername/docbro
cd docbro

# Quick setup (installs dependencies and starts services)
./setup.sh

# Or manual installation
pip install -e .
```

### Basic Usage

```bash
# Create a new project
docbro create python-docs --url https://docs.python.org/3/ --depth 2

# Crawl documentation
docbro crawl python-docs --max-pages 100 --rate-limit 2.0

# Search documentation
docbro search "async function" --project python-docs --limit 10

# List projects
docbro list

# Check system status
docbro status

# Start MCP server for coding agents
docbro serve --port 8765
```

## CLI Commands

### Main Commands

| Command | Description | Key Options |
|---------|-------------|------------|
| `docbro create` | Create a new documentation project | `-u/--url` (required): Source URL<br>`-d/--depth`: Max crawl depth<br>`-m/--model`: Embedding model |
| `docbro crawl` | Start crawling an existing project | `-m/--max-pages`: Page limit<br>`-r/--rate-limit`: Requests/second |
| `docbro search` | Search documentation in projects | `-p/--project`: Target project<br>`-l/--limit`: Max results<br>`--strategy`: Search strategy |
| `docbro list` | List all documentation projects | No additional options |
| `docbro remove` | Remove a project and all its data | `--confirm`: Skip confirmation |
| `docbro serve` | Start MCP server for agent integration | `--host`: Server host<br>`--port`: Server port |
| `docbro status` | Show system status | No additional options |

### Global Options
- `--version`: Show version and exit
- `--config-file PATH`: Custom configuration file
- `-v/--verbose`: Enable verbose output
- `--help`: Show help message

## MCP Server API

The MCP (Model Context Protocol) server enables integration with coding agents:

### REST API Endpoints

| Method | Endpoint | Description | Authentication |
|--------|----------|-------------|----------------|
| GET | `/health` | Health check endpoint | No |
| POST | `/mcp/connect` | Establish MCP connection | Yes |
| GET | `/mcp/projects` | List available documentation projects | Yes |
| POST | `/mcp/search` | Search documentation across projects | Yes |
| POST | `/mcp/projects/refresh` | Refresh/re-crawl a project | Yes |

### WebSocket Endpoint

- **WS** `/mcp/ws/{session_id}`: Real-time bidirectional communication
  - Supports `ping`/`pong` keep-alive
  - Real-time search capabilities
  - Streaming updates for long operations

### Authentication

- Bearer token authentication: `Authorization: Bearer <token>`
- Configure token via `DOCBRO_MCP_AUTH_TOKEN` environment variable

## Architecture

- **Language**: Python 3.13.5
- **Vector DB**: Qdrant 1.13.0 (Docker)
- **Queue**: Redis 7.2 (Docker)
- **Embeddings**: Ollama (Local) - mxbai-embed-large
- **Web Framework**: FastAPI + WebSocket support
- **CLI**: Click + Rich for beautiful terminal output

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