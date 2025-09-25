# DocBro Quickstart Guide

**Date**: 2025-09-25
**Version**: 1.0.0

## Prerequisites

Before starting, ensure you have:
- Python 3.11 or higher
- Docker and Docker Compose
- Ollama installed locally
- 2GB+ free disk space

## Installation

### 1. Quick Setup (Recommended)
```bash
# Clone the repository
git clone https://github.com/yourusername/docbro.git
cd docbro

# Run the setup script
./setup.sh

# This will:
# - Install Python dependencies
# - Start Docker services (Qdrant, Redis)
# - Pull the default Ollama model
# - Initialize the database
```

### 2. Manual Setup
```bash
# Install Python package
pip install -e .

# Start services
docker-compose -f docker/docker-compose.yml up -d

# Pull Ollama model
ollama pull mxbai-embed-large

# Verify installation
docbro status
```

## Quick Start Tutorial

### Step 1: Create Your First Project
```bash
# Create a project for Python documentation
docbro create python-docs --url https://docs.python.org/3/ --depth 2

# Output:
# ✅ Project 'python-docs' created successfully
# 📁 Project ID: a1b2c3d4-...
# 🌐 Source URL: https://docs.python.org/3/
# 📊 Status: creating
```

### Step 2: Start Crawling
```bash
# Begin crawling with rate limiting
docbro crawl python-docs --max-pages 100 --rate-limit 2.0

# Output:
# 🕷️ Starting crawl for 'python-docs'...
# ⏳ Crawling: 45/100 pages [===>    ] 45%
# ✅ Crawl completed: 100 pages in 52s
```

### Step 3: Search Documentation
```bash
# Search for async programming information
docbro search "async await coroutines" --project python-docs --limit 5

# Output:
# 🔍 Searching in 'python-docs'...
#
# 1. [0.92] Coroutines and Tasks - Python 3.12 documentation
#    "Coroutines declared with async/await syntax is the preferred way..."
#    URL: https://docs.python.org/3/library/asyncio-task.html
#
# 2. [0.87] asyncio — Asynchronous I/O
#    "asyncio is a library to write concurrent code using async/await..."
#    URL: https://docs.python.org/3/library/asyncio.html
# ...
```

### Step 4: List Your Projects
```bash
# View all projects with their status
docbro list

# Output:
# ┏━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━┓
# ┃ Name          ┃ Source URL            ┃ Status ┃ Pages   ┃ Last Crawl  ┃
# ┡━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━┩
# │ python-docs   │ docs.python.org/3/    │ ready  │ 100     │ 2 mins ago  │
# │ react-docs    │ react.dev/learn       │ ready  │ 75      │ 1 day ago   │
# │ nodejs-docs   │ nodejs.org/docs       │ ready  │ 150     │ 65 days ago │ ⚠️
# └───────────────┴───────────────────────┴────────┴─────────┴─────────────┘
# ⚠️ = Outdated (>60 days)
```

## MCP Agent Connection

### Step 1: Start the MCP Server
```bash
# Start the server on default port
docbro serve --port 8000

# Output:
# 🚀 DocBro MCP Server starting...
# 📡 WebSocket: ws://localhost:8000/mcp
# 🌐 REST API: http://localhost:8000/api
# ✅ Server ready for connections
```

### Step 2: Connect Your Agent
Configure your coding agent (e.g., Claude Code) with:
```json
{
  "mcp_servers": {
    "docbro": {
      "url": "ws://localhost:8000/mcp",
      "capabilities": ["search", "chunks"]
    }
  }
}
```

### Step 3: Agent Usage Example
```python
# In your agent's code assistant
agent.query("How to use asyncio in Python?", project="python-docs")
# Returns relevant documentation chunks with context
```

## Common Operations

### Rename a Project
```bash
docbro rename python-docs py-docs
# ✅ Project renamed from 'python-docs' to 'py-docs'
```

### Re-crawl Outdated Project
```bash
# Re-crawl an outdated project
docbro crawl nodejs-docs --max-pages 200
# 🔄 Re-crawling 'nodejs-docs' (outdated: 65 days)...
```

### Delete a Project
```bash
docbro remove old-project --confirm
# ⚠️  Removing project 'old-project' and all associated data...
# ✅ Project removed successfully
```

### Check System Status
```bash
docbro status

# Output:
# System Status:
# ✅ Database: Connected
# ✅ Qdrant: Connected (1.2M vectors)
# ✅ Redis: Connected
# ✅ Ollama: Connected (mxbai-embed-large loaded)
#
# Statistics:
# 📁 Projects: 3
# 📄 Total Pages: 325
# 🔢 Total Chunks: 4,875
# 💾 Storage Used: 1.2 GB
```

### Change Embedding Model
```bash
# Switch to a different model
docbro config --embedding-model nomic-embed-text

# Re-embed existing project with new model
docbro crawl python-docs --reindex-only
```

## Advanced Usage

### Custom Crawl Configuration
```bash
# Deep crawl with custom settings
docbro crawl my-docs \
  --depth 5 \
  --max-pages 500 \
  --rate-limit 1.0 \
  --include-pattern "*/api/*" \
  --exclude-pattern "*/legacy/*"
```

### Export/Import Projects
```bash
# Export a project
docbro export python-docs --output ./backups/python-docs.tar.gz

# Import a project
docbro import ./backups/python-docs.tar.gz --name python-docs-restored
```

### JSON Output for Scripting
```bash
# Get JSON output for automation
docbro list --format json | jq '.[] | select(.is_outdated==true)'

# Search with JSON output
docbro search "query" --format json | jq '.results[0].content'
```

## Troubleshooting

### Services Not Starting
```bash
# Check Docker services
docker-compose -f docker/docker-compose.yml ps

# View logs
docker-compose -f docker/docker-compose.yml logs -f

# Restart services
docker-compose -f docker/docker-compose.yml restart
```

### Ollama Model Issues
```bash
# List available models
ollama list

# Pull model if missing
ollama pull mxbai-embed-large

# Test Ollama connection
curl http://localhost:11434/api/tags
```

### Database Issues
```bash
# Reset database (WARNING: deletes all data)
rm -f ~/.docbro/docbro.db
docbro status  # Will recreate database
```

## Performance Tips

1. **Rate Limiting**: Use appropriate rate limits (1-2 req/s) to avoid overwhelming documentation servers
2. **Chunk Size**: Adjust chunk size (default: 1000 chars) based on your use case
3. **Concurrent Crawls**: Only one crawl runs at a time to prevent resource exhaustion
4. **Vector Indexing**: Large projects (>10k pages) may take time to index initially

## Next Steps

- Explore RAG strategies: `docbro search --strategy rerank`
- Set up automatic re-crawling with cron
- Integrate with your IDE or coding workflow
- Customize chunk sizes for your agent: `docbro config --chunk-size 1500`

## Getting Help

```bash
# View all commands
docbro --help

# Get help for specific command
docbro crawl --help

# Check version
docbro --version
```

For more information, visit the [DocBro Documentation](https://github.com/yourusername/docbro/wiki)