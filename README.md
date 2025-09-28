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

  INSTALLATION:
    uv tool install git+https://github.com/behemotion/doc-bro

  QUICK START:
    docbro setup                                  # Interactive setup wizard
    docbro project --create myproject --type crawling
    docbro crawl myproject
    docbro serve                                  # Start MCP server for AI assistants

  PROJECT MANAGEMENT:
    docbro project                                # Interactive project menu
    docbro project --list                         # List all projects
    docbro project --create <name> --type <type>  # Create project
    docbro project --remove myproject             # Remove project
    docbro project --show myproject               # Show project details
    docbro upload                                 # Upload files to projects
    docbro health                                 # Check system health

  VECTOR STORE OPTIONS:
    - SQLite-vec: Local, no dependencies, perfect for getting started
    - Qdrant: Scalable, production-ready, requires Docker

  AI ASSISTANT INTEGRATION:
    Once the MCP server is running (docbro serve), AI assistants like Claude
    can access your documentation for context-aware responses.

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
  crawl    Start crawling a documentation project.
  health   Check health status of DocBro components with comprehensive...
  project  Manage documentation projects.
  serve    Start the MCP server for AI assistant integration.
  setup    Unified setup command for DocBro configuration.
  upload   Upload files to documentation projects.
```