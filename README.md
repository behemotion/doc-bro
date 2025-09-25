# DocBro - Documentation Crawler & Search Tool

A powerful CLI tool that crawls documentation websites, creates vector databases, and provides RAG-powered search capabilities with MCP server integration for coding agents.

## 🚀 Quick Start

### Install with UV (Recommended):
```bash
uvx install git+https://github.com/behemotion/doc-bro
docbro setup
```

That's it! The setup wizard will guide you through configuring external services.

## ✨ Features

- **One-Command Installation**: Install globally with UV - no repository cloning needed
- **Interactive Setup**: Guided wizard detects and helps configure external services
- **Smart Web Crawling**: Rate limiting, robots.txt respect, configurable depth
- **Vector Search**: Qdrant-powered semantic search with RAG capabilities
- **Local Embeddings**: Ollama integration for privacy-focused, offline operation
- **MCP Server**: Model Context Protocol server for Claude, Cursor, and other AI coding assistants
- **Rich CLI**: Beautiful terminal interface with progress bars and formatted output

## 📋 Prerequisites

The setup wizard will check these for you, but you'll need:

- **Python 3.13+** - Core runtime
- **UV** - Package installer ([install here](https://docs.astral.sh/uv/getting-started/installation/))
- **Docker** - For Qdrant service
- **Ollama** - For local embeddings ([install here](https://ollama.com/))

## 🛠️ Installation

### Recommended: UV Tool Installation

Install DocBro globally using UV for persistent access across all your projects:

```bash
# Install DocBro globally
uvx install git+https://github.com/behemotion/doc-bro

# Run interactive setup wizard
docbro setup

# Verify installation
docbro --help
```

The setup wizard will:
- ✅ Validate Python 3.13+ installation
- ✅ Check for Docker, Ollama, and Qdrant
- ✅ Provide installation guidance for missing services
- ✅ Create configuration directories
- ✅ Set up installation metadata

### Alternative: Development Setup

For development or contributing:

```bash
# Clone and setup
git clone https://github.com/behemotion/doc-bro.git
cd doc-bro

# Install with UV in editable mode
uv pip install -e .

# Run tests
pytest tests/ -v
```

## 📚 Available Commands

DocBro provides the following commands:

| Command | Description | Example |
|---------|-------------|---------|
| `setup` | Interactive setup wizard | `docbro setup` |
| `create` | Create new documentation project | `docbro create myproject -u https://docs.python.org/3/` |
| `crawl` | Crawl and index documentation pages | `docbro crawl myproject --max-pages 100` |
| `list` | List all projects | `docbro list` |
| `serve` | Start MCP server | `docbro serve --port 9382` |
| `remove` | Delete a project | `docbro remove myproject --confirm` |
| `uninstall` | Completely remove DocBro | `docbro uninstall --force` |

Additional options:
- `docbro --help` - Show all available commands
- `docbro --health` - Check service health status
- `docbro --version` - Show version information

## 🎯 Usage

### 1. Create a Documentation Project
```bash
# Basic usage
docbro create python-docs -u https://docs.python.org/3/ --depth 2

# URLs with special characters MUST be quoted
docbro create github-docs -u "https://github.com/astral-sh/uv?tab=readme-ov-file" --depth 2
```

**⚠️ Important:** URLs containing special characters (?, &, *, [, ]) must be quoted to prevent shell interpretation.

### 2. Crawl Documentation
```bash
docbro crawl python-docs --max-pages 100 --rate-limit 2.0
```

### 3. List Projects
```bash
docbro list --status ready
```

### 4. Start MCP Server (for AI Agents)
```bash
docbro serve --port 9382
```

### 5. Remove Projects
```bash
docbro remove python-docs --confirm
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

## 🔧 Advanced Configuration

DocBro uses XDG-compliant directories for configuration:

- **Config**: `~/.config/docbro/`
- **Data**: `~/.local/share/docbro/`
- **Cache**: `~/.cache/docbro/`

### Environment Variables

```bash
DOCBRO_QDRANT_URL=http://localhost:6333
DOCBRO_OLLAMA_URL=http://localhost:11434
DOCBRO_EMBEDDING_MODEL=mxbai-embed-large
DOCBRO_LOG_LEVEL=INFO
```

## 🏗️ Architecture

Built with:
- **Python 3.13+** with async/await
- **Qdrant** - Vector database
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
docbro --health
docbro --version
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

**Server won't start:**
```bash
# Check if port is already in use
lsof -i :9382

# Try a different port
docbro serve --port 9383
```

**Connection refused:**
- Verify DocBro is installed globally: `which docbro`
- Check the command path in your MCP config
- Ensure all required services (Qdrant, Ollama) are running: `docbro --health`

**No documentation found:**
```bash
# List available projects
docbro list

# Crawl some documentation first
docbro create python-docs -u https://docs.python.org/3/
docbro crawl python-docs --max-pages 50
```

## 📝 License

MIT License - See [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📮 Support

- **Issues**: [GitHub Issues](https://github.com/behemotion/doc-bro/issues)
- **Discussions**: [GitHub Discussions](https://github.com/behemotion/doc-bro/discussions)