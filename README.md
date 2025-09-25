# DocBro - Local Documentation Crawler & Search

A powerful CLI tool that crawls documentation websites, creates vector databases, and provides RAG-powered search capabilities with MCP server integration for coding agents.

## 🚀 Quick Start

### Install with one command:
```bash
uvx install git+https://github.com/behemotion/doc-bro
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
- **Docker** - For Qdrant service
- **Ollama** - For local embeddings ([install here](https://ollama.com/))

## 🛠️ Installation

### Recommended: UVX Installation

```bash
# 1. Install DocBro
uvx install git+https://github.com/behemotion/doc-bro

# 2. Run interactive setup
docbro setup

# 3. Check everything is working
docbro status
```

The setup wizard will:
- ✅ Validate Python 3.13+ installation
- ✅ Check for Docker, Ollama, and Qdrant
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
# Basic usage
docbro create python-docs --url https://docs.python.org/3/ --depth 2

# URLs with special characters MUST be quoted
docbro create github-docs --url "https://github.com/astral-sh/uv?tab=readme-ov-file" --depth 2
```

**⚠️ Important:** URLs containing special characters (?, &, *, [, ]) must be quoted to prevent shell interpretation.

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

DocBro provides a Model Context Protocol (MCP) server that allows AI coding assistants like Claude Code, Claude Desktop, and Cursor to search your crawled documentation directly.

### For Claude Code

Claude Code supports MCP servers through configuration. Add DocBro to your MCP configuration:

#### 1. Install DocBro MCP Server
```bash
# Install DocBro globally if not already done
uvx install git+https://github.com/yourusername/local-doc-bro

# Verify installation
docbro --version
```

#### 2. Configure MCP Client

Create or update your MCP configuration file at `~/.config/mcp/config.json`:

```json
{
  "mcpServers": {
    "docbro": {
      "command": "docbro",
      "args": ["serve", "--port", "8765", "--host", "127.0.0.1"],
      "env": {
        "DOCBRO_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

#### 3. Alternative Configuration Methods

**Option A: Using UVX command (Recommended)**
```json
{
  "mcpServers": {
    "docbro": {
      "command": "uvx",
      "args": ["run", "docbro", "serve", "--port", "8765"],
      "env": {
        "DOCBRO_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

**Option B: Direct Python execution**
```json
{
  "mcpServers": {
    "docbro": {
      "command": "python",
      "args": ["-m", "src.cli.main", "serve", "--port", "8765"],
      "cwd": "/path/to/local-doc-bro",
      "env": {
        "PYTHONPATH": "/path/to/local-doc-bro",
        "DOCBRO_LOG_LEVEL": "INFO"
      }
    }
  }
}
```

#### 4. Start and Test MCP Server

```bash
# Test the server manually
docbro serve --port 8765

# In another terminal, test the connection
curl http://localhost:8765/health
```

You should see a health check response indicating the server is running.

#### 5. Available MCP Endpoints

Once configured, Claude Code can access these DocBro functions:

- **`/mcp/projects`** - List all crawled documentation projects
- **`/mcp/search`** - Search across documentation with RAG
- **`/mcp/connect`** - Establish MCP session
- **`/health`** - Server health check

#### 6. Usage in Claude Code

After configuration, you can ask Claude Code to:

```
"Search the Python documentation for async/await examples"
"Find Flask routing documentation"
"Look up Django model field types in the docs"
```

Claude Code will automatically use the DocBro MCP server to search your local documentation.

### For Claude Desktop

Add to your Claude Desktop config (`~/Library/Application\ Support/Claude/claude_desktop_config.json` on macOS):

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

### For Cursor

Add to Cursor's MCP configuration:

```json
{
  "mcpServers": {
    "docbro": {
      "command": "docbro",
      "args": ["serve", "--port", "8766"]
    }
  }
}
```

### Advanced MCP Configuration

#### Custom Server Settings
```json
{
  "mcpServers": {
    "docbro": {
      "command": "docbro",
      "args": [
        "serve",
        "--port", "8765",
        "--host", "127.0.0.1"
      ],
      "env": {
        "DOCBRO_LOG_LEVEL": "DEBUG",
        "DOCBRO_QDRANT_URL": "http://localhost:6333",
        "DOCBRO_OLLAMA_URL": "http://localhost:11434"
      }
    }
  }
}
```

#### Multiple Project Configurations
```json
{
  "mcpServers": {
    "docbro-python": {
      "command": "docbro",
      "args": ["serve", "--port", "8765"]
    },
    "docbro-js": {
      "command": "docbro",
      "args": ["serve", "--port", "8766"]
    }
  }
}
```

### MCP Troubleshooting

#### Check MCP Server Status
```bash
# Verify DocBro is installed and accessible
docbro --version

# Test server startup
docbro serve --port 8765 --host 127.0.0.1

# Check health endpoint
curl http://127.0.0.1:8765/health
```

#### Common Issues

**Server won't start:**
```bash
# Check if port is already in use
lsof -i :8765

# Try a different port
docbro serve --port 8766
```

**Connection refused:**
- Verify DocBro is installed globally: `which docbro`
- Check the command path in your MCP config
- Ensure all required services (Qdrant, Ollama) are running: `docbro status`

**No documentation found:**
```bash
# List available projects
docbro list

# Crawl some documentation first
docbro create python-docs --url https://docs.python.org/3/
docbro crawl python-docs --max-pages 50
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
