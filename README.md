```
██████╗  ██████╗  ██████╗██████╗ ██████╗  ██████╗
██╔══██╗██╔═══██╗██╔════╝██╔══██╗██╔══██╗██╔═══██╗
██║  ██║██║   ██║██║     ██████╔╝██████╔╝██║   ██║
██║  ██║██║   ██║██║     ██╔══██╗██╔══██╗██║   ██║
██████╔╝╚██████╔╝╚██████╗██████╔╝██║  ██║╚██████╔╝
╚═════╝  ╚═════╝  ╚═════╝╚═════╝ ╚═╝  ╚═╝ ╚═════╝
```

# DocBro

[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![UV Tool](https://img.shields.io/badge/UV-0.8+-green.svg)](https://docs.astral.sh/uv/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## Installation

```bash
# Install globally with UV
uv tool install git+https://github.com/behemotion/doc-bro

# Run interactive setup
docbro setup
```

## What DocBro Can Do

DocBro transforms any documentation website into a searchable knowledge base with AI-powered semantic search. It crawls documentation sites, processes content into vector embeddings, and provides an MCP server for AI assistants like Claude Code to search and retrieve relevant information instantly.

The tool offers flexible vector storage options - either SQLite-vec for local zero-dependency usage or Qdrant for scalable production deployments. With intelligent crawling, rate limiting, and universal arrow-key navigation throughout its CLI interface, DocBro makes documentation accessible and searchable within your coding workflow through seamless AI assistant integration.

## Commands

```
Usage: docbro [OPTIONS] COMMAND [ARGS]...

  DocBro - Local documentation crawler and search tool with RAG capabilities.

  DocBro crawls documentation websites, stores them locally, and provides
  semantic search through an MCP server for AI assistants like Claude.

  Quick start:   docbro create myproject -u "https://docs.example.com"
  docbro crawl myproject   docbro serve

  For interactive setup:   docbro setup

  Command aliases:   create: add, new   remove: delete, erase, rm   list: ls

Options:
  -v, --version       Show version and exit
  --config-file PATH  Configuration file path
  --debug             Enable debug output
  -q, --quiet         Suppress non-essential output
  --json              Output in JSON format
  --no-color          Disable colored output
  --no-progress       Disable progress indicators
  --skip-auto-setup   Skip automatic setup for first-time installations
  --help              Show this message and exit.

Commands:
  crawl   Start crawling a documentation project.
  create  Create a new documentation project.
  health  Check health status of DocBro components with comprehensive...
  list    List all documentation projects.
  remove  Remove a documentation project and all its data.
  serve   Start the MCP server for AI assistant integration.
  setup   Unified setup command for DocBro configuration.
```