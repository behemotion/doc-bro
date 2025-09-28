```
██████╗  ██████╗  ██████╗██████╗ ██████╗  ██████╗
██╔══██╗██╔═══██╗██╔════╝██╔══██╗██╔══██╗██╔═══██╗
██║  ██║██║   ██║██║     ██████╔╝██████╔╝██║   ██║
██║  ██║██║   ██║██║     ██╔══██╗██╔══██╗██║   ██║
██████╔╝╚██████╔╝╚██████╗██████╔╝██║  ██║╚██████╔╝
╚═════╝  ╚═════╝  ╚═════╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝
```

# DocBro - Universal Documentation Intelligence Platform

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![UV Tool](https://img.shields.io/badge/UV-0.8+-green.svg)](https://docs.astral.sh/uv/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A next-generation CLI tool that transforms any documentation site into a searchable knowledge base with RAG-powered semantic search, local or cloud vector storage, and seamless AI assistant integration via MCP.

## 🚀 Quick Start

### One-Command Installation:
```bash
# Install globally with UV (< 30 seconds)
uv tool install git+https://github.com/behemotion/doc-bro

# Run interactive setup with universal arrow navigation
docbro setup
```

✨ **That's it!** The intelligent setup wizard will guide you through everything.

## ✨ Key Features

### 🎯 Core Capabilities
- **30-Second Setup**: Single `uvx install` command with automatic configuration
- **Dual Vector Storage**: Choose between SQLite-vec (local, zero deps) or Qdrant (scalable)
- **Universal Navigation**: Consistent arrow keys, vim keys (j/k), and number selection across all interfaces
- **Smart Crawling**: Intelligent rate limiting, robots.txt compliance, asset filtering, depth control
- **RAG-Powered Search**: Semantic search with context-aware results using local embeddings
- **MCP Integration**: Native support for Claude Code, Claude Desktop, Cursor, and other AI assistants
- **Rich Terminal UI**: Beautiful progress bars, interactive menus, and formatted outputs

### 🔄 Setup & Configuration
- **Unified Setup Command**: All operations under `docbro setup` with flag-based routing
- **Interactive Menu**: Rich-based UI for guided setup when no flags provided
- **Auto-Detection**: Async service detection for Docker, Qdrant, Ollama, Python, UV, Git
- **Graceful Fallbacks**: Automatic switching between SQLite-vec and Qdrant based on availability
- **Legacy Compatibility**: Backward compatible aliases with deprecation warnings

## 📋 System Requirements

### Minimum Requirements
- **Python 3.13+** - Core runtime (verified during setup)
- **UV/UVX 0.8+** - Modern Python package manager ([install](https://docs.astral.sh/uv/))
- **4GB RAM** - For embeddings and vector operations
- **2GB Disk** - For local vector storage and cache

### Optional Services (Auto-Detected)
- **SQLite-vec** - Local vector storage (installed automatically, no external deps)
- **Docker** - For Qdrant scalable vector database (optional)
- **Ollama** - Local embeddings with mxbai-embed-large ([install](https://ollama.com/))
- **Qdrant** - Production vector database (requires Docker)

## 🛠️ Installation

### Production Installation (Recommended)

```bash
# Single command installation with UV
uv tool install git+https://github.com/behemotion/doc-bro

# Interactive setup with arrow navigation
docbro setup

# Quick setup with auto-configuration
docbro setup --init --auto --vector-store sqlite_vec
```

#### What Setup Does:
- ✅ **System Validation**: Python 3.13+, memory, disk space checks
- ✅ **Vector Store Selection**: Interactive choice between SQLite-vec (local) or Qdrant (scalable)
- ✅ **Service Detection**: Async detection of Docker, Qdrant, Ollama availability
- ✅ **XDG Directories**: Creates `~/.config/docbro/`, `~/.local/share/docbro/`, `~/.cache/docbro/`
- ✅ **Configuration**: Persists settings with intelligent defaults

### Development Installation

```bash
# Clone repository
git clone https://github.com/behemotion/doc-bro.git
cd doc-bro

# Install with UV in editable mode
uv pip install -e .

# Run comprehensive test suite
pytest tests/ -v                    # All 200+ tests
pytest tests/performance/ -v        # Performance validation (< 30s)
pytest tests/contract/ -v           # API contracts
pytest --cov=src tests/             # Coverage report

# Verify package integrity (critical after model changes)
./.verify-package.sh
```

## 📚 Command Reference

### Core Commands

| Command | Description | Example |
|---------|-------------|---------|
| `setup` | Unified setup command (interactive or flag-based) | `docbro setup --init --auto` |
| `create` | Create new documentation project | `docbro create python -u https://docs.python.org/3/ --depth 3` |
| `crawl` | Crawl and index documentation | `docbro crawl python --max-pages 100 --update` |
| `list` | List all projects with status | `docbro list --status ready --limit 10` |
| `serve` | Start MCP server for AI assistants | `docbro serve --host 0.0.0.0 --port 9382` |
| `remove` | Delete a project and its data | `docbro remove python --confirm` |

### Setup Operations (Unified Command)

```bash
docbro setup                           # Interactive menu with arrow navigation
docbro setup --init --auto             # Quick initialization
docbro setup --init --vector-store sqlite_vec  # Specify vector store
docbro setup --uninstall --force       # Force uninstall
docbro setup --reset --preserve-data   # Reset keeping projects
```

### System Commands

```bash
docbro system-check                    # Validate all requirements
docbro services list                   # Check service status
docbro services setup                  # Configure external services
docbro --health                        # Quick health check
docbro --version                       # Version information
```

## 🎯 Usage Examples

### 1. Create Documentation Projects
```bash
# Python documentation
docbro create python -u https://docs.python.org/3/ --depth 3 --model mxbai-embed-large

# FastAPI documentation
docbro create fastapi -u https://fastapi.tiangolo.com/ --depth 2

# URLs with special characters MUST be quoted
docbro create uv-docs -u "https://github.com/astral-sh/uv?tab=readme-ov-file" --depth 2
```

**⚠️ Important:** Always quote URLs containing special characters (?, &, *, [, ]).

### 2. Crawl & Index Documentation

```bash
# Initial crawl with progress display
docbro crawl python --max-pages 100 --rate-limit 1.0

# Update existing project
docbro crawl python --update --max-pages 50

# Batch crawl multiple projects
docbro crawl python fastapi uv-docs --max-pages 100
```

### 3. Manage Projects

```bash
# List all projects with status
docbro list --status ready --limit 10

# Remove project and all data
docbro remove python --confirm

# View detailed project info
docbro list --verbose
```

### 4. Start MCP Server for AI Assistants

```bash
# Start in background (default)
docbro serve --host 127.0.0.1 --port 9382

# Start in foreground for debugging
docbro serve --foreground --port 9382

# Custom configuration
docbro serve --host 0.0.0.0 --port 9383
```

## 🤖 MCP Server Integration

DocBro provides a Model Context Protocol (MCP) server that allows AI coding assistants like Claude Code, Claude Desktop, and Cursor to search your crawled documentation directly.

### For Claude Code

Add DocBro to your MCP configuration file at `~/.config/mcp/config.json`:

```json
{
  "mcpServers": {
    "docbro": {
      "command": "docbro",
      "args": ["serve", "--port", "9382", "--host", "127.0.0.1"],
      "env": {
        "DOCBRO_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

### For Claude Desktop

Add to your Claude Desktop config (`~/Library/Application Support/Claude/claude_desktop_config.json` on macOS):

```json
{
  "mcpServers": {
    "docbro": {
      "command": "docbro",
      "args": ["serve", "--port", "9382"]
    }
  }
}
```

### For Cursor

Add to Cursor's MCP configuration:

```json
{
  "mcpServers": {
    "docbro": {
      "command": "docbro",
      "args": ["serve", "--port", "9382"]
    }
  }
}
```

### Testing MCP Server

```bash
# Start the server
docbro serve --port 9382

# In another terminal, test the connection
curl http://localhost:9382/health
```

## ⚙️ Configuration

### Directory Structure (XDG-Compliant)

```bash
~/.config/docbro/           # Configuration files
├── settings.yaml           # Global settings & vector store selection
└── projects.yaml           # Project configurations

~/.local/share/docbro/      # Data storage
├── projects/               # SQLite databases per project
│   ├── python/            # Project-specific data
│   └── fastapi/           # Vector embeddings & metadata
└── installation.yaml       # Installation metadata

~/.cache/docbro/            # Temporary files
└── downloads/              # Cached web pages
```

### Environment Variables

```bash
# Vector Store Configuration
DOCBRO_VECTOR_STORE=sqlite_vec|qdrant  # Choose vector store provider
DOCBRO_QDRANT_URL=http://localhost:6333
DOCBRO_SQLITE_VEC_PATH=/custom/path/vectors.db

# Embeddings & Processing
DOCBRO_OLLAMA_URL=http://localhost:11434
DOCBRO_EMBEDDING_MODEL=mxbai-embed-large
DOCBRO_CHUNK_SIZE=500
DOCBRO_CHUNK_OVERLAP=50

# Crawling & Server
DOCBRO_DEFAULT_CRAWL_DEPTH=3
DOCBRO_DEFAULT_RATE_LIMIT=1.0
DOCBRO_MCP_HOST=localhost
DOCBRO_MCP_PORT=9382
DOCBRO_LOG_LEVEL=WARNING|INFO|DEBUG
```

### Vector Store Selection

#### SQLite-vec (Default)
- **Zero Dependencies**: No external services required
- **Local Storage**: All data stored in `~/.local/share/docbro/`
- **Best For**: Personal use, small to medium documentation sets
- **Setup**: Automatic, no configuration needed

#### Qdrant (Scalable Option)
- **External Service**: Requires Docker
- **Scalable**: Handles millions of documents
- **Best For**: Large documentation sets, production use
- **Setup**: `docker run -p 6333:6333 qdrant/qdrant`

## 🏗️ Architecture & Design

### Technology Stack

```
┌─────────────────────────────────────────┐
│           DocBro CLI (Click + Rich)      │
├─────────────────────────────────────────┤
│         Universal Navigation System      │
│    (Arrow Keys, Vim Keys, Numbers)       │
├─────────────────────────────────────────┤
│           Business Logic Layer           │
│  ┌──────────────┐  ┌──────────────┐     │
│  │ Setup Logic  │  │ Crawler Logic│     │
│  │  50+ Services│  │  Analytics   │     │
│  └──────────────┘  └──────────────┘     │
├─────────────────────────────────────────┤
│           Core Services Layer            │
│  ┌──────────────┐  ┌──────────────┐     │
│  │ Vector Store │  │  Embeddings  │     │
│  │   Factory    │  │   (Ollama)   │     │
│  └──────────────┘  └──────────────┘     │
├─────────────────────────────────────────┤
│           Storage Layer                  │
│  ┌──────────────┐  ┌──────────────┐     │
│  │ SQLite-vec   │  │    Qdrant    │     │
│  │   (Local)    │  │  (External)  │     │
│  └──────────────┘  └──────────────┘     │
└─────────────────────────────────────────┘
```

### Key Design Patterns

- **Service Architecture**: 50+ specialized services with dependency injection
- **Factory Pattern**: Runtime vector store provider selection
- **Repository Pattern**: Database abstraction layer
- **Async/Await**: Non-blocking I/O throughout
- **Settings Layering**: Global → Project → Effective configuration
- **Universal Navigation**: Consistent UX across all CLI interfaces

## 🧪 Testing & Quality

### Test Suite (200+ Tests)

```bash
# Run all tests
pytest tests/ -v

# Test categories
pytest tests/contract/ -v      # API contracts
pytest tests/integration/ -v   # End-to-end flows
pytest tests/unit/ -v          # Component tests
pytest tests/performance/ -v   # Performance validation

# Coverage report
pytest --cov=src tests/ --cov-report=html

# Package integrity check (critical)
./.verify-package.sh
```

### Code Quality

```bash
# Format code
ruff format src/ tests/

# Lint code
ruff check src/ tests/ --fix

# Type checking
mypy src/
```

### Performance Benchmarks

- **Installation**: < 30 seconds complete setup
- **System Check**: < 5 seconds validation
- **Vector Search**: Sub-second queries
- **Menu Response**: < 100ms interaction
- **Crawl Speed**: 100+ pages/minute (with rate limiting)

## 🐛 Troubleshooting Guide

### Quick Diagnostics

```bash
# Full system check
docbro system-check

# Service status
docbro services list

# Health check
docbro --health

# Version info
docbro --version
```

### Common Issues & Solutions

**Issue: Services not detected**
```bash
# Solution 1: Re-run setup with auto-detection
docbro setup --init --auto

# Solution 2: Use SQLite-vec (no external deps)
docbro setup --init --vector-store sqlite_vec

# Solution 3: Manual service check
docker --version
ollama list
```

**Issue: MCP server won't start**
```bash
# Solution 1: Check port availability
lsof -i :9382

# Solution 2: Use different port
docbro serve --port 9383

# Solution 3: Start in foreground for debugging
docbro serve --foreground --port 9382
```

**Issue: Connection refused from AI assistant**
```bash
# Solution 1: Verify global installation
which docbro  # Should show: /Users/[you]/.local/bin/docbro

# Solution 2: Check MCP config path
cat ~/.config/mcp/config.json  # Verify docbro entry

# Solution 3: Restart with correct settings
docbro serve --host 127.0.0.1 --port 9382
```

**Issue: No documentation found in searches**
```bash
# Solution 1: Check project status
docbro list --verbose

# Solution 2: Create and crawl a project
docbro create python -u https://docs.python.org/3/ --depth 3
docbro crawl python --max-pages 100

# Solution 3: Verify embeddings service
ollama list  # Should show mxbai-embed-large
ollama pull mxbai-embed-large  # If missing
```

**Issue: Import errors after changes**
```bash
# Root cause: UV uses Git committed state, not working directory
# Solution: Always commit before installing
git add .
git commit -m "Your changes"
uv tool install . --force --reinstall
```

## 🚀 Roadmap

### Coming Soon
- [ ] Web UI dashboard for project management
- [ ] Multi-language documentation support
- [ ] Custom embedding model support
- [ ] Incremental crawling with change detection
- [ ] Export/import project configurations
- [ ] Cloud vector store integrations (Pinecone, Weaviate)

## 📝 License

MIT License - See [LICENSE](LICENSE) file for details.

## 🤝 Contributing

We welcome contributions! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

### Development Workflow
1. Fork the repository
2. Create a feature branch
3. Follow TDD methodology (tests first)
4. Ensure all tests pass (`pytest tests/`)
5. Submit a pull request

## 📮 Support & Community

- **Issues**: [GitHub Issues](https://github.com/behemotion/doc-bro/issues)
- **Discussions**: [GitHub Discussions](https://github.com/behemotion/doc-bro/discussions)
- **Documentation**: [Wiki](https://github.com/behemotion/doc-bro/wiki)

---

<div align="center">
  <sub>Built with ❤️ by the DocBro team | Powered by Python 3.13+ and UV</sub>
</div>