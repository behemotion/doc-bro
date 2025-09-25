# DocBro - Local Documentation Crawler & Search

A powerful CLI tool that crawls documentation websites, creates vector databases, and provides RAG-powered search capabilities with MCP server integration for coding agents.

## 🚀 Quick Start

### Install with one command:
```bash
uvx install git+https://github.com/yourusername/local-doc-bro
docbro setup
```

That's it! The setup wizard will guide you through the rest.

## ✨ Features

- **One-Command Installation**: Install globally with `uvx` - no repository cloning needed
- **Interactive Setup**: Guided wizard detects services and provides installation help
- **Smart Web Crawling**: Rate limiting, robots.txt respect, configurable depth
- **Vector Search**: Qdrant-powered semantic search with multiple RAG strategies
- **Local Embeddings**: Ollama integration for privacy-focused, offline operation
- **MCP Server**: Model Context Protocol server for Claude, Cursor, and other AI coding assistants
- **Rich CLI**: Beautiful terminal interface with progress bars and formatted output

## 📋 Prerequisites

The setup wizard will check these for you, but you'll need:

- **Python 3.13+** - Core runtime
- **UV** - Package installer ([install here](https://docs.astral.sh/uv/getting-started/installation/))
- **Docker** - For Qdrant and Redis services
- **Ollama** - For local embeddings ([install here](https://ollama.com/))

## 🛠️ Installation

### Recommended: UVX Installation

```bash
# 1. Install DocBro
uvx install git+https://github.com/yourusername/local-doc-bro

# 2. Run interactive setup
docbro setup

# 3. Check everything is working
docbro status
```

The setup wizard will:
- ✅ Validate Python 3.13+ installation
- ✅ Check for Docker, Ollama, Redis, and Qdrant
- ✅ Provide installation guidance for missing services
- ✅ Create configuration directories
- ✅ Set up installation metadata

### Alternative: Development Setup

For development or if you prefer manual control:

```bash
# Clone and setup
git clone https://github.com/yourusername/local-doc-bro.git
cd local-doc-bro
./setup.sh
```

## 🎯 Usage

### 1. Create a Documentation Project
```bash
docbro create python-docs --url https://docs.python.org/3/ --depth 2
```

### 2. Crawl Documentation
```bash
docbro crawl python-docs --max-pages 100 --rate-limit 2.0
```

### 3. Search Documentation
```bash
docbro search "async await" --project python-docs --limit 10
```

### 4. Start MCP Server (for AI Agents)
```bash
docbro serve --port 8000
```

## 📚 Commands

| Command | Description | Example |
|---------|-------------|---------|
| `setup` | Run interactive setup wizard | `docbro setup` |
| `create` | Create new documentation project | `docbro create <name> --url <docs-url>` |
| `crawl` | Crawl documentation pages | `docbro crawl <name> --max-pages 100` |
| `search` | Search across documentation | `docbro search "query" --project <name>` |
| `list` | List all projects | `docbro list --status ready` |
| `status` | Check system health | `docbro status` |
| `serve` | Start MCP server | `docbro serve --port 8000` |
| `remove` | Delete a project | `docbro remove <name> --confirm` |
| `version` | Show version info | `docbro version --detailed` |

## 🤖 MCP Server Integration

### For Claude Desktop

Add to your Claude Desktop config:

```json
{
  "mcpServers": {
    "docbro": {
      "command": "docbro",
      "args": ["serve", "--port", "8765"]
    }
  }
}
```

## 🔧 Advanced Configuration

DocBro uses XDG-compliant directories for configuration:

- **Config**: `~/.config/docbro/`
- **Data**: `~/.local/share/docbro/`
- **Cache**: `~/.cache/docbro/`

### Environment Variables

```bash
DOCBRO_QDRANT_URL=http://localhost:6333
DOCBRO_REDIS_URL=redis://localhost:6379
DOCBRO_OLLAMA_URL=http://localhost:11434
DOCBRO_EMBEDDING_MODEL=mxbai-embed-large
DOCBRO_LOG_LEVEL=INFO
```

## 🏗️ Architecture

Built with:
- **Python 3.13+** with async/await
- **Qdrant** - Vector database
- **Redis** - Cache and queue
- **Ollama** - Local embeddings
- **SQLite** - Metadata storage
- **FastAPI** - MCP server
- **Click + Rich** - Beautiful CLI

## 🧪 Development

### Running Tests
```bash
pytest tests/ -v
```

### Code Quality
```bash
ruff format src/ tests/
ruff check src/ tests/
```

## 🐛 Troubleshooting

### Check Installation Status
```bash
docbro status --install
docbro version --detailed
```

### Common Issues

**Services not detected:**
```bash
# Re-run setup wizard
docbro setup

# Check individual services
docker --version
ollama --version
```

**Database issues:**
```bash
# Check status and reset if needed
docbro status
```

The interactive setup wizard provides specific guidance for each service that's missing or misconfigured.

## 📝 License

MIT License - See [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📮 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/local-doc-bro/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/local-doc-bro/discussions)