# DocBro Development Guidelines

**Last Updated:** 2025-09-28

**IMPORTANT:** This file must be updated every time new functional changes are implemented. Keep the content under 40,000 characters by removing outdated details when adding new content.

## Project Overview
DocBro is a documentation crawler and search tool with RAG capabilities and MCP server integration. Features single-command UV installation with unified setup operations.

## Implementation Status
✅ **100% Complete** - Installation Process Reorganization + Unified Setup Command + Full Vector Store Support

### Core Components
- **UV Installation** - Single command: `uv tool install git+https://github.com/behemotion/doc-bro`
- **Unified Setup System** - All operations under `docbro setup` with flag-based routing
- **Universal Arrow Navigation** - Consistent keyboard navigation across all CLI interfaces
- **Interactive Menu** - Rich-based UI for guided setup when no flags provided
- **Vector Store Selection** - Runtime choice between SQLite-vec and Qdrant with factory pattern
- **Setup Orchestration** - Centralized coordinator for all installation operations
- **Service Detection** - Async detection of Docker, Qdrant, Ollama, Python, UV, Git
- **Documentation Crawler** - Reorganized under `src/logic/crawler/` with functional grouping
- **MCP Server** - FastAPI with installation API
- **Setup Logic** - Reorganized under `src/logic/setup/` with service-oriented architecture

## Tech Stack
- **Python 3.13+**, **UV/UVX 0.8+** - Package management
- **SQLite-vec** - Local vector database (no external dependencies)
- **Qdrant 1.15.1** - Scalable vector database (optional)
- **Ollama** - Embeddings (mxbai-embed-large)
- **FastAPI** - MCP server with REST API
- **Click + Rich** - CLI with progress UI
- **Pydantic v2** - Data validation with enum support
- **pytest + pytest-asyncio** - Testing

## Project Structure
```
src/
├── models/              # Pydantic models (settings, configurations)
├── services/            # Core services (database, vector store, embeddings)
├── cli/                 # CLI commands (setup, create, crawl, serve)
│   └── utils/           # Universal CLI utilities (navigation, etc.)
├── lib/                 # Utilities and logging
└── logic/               # Reorganized business logic
    ├── setup/           # Setup operations
    │   ├── core/        # SetupOrchestrator, CommandRouter, InteractiveMenu
    │   ├── services/    # SetupInitializer, Uninstaller, Configurator, etc.
    │   ├── models/      # SetupOperation, Configuration, MenuState, etc.
    │   └── utils/       # ProgressReporter, user prompts
    ├── crawler/         # Crawler logic
    │   ├── core/        # DocumentationCrawler, BatchCrawler
    │   ├── analytics/   # ErrorReporter, CrawlReport
    │   ├── utils/       # ProgressReporter, CrawlProgressDisplay
    │   └── models/      # CrawlSession, Page, BatchOperation, ErrorEntry
    └── mcp/             # MCP server logic (NEW)
        ├── core/        # McpReadOnlyServer, McpAdminServer, ServerOrchestrator
        ├── services/    # ReadOnlyMcpService, AdminMcpService, CommandExecutor
        ├── models/      # McpServerConfig, McpResponse, FileAccessRequest
        └── utils/       # PortManager, ConfigGenerator, Security
tests/
├── contract/            # API contract tests (setup, crawl, MCP)
├── integration/         # End-to-end tests (setup flows, legacy commands)
├── unit/               # Model/service tests (flag validation, routing)
└── performance/        # <30s validation tests (setup, menu responsiveness)
```

## Installation

```bash
# Single command installation with automatic setup
uv tool install git+https://github.com/behemotion/doc-bro

# Commands available after installation
docbro setup              # Unified setup command (interactive or flag-based)
docbro project            # Project management (interactive or flag-based)
docbro crawl              # Documentation crawling
docbro serve              # MCP server for AI assistants
docbro health             # System health checks
```

**Key Features:**
- ✅ <30s installation with automatic setup
- ✅ Unified setup command for all operations
- ✅ Interactive menu with Rich UI when no flags provided
- ✅ Vector database selection (SQLite-vec or Qdrant) with runtime switching
- ✅ System validation (Python 3.13+, 4GB RAM, 2GB disk)
- ✅ Async service detection (Docker, Qdrant, Ollama, SQLite-vec, UV, Git)
- ✅ Graceful fallback when services unavailable

## Commands

### Core Commands
```bash
# Project Management
docbro project --create <name> --type <type> [--description "text"]
docbro project --list [--status active] [--limit 10] [--verbose]
docbro project --show <name> [--detailed]
docbro project --remove <name> [--confirm] [--backup]
docbro project --update <name> [--settings '{}'] [--description "text"]

# Documentation Crawling
docbro crawl <name> [--url "url"] [--max-pages 100] [--rate-limit 1.0] [--depth 3]
docbro crawl --update <name>           # Re-crawl existing project
docbro crawl --update --all            # Update all projects

# File Upload
docbro upload                          # Interactive upload menu
docbro upload files --project <name> --source <path/url> --type <type>
docbro upload status [--project <name>] [--active]     # Check upload status

# Unified Setup & Configuration
docbro setup                           # Interactive menu
docbro setup --init --auto             # Quick initialization
docbro setup --init --vector-store sqlite_vec
docbro setup --uninstall --force       # Force uninstall
docbro setup --reset --preserve-data   # Reset keeping projects

# Server Operations
docbro serve [--host 0.0.0.0] [--port 9382] [--foreground]    # Read-only MCP server (default)
docbro serve --admin [--host 127.0.0.1] [--port 9384]         # Admin MCP server (localhost only)
docbro health [--system] [--services] [--config] [--projects]
```

### Testing
```bash
pytest tests/ -v                # All tests
pytest tests/performance/ -v    # Performance validation
pytest --cov=src tests/         # Coverage report
./.verify-package.sh             # Verify package installation integrity (CRITICAL after model changes)
```

## Configuration

### Directories (XDG-Compliant)
- `~/.config/docbro/` - Config files
- `~/.local/share/docbro/` - Data storage
- `~/.cache/docbro/` - Temp files

### Vector Store Configuration
- **SQLite-vec**: Local storage in `~/.local/share/docbro/projects/`
- **Qdrant**: External service at `http://localhost:6333`
- **Provider Selection**: Stored in `~/.config/docbro/settings.yaml`

### Environment Variables
```bash
# Vector Store
DOCBRO_VECTOR_STORE=qdrant|sqlite_vec
DOCBRO_QDRANT_URL=http://localhost:6333
DOCBRO_SQLITE_VEC_PATH=/path/to/vectors.db

# Embeddings & Processing
DOCBRO_OLLAMA_URL=http://localhost:11434
DOCBRO_EMBEDDING_MODEL=mxbai-embed-large
DOCBRO_CHUNK_SIZE=500
DOCBRO_CHUNK_OVERLAP=50

# Crawling & Server
DOCBRO_DEFAULT_CRAWL_DEPTH=3
DOCBRO_DEFAULT_RATE_LIMIT=1.0
DOCBRO_MCP_READ_ONLY_HOST=0.0.0.0
DOCBRO_MCP_READ_ONLY_PORT=9383
DOCBRO_MCP_ADMIN_HOST=127.0.0.1
DOCBRO_MCP_ADMIN_PORT=9384
DOCBRO_LOG_LEVEL=WARNING|INFO|DEBUG
```

## Vector Store Architecture

### Vector Store Selection
- **Interactive Mode**: User prompted to choose between SQLite-vec and Qdrant
- **Auto Mode**: Specify provider via `--vector-store` CLI option
- **Settings Persistence**: Choice saved in `GlobalSettings.vector_store_provider`
- **Runtime Factory**: `VectorStoreFactory` creates appropriate service instance

### Provider Models
- **VectorStoreProvider** - Enum with SQLITE_VEC and QDRANT options
- **SQLiteVecService** - Local vector storage with no external dependencies
- **VectorStoreService** - Qdrant-based scalable vector storage
- **VectorStoreFactory** - Runtime provider selection based on settings

### Setup Flow
1. System requirements validation (Python 3.13+, memory, disk)
2. Vector store provider selection (interactive) or CLI override
3. Provider-specific setup and validation
4. Settings persistence with enum serialization
5. Service availability warnings with setup instructions

### MCP Integration

#### Dual Server Architecture
- **Read-Only Server** (Port 9383): Provides safe read access to projects and documentation
  - Server name: `docbro` (renamed from doc-bro-mcp)
  - Project listing and search capabilities
  - File access with project-type-based restrictions
  - Vector search across project content
  - Health monitoring endpoints
- **Admin Server** (Port 9384): Full administrative control with security restrictions
  - Server name: `docbro-admin` (renamed from doc-bro-mcp-admin)
  - Complete DocBro command execution (with restrictions)
  - Project creation and management
  - Crawling operations and batch processing
  - Localhost-only binding for security
  - **BLOCKED OPERATIONS**: Uninstall, reset, and delete-all-projects operations are prohibited via MCP admin for security

#### Security Features
- **Network Isolation**: Admin server restricted to localhost (127.0.0.1) only
- **Access Control**: File access varies by project type (crawling=metadata, storage=full)
- **Input Sanitization**: Command injection and path traversal protection
- **Resource Limits**: Timeout enforcement and memory management
- **Operation Restrictions**: Critical system operations (uninstall, reset, delete-all) blocked via MCP admin

#### MCP Client Configuration
- **Auto-Generated Configs**: Client configuration files created in `mcp/` directory
- **Claude Code Integration**: Official CLI with dedicated MCP tools
- **Universal Compatibility**: Works with any MCP-compliant AI assistant
- **Concurrent Operations**: Both servers can run simultaneously on different ports

## Universal Arrow Navigation Architecture

### Navigation Components
- **ArrowNavigator** (`src/cli/utils/navigation.py`) - Main navigation engine with cross-platform keyboard input
- **NavigationChoice** - Data structure for menu items with value, label, description, and styling
- **Universal Interface** - Consistent navigation behavior across all CLI components

### Navigation Features
- **Multi-Input Support**: ↑/↓ arrows, j/k vim keys, numbers 1-9, Enter, Escape/q, ? for help
- **Visual Highlighting**: Blue background for current selection with arrow indicator (`→`)
- **Cross-Platform**: Full keyboard support on Unix/macOS, graceful fallback on Windows/non-TTY
- **Accessibility**: Multiple navigation methods accommodate different user preferences

### Mandatory Navigation Requirements
1. **ArrowNavigator**: Full arrow key support (↑/↓) for sequential navigation
2. **AddressNavigator**: Direct number selection (1-9) for quick access
3. **Y/N Exclusion**: Never use numbered structure for yes/no confirmations - only y/n keys
4. **Option Descriptions**: Every selectable option MUST display a short descriptive label
5. **Status Display**: Show current status in short form for options where applicable (e.g., "[configured]", "[enabled]", "[running]")

### Implementation Patterns
- **Centralized Logic**: Single navigation utility eliminates code duplication
- **Clean Interfaces**: `NavigationChoice` objects separate data from presentation
- **Consistent Behavior**: Same navigation experience in setup menus, prompts, and all future interfaces
- **Fallback Support**: Automatic detection and graceful degradation for unsupported environments

### Usage Guidelines
**For All CLI Components:**
```python
from src.cli.utils.navigation import ArrowNavigator, NavigationChoice

# Standard choice prompt
navigator = ArrowNavigator()
result = navigator.navigate_choices(prompt, choices, default)

# Full menu interface
menu_items = [NavigationChoice(value, label) for value, label in choices]
result = navigator.navigate_menu(title, menu_items)
```

**Navigation Standards:**
- All interactive CLI elements MUST use the universal navigation system
- Consistent keyboard shortcuts across all interfaces
- Visual highlighting and help system integration required
- Cross-platform compatibility mandatory
- Y/N confirmations use only y/n keys (never numbered options)
- Every option must have descriptive label and status when applicable

## Development Guidelines

### Code Style
- PEP 8 with 100 char line limit
- Async/await for all I/O operations
- Type hints throughout
- Pydantic v2 for validation
- Structured logging with component tracking

### Testing
- **TDD Methodology**: Tests written first
- **200+ Tests**: Contract, integration, unit, performance layers
- **Performance**: <30s installation validation
- **Coverage**: Comprehensive test suite with 100% UV compliance

### Key Patterns
- **Service Architecture**: 50+ services with dependency injection
- **Factory Pattern**: Runtime vector store provider selection
- **Settings Layering**: Global → project → effective configuration
- **Async/Await**: Non-blocking I/O throughout
- **Repository Pattern**: Database abstraction layer

## Performance Metrics
- **Installation**: <30 seconds complete setup
- **System Check**: <5 seconds validation
- **Vector Search**: Sub-second semantic queries
- **Memory**: Chunked processing for large documentation sites
- **Caching**: 5-minute query cache TTL

## Dependencies & Integrations
### Core Dependencies
- **Python 3.13+**, **UV/UVX 0.8+** (package management)
- **FastAPI**, **Click + Rich** (API + CLI)
- **Pydantic v2**, **PyYAML** (data validation)
- **aiosqlite**, **qdrant-client**, **sqlite-vec** (storage)
- **BeautifulSoup4**, **httpx** (web scraping)

### External Services
- **Qdrant**: Production vector database (Docker)
- **Ollama**: Local embeddings (mxbai-embed-large)
- **Docker**: Container management for services

## Crawler Logic Organization

### New Structure (September 2025)
All crawler functionality has been reorganized from scattered `src/services/` and `src/models/` locations into a unified `src/logic/crawler/` structure:

**Core Crawler Components:**
- `src.logic.crawler.core.crawler.DocumentationCrawler` - Main crawler engine
- `src.logic.crawler.core.batch.BatchCrawler` - Multi-project orchestration

**Analytics & Reporting:**
- `src.logic.crawler.analytics.reporter.ErrorReporter` - Error collection and reporting
- `src.logic.crawler.analytics.report.CrawlReport` - Operation results and metrics

**Utilities:**
- `src.logic.crawler.utils.progress.ProgressReporter` - Advanced progress tracking
- `src.logic.crawler.utils.progress.CrawlProgressDisplay` - Simple progress display

**Models:**
- `src.logic.crawler.models.session.CrawlSession` - Session tracking
- `src.logic.crawler.models.page.Page` - Page data structure
- `src.logic.crawler.models.batch.BatchOperation` - Batch operation tracking
- `src.logic.crawler.models.error.ErrorEntry` - Error data structure

### Import Guidelines
**Use new paths:**
```python
from src.logic.crawler.core.crawler import DocumentationCrawler
from src.logic.crawler.analytics.reporter import ErrorReporter
from src.logic.crawler.utils.progress import ProgressReporter
```

**Old paths removed:** All `src.services.crawler*` and related imports have been removed per constitutional guidelines (no backward compatibility).

## Setup Logic Organization

### New Structure (September 2025)
All setup functionality has been reorganized from scattered `src/services/` locations into a unified `src/logic/setup/` structure following service-oriented architecture:

**Core Setup Components:**
- `src.logic.setup.core.orchestrator.SetupOrchestrator` - Main setup coordinator
- `src.logic.setup.core.router.CommandRouter` - Flag routing and validation
- `src.logic.setup.core.menu.InteractiveMenu` - Rich-based interactive UI

**Setup Services:**
- `src.logic.setup.services.initializer.SetupInitializer` - Installation logic
- `src.logic.setup.services.uninstaller.SetupUninstaller` - Clean uninstall
- `src.logic.setup.services.configurator.SetupConfigurator` - Config management
- `src.logic.setup.services.validator.SetupValidator` - System validation
- `src.logic.setup.services.detector.ServiceDetector` - Async service detection
- `src.logic.setup.services.reset_handler.ResetHandler` - Reset operations

**Setup Models:**
- `src.logic.setup.models.operation.SetupOperation` - Operation tracking
- `src.logic.setup.models.configuration.SetupConfiguration` - Setup config
- `src.logic.setup.models.menu_state.MenuState` - Menu navigation state
- `src.logic.setup.models.service_info.ServiceInfo` - External service info
- `src.logic.setup.models.uninstall_manifest.UninstallManifest` - Uninstall planning

**Setup Utilities:**
- `src.logic.setup.utils.progress.ProgressReporter` - Rich progress bars
- `src.logic.setup.utils.prompts` - User interaction helpers

### Setup Import Guidelines
**Use new paths:**
```python
from src.logic.setup.core.orchestrator import SetupOrchestrator
from src.logic.setup.services.initializer import SetupInitializer
from src.logic.setup.utils.progress import ProgressReporter
```

**Unified CLI Command:**
```bash
docbro setup                    # Interactive menu
docbro setup --init --auto      # Quick initialization
docbro setup --uninstall --force # Force uninstall
docbro setup --reset            # Full reset
```

## Package Integrity & Import Safety

### Critical Development Practice - Root Cause Identified
**UV tool install uses Git committed state, NOT working directory changes!**

**ALWAYS commit changes before testing installation:**
```bash
git add .
git commit -m "Your changes"
uv tool install . --force --reinstall
```

**Root Cause:** UV tool install builds from the last Git commit, ignoring uncommitted changes in your working directory. This means:
- Uncommitted new model files won't be included
- Uncommitted `__init__.py` changes won't be included
- Installation appears to work but uses stale code

### When to commit before installing:
- After adding new model files
- After modifying `__init__.py` files
- After changing package structure
- Before testing `uv tool install`
- When encountering import errors

### Verification Script (Emergency Only)
For urgent debugging only, use:
```bash
./.verify-package.sh
```

**Primary Rule:** Always commit first, then install. This prevents 99% of import issues.

## Important Instructions
- ALWAYS check constitution.md before working on any features or making changes
- Do what has been asked; nothing more, nothing less
- NEVER create files unless absolutely necessary for achieving your goal
- ALWAYS prefer editing an existing file to creating a new one
- NEVER proactively create documentation files (*.md) or README files unless explicitly requested
