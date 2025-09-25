# Installing DocBro MCP Server for Claude Desktop

## Installation Steps

### 1. Locate Claude Desktop Configuration

The Claude Desktop configuration file is typically located at:
- **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
- **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
- **Linux**: `~/.config/Claude/claude_desktop_config.json`

### 2. Manual Installation

#### Option A: Add to existing configuration
If you already have a `claude_desktop_config.json` file, add the DocBro server to the `mcpServers` section:

```json
{
  "mcpServers": {
    "docbro": {
      "command": "/Users/alexandr/Repository/local-doc-bro/docbro",
      "args": [
        "serve",
        "--port",
        "9382"
      ],
      "env": {
        "DOCBRO_MCP_PORT": "9382",
        "DOCBRO_DATABASE_PATH": "/Users/alexandr/.docbro/docbro.db",
        "DOCBRO_QDRANT_URL": "http://localhost:6333",
        "DOCBRO_REDIS_URL": "redis://localhost:6379",
        "DOCBRO_OLLAMA_URL": "http://localhost:11434",
        "DOCBRO_EMBEDDING_MODEL": "mxbai-embed-large",
        "DOCBRO_LOG_LEVEL": "INFO"
      }
    }
    // ... other MCP servers ...
  }
}
```

#### Option B: Create new configuration
If you don't have a configuration file yet, copy the provided `claude_desktop_config.json`:

```bash
# macOS
cp claude_desktop_config.json ~/Library/Application\ Support/Claude/claude_desktop_config.json
```

### 3. Automatic Installation (macOS)

Run the installation script:

```bash
./install_mcp_global.sh
```

This script will:
1. Check if Claude Desktop config exists
2. Backup existing configuration
3. Merge DocBro MCP server configuration
4. Verify the installation

### 4. Verify Installation

1. **Restart Claude Desktop** (completely quit and reopen)
2. Check MCP server availability in Claude
3. Test with: "Can you search documentation using DocBro?"

## Prerequisites

Before using the DocBro MCP server, ensure:

1. **Docker services are running:**
   ```bash
   docker-compose -f docker/docker-compose.yml up -d
   ```

2. **Python dependencies installed:**
   ```bash
   pip install -e .
   ```

3. **Ollama is running** (for embeddings):
   ```bash
   ollama serve
   ```

4. **Embedding model is available:**
   ```bash
   ollama pull mxbai-embed-large
   ```

## Configuration Options

You can customize the MCP server by modifying environment variables:

| Variable | Default | Description |
|----------|---------|-------------|
| `DOCBRO_MCP_PORT` | 9382 | MCP server port |
| `DOCBRO_DATABASE_PATH` | ~/.docbro/docbro.db | SQLite database location |
| `DOCBRO_QDRANT_URL` | http://localhost:6333 | Qdrant vector DB URL |
| `DOCBRO_REDIS_URL` | redis://localhost:6379 | Redis cache URL |
| `DOCBRO_OLLAMA_URL` | http://localhost:11434 | Ollama API URL |
| `DOCBRO_EMBEDDING_MODEL` | mxbai-embed-large | Embedding model name |
| `DOCBRO_LOG_LEVEL` | INFO | Logging verbosity |

## Usage in Claude Desktop

Once installed, you can use DocBro commands in any Claude Desktop conversation:

### Available Commands

1. **Check status:**
   ```
   Check DocBro status
   ```

2. **List projects:**
   ```
   List all DocBro documentation projects
   ```

3. **Search documentation:**
   ```
   Search for "python package manager" in DocBro
   ```

4. **Create project:**
   ```
   Create a DocBro project for https://docs.example.com
   ```

5. **Crawl documentation:**
   ```
   Crawl documentation for project-name
   ```

## Troubleshooting

### MCP Server Not Responding

1. Check if services are running:
   ```bash
   docker ps
   curl http://localhost:9382/health
   ```

2. Check logs:
   ```bash
   tail -f ~/.docbro/logs/mcp_server.log
   ```

3. Restart services:
   ```bash
   docker-compose -f docker/docker-compose.yml restart
   ./docbro serve --port 9382
   ```

### Permission Issues

Make sure the DocBro CLI is executable:
```bash
chmod +x /Users/alexandr/Repository/local-doc-bro/docbro
```

### Port Conflicts

If port 9382 is in use, change it in both:
1. The Claude Desktop config file
2. The DOCBRO_MCP_PORT environment variable

## Uninstallation

To remove DocBro MCP server from Claude Desktop:

1. Edit `~/Library/Application Support/Claude/claude_desktop_config.json`
2. Remove the "docbro" entry from "mcpServers"
3. Restart Claude Desktop

## Support

For issues or questions:
- Check the test report: `TEST_REPORT.md`
- Review logs: `~/.docbro/logs/`
- Test connectivity: `python test_mcp_client.py`

---
*Last updated: 2025-09-25*