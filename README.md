# DocBro - Local Documentation Crawler & Search

A powerful CLI tool that crawls documentation websites, creates vector databases, and provides RAG-powered search capabilities with MCP server integration for coding agents.

## 🚀 Features

- **Smart Web Crawling**: Configurable documentation crawler with rate limiting and robots.txt respect
- **Vector Search**: Qdrant-powered semantic search with multiple RAG strategies
- **Local Embeddings**: Ollama integration for privacy-focused, offline operation
- **MCP Server**: Model Context Protocol server for Claude, Cursor, and other AI coding assistants
- **Project Management**: Organize multiple documentation sources
- **Rich CLI**: Beautiful terminal interface with progress bars and formatted output
- **Docker Integration**: Pre-configured services for immediate use

## 📋 Prerequisites

### Required Services

1. **Docker & Docker Compose** - For Qdrant and Redis
2. **Python 3.13+** - Core runtime (required for UVX installation)
3. **Ollama** - For local embeddings
4. **UV** - Package installer (for UVX method)

### Quick Prerequisites Check

```bash
# Check Docker
docker --version
docker-compose --version

# Check Python
python3 --version

# Check/Install UV (for UVX installation)
uv --version || curl -LsSf https://astral.sh/uv/install.sh | sh

# Check/Install Ollama
ollama --version || curl -fsSL https://ollama.com/install.sh | sh
```

## 🛠️ Installation

### Option 1: UVX Installation (Recommended)

Install DocBro globally with a single command using [UV](https://docs.astral.sh/uv/):

```bash
# Install with uvx (one command installation)
uvx install git+https://github.com/yourusername/local-doc-bro

# Run interactive setup wizard
docbro setup

# Check installation status
docbro status --install

# Get detailed version info
docbro version --detailed
```

**What the setup wizard does:**
- ✅ Detects and validates Python 3.13+ installation
- ✅ Checks for external services (Docker, Ollama, Redis, Qdrant)
- ✅ Provides installation guidance for missing services
- ✅ Creates XDG-compliant configuration directories
- ✅ Sets up installation metadata and tracking

### Option 2: Development/Manual Setup

```bash
# Clone repository
git clone https://github.com/yourusername/local-doc-bro.git
cd local-doc-bro

# Run automated setup
./setup.sh

# This will:
# - Install Python dependencies
# - Start Docker services (Qdrant + Redis)
# - Pull Ollama embedding models
# - Verify installation
```

### Option 3: Quick Start (Development)

```bash
# All-in-one command for development
./run.sh
```

## 🎯 Quick Start Guide

### 1. Create a Documentation Project

```bash
# Create project for Python docs
./docbro create python-docs --url https://docs.python.org/3/ --depth 2

# Create project with custom settings
./docbro create fastapi \
  --url https://fastapi.tiangolo.com \
  --depth 3 \
  --model nomic-embed-text
```

### 2. Crawl Documentation

```bash
# Basic crawl
./docbro crawl python-docs

# Crawl with limits
./docbro crawl python-docs \
  --max-pages 100 \
  --rate-limit 2.0 \
  --respect-robots
```

### 3. Search Documentation

```bash
# Simple search
./docbro search "async await" --project python-docs

# Advanced search with options
./docbro search "error handling" \
  --project fastapi \
  --limit 10 \
  --strategy hybrid
```

### 4. Start MCP Server (for AI Agents)

```bash
# Start MCP server
./docbro serve --port 8000

# For Claude Desktop integration
./docbro serve --port 8765 --host 127.0.0.1
```

## 📚 Command Reference

### Core Commands

| Command | Description | Example |
|---------|-------------|---------|
| `create` | Create new documentation project | `./docbro create <name> --url <docs-url>` |
| `crawl` | Crawl documentation pages | `./docbro crawl <name> --max-pages 100` |
| `search` | Search across documentation | `./docbro search "query" --project <name>` |
| `list` | List all projects | `./docbro list --status ready` |
| `status` | Check system health | `./docbro status` |
| `serve` | Start MCP server | `./docbro serve --port 8000` |
| `remove` | Delete a project | `./docbro remove <name> --confirm` |

### Command Options

#### `create` Options
- `--url, -u`: Documentation base URL (required)
- `--depth, -d`: Maximum crawl depth (default: 2)
- `--model, -m`: Embedding model (default: mxbai-embed-large)

#### `crawl` Options
- `--max-pages, -m`: Maximum pages to crawl (default: 100)
- `--rate-limit, -r`: Requests per second (default: 2.0)
- `--respect-robots`: Honor robots.txt (default: true)

#### `search` Options
- `--project, -p`: Target project name
- `--limit, -l`: Maximum results (default: 10)
- `--strategy, -s`: Search strategy (vector|keyword|hybrid)

## 🔧 Configuration

### Environment Variables

```bash
# Database & Storage
DOCBRO_DATABASE_PATH=./data/docbro.db

# Vector Database
DOCBRO_QDRANT_URL=http://localhost:6333

# Cache & Queue
DOCBRO_REDIS_URL=redis://localhost:6379

# Embeddings
DOCBRO_OLLAMA_URL=http://localhost:11434
DOCBRO_EMBEDDING_MODEL=mxbai-embed-large

# Logging
DOCBRO_LOG_LEVEL=INFO

# MCP Server
DOCBRO_MCP_AUTH_TOKEN=your-secret-token
```

### Configuration File

Create `~/.docbro/config.yaml`:

```yaml
database:
  path: ./data/docbro.db

services:
  qdrant:
    url: http://localhost:6333
  redis:
    url: redis://localhost:6379
  ollama:
    url: http://localhost:11434
    model: mxbai-embed-large

crawler:
  default_max_pages: 100
  default_rate_limit: 2.0
  respect_robots: true

search:
  default_limit: 10
  default_strategy: hybrid
```

## 🤖 MCP Server Integration

### For Claude Desktop

Add to Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json`):

```json
{
  "mcpServers": {
    "docbro": {
      "command": "/path/to/docbro",
      "args": ["serve", "--port", "8765"],
      "env": {
        "DOCBRO_MCP_AUTH_TOKEN": "your-token"
      }
    }
  }
}
```

### API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Health check |
| GET | `/mcp/projects` | List projects |
| POST | `/mcp/search` | Search documentation |
| WS | `/mcp/ws/{session_id}` | WebSocket connection |

## 🏗️ Architecture

### Technology Stack

- **Core**: Python 3.11+ with async/await
- **Vector DB**: Qdrant 1.13.0
- **Cache**: Redis 7.2
- **Embeddings**: Ollama (mxbai-embed-large, nomic-embed-text)
- **Database**: SQLite (metadata)
- **Web Framework**: FastAPI + WebSocket
- **CLI**: Click + Rich

### Project Structure

```
local-doc-bro/
├── src/
│   ├── models/         # Pydantic data models
│   ├── services/       # Core services
│   │   ├── database.py     # SQLite operations
│   │   ├── vector_store.py # Qdrant integration
│   │   ├── embeddings.py   # Ollama service
│   │   ├── rag.py         # RAG search
│   │   ├── crawler.py     # Web crawler
│   │   └── mcp_server.py  # MCP/FastAPI
│   ├── cli/           # CLI implementation
│   └── lib/           # Utilities
├── tests/             # Test suite
├── docker/            # Docker configs
├── docbro            # CLI entry point
└── setup.sh          # Setup script
```

## 🧪 Development

### Running Tests

```bash
# All tests
pytest tests/

# Specific test file
pytest tests/contract/test_cli_create.py -v

# With coverage
pytest --cov=src tests/
```

### Code Quality

```bash
# Formatting
ruff format src/ tests/

# Linting
ruff check src/ tests/

# Type checking
mypy src/
```

## 📊 Implementation Status

- ✅ **Core Functionality** (90% complete)
  - ✅ Data models with validation
  - ✅ Async database operations
  - ✅ Vector store integration
  - ✅ Embedding service
  - ✅ RAG search (3 strategies)
  - ✅ Web crawler with rate limiting
  - ✅ MCP server implementation
  - ✅ Rich CLI interface
  - ✅ Docker configuration

- 🚧 **Planned Features** (10% remaining)
  - [ ] Incremental crawl updates
  - [ ] Export functionality (JSON/Markdown)
  - [ ] Advanced crawling strategies
  - [ ] Crawl scheduling
  - [ ] Web UI (optional)

## 🐛 Troubleshooting

### Common Issues

**Services not starting:**
```bash
# Check Docker services
docker-compose -f docker/docker-compose.yml ps
docker-compose -f docker/docker-compose.yml logs

# Restart services
docker-compose -f docker/docker-compose.yml restart
```

**Ollama connection error:**
```bash
# Check Ollama service
ollama list
ollama serve  # If not running

# Pull model if missing
ollama pull mxbai-embed-large
```

**Database errors:**
```bash
# Reset database
rm -rf data/docbro.db
./docbro status  # Will recreate
```

## 📝 License

MIT License - See [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📮 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/local-doc-bro/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/local-doc-bro/discussions)