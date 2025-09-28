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
    docbro project create myproject --type crawling
    docbro crawl myproject
    docbro serve                                  # Start MCP server for AI assistants

  PROJECT MANAGEMENT:
    docbro project                                # Interactive project menu
    docbro project list                           # List all projects
    docbro project create <name> --type <type>    # Create project
    docbro project remove myproject               # Remove project
    docbro project show myproject                 # Show project details
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
```

### Command Details

#### project
```
Usage: docbro project [OPTIONS] COMMAND [ARGS]...

  Manage documentation projects.

  Run without arguments to launch interactive menu: docbro project

  Or use subcommands directly: docbro project create my-docs --type data
  docbro project list --status active docbro project remove old-project
  --confirm docbro project show my-docs --detailed docbro project update my-
  docs --settings '{"key": "value"}'

Options:
  --help  Show this message and exit.

Commands:
  create  Create a new project with specified type and settings.
  list    List projects with optional filtering.
  remove  Remove a project and handle type-specific cleanup.
  show    Show project information and status.
  update  Update project settings and metadata.
```

##### project create
```
Usage: docbro project create [OPTIONS] NAME

  Create a new project with specified type and settings.

  PROJECT TYPES:
    crawling    Web documentation crawler projects
    data        Document upload and vector search projects
    storage     File storage with inventory management

  EXAMPLES:
    docbro project create django --type crawling --description "Django docs"
    docbro project create mydata --type data --settings '{"chunk_size": 1000}'
    docbro project create files --type storage --force

  ARGUMENTS:
    NAME        Project name (must be unique)

  OPTIONS:
    --type      Project type (required): crawling, data, or storage
    --description Optional project description
    --settings  JSON settings override for project configuration
    --force     Overwrite existing project if it exists

Options:
  -t, --type [crawling|data|storage]
                                  Project type  [required]
  -d, --description TEXT          Optional project description
  -s, --settings TEXT             JSON settings override
  -f, --force                     Overwrite existing project
  --help                          Show this message and exit.
```

##### project list
```
Usage: docbro project list [OPTIONS]

  List projects with optional filtering.

  FILTERING OPTIONS:
    --status    Filter by project status (active, inactive, error, processing)
    --type      Filter by project type (crawling, data, storage)
    --limit     Limit number of results returned
    --verbose   Show detailed information for each project

  EXAMPLES:
    docbro project list                           # List all projects
    docbro project list --status active          # List only active projects
    docbro project list --type crawling --limit 5  # List first 5 crawling projects
    docbro project list --verbose                # Show detailed information

  OUTPUT FORMATS:
    Default     Table view with basic information
    --verbose   Detailed view with statistics and settings

Options:
  -st, --status [active|inactive|error|processing]
                                  Filter by status
  -t, --type [crawling|data|storage]
                                  Filter by project type
  -l, --limit INTEGER             Limit number of results
  -v, --verbose                   Show detailed information
  --help                          Show this message and exit.
```

##### project remove
```
Usage: docbro project remove [OPTIONS] NAME

  Remove a project and handle type-specific cleanup.

  SAFETY FEATURES:
    - Confirmation prompt by default (use --confirm to skip)
    - Automatic backup creation before removal (disable with --no-backup)
    - Comprehensive cleanup of all project data and files

  WHAT GETS REMOVED:
    - Project configuration and metadata
    - All uploaded files and crawled content
    - Vector embeddings and search indices
    - Associated database entries
    - Project directories and cached data

  EXAMPLES:
    docbro project remove myproject                    # Remove with confirmation
    docbro project remove myproject --confirm          # Remove without confirmation
    docbro project remove myproject --no-backup        # Remove without backup
    docbro project remove myproject --force            # Force removal even if errors

  ARGUMENTS:
    NAME        Name of the project to remove

  OPTIONS:
    --confirm   Skip confirmation prompt
    --backup    Create backup before removal (default: enabled)
    --force     Force removal even if errors occur

  WARNING:
    This permanently deletes all project data. Use backups to recover if needed.

Options:
  -c, --confirm  Skip confirmation prompt
  -b, --backup   Create backup before removal
  -f, --force    Force removal even if errors
  --help         Show this message and exit.
```

##### project show
```
Usage: docbro project show [OPTIONS] NAME

  Show project information and status.

  INFORMATION DISPLAYED:
    Basic       Name, type, status, creation/update dates
    --detailed  Statistics, settings, file counts, sizes, and more

  EXAMPLES:
    docbro project show django                    # Basic project information
    docbro project show django --detailed        # Detailed project information

  ARGUMENTS:
    NAME        Name of the project to display

  OPTIONS:
    --detailed  Show comprehensive project information and statistics

Options:
  -dt, --detailed  Show detailed information
  --help           Show this message and exit.
```

##### project update
```
Usage: docbro project update [OPTIONS] NAME

  Update project settings and metadata.

  UPDATE OPTIONS:
    --settings    JSON string with new settings to merge with existing
    --description Update or set project description

  EXAMPLES:
    docbro project update django --description "Django documentation project"
    docbro project update mydata --settings '{"chunk_size": 1000, "overlap": 100}'
    docbro project update myproject --settings '{}' --description "Updated description"

  ARGUMENTS:
    NAME        Name of the project to update

  OPTIONS:
    --settings    JSON settings to merge with existing project configuration
    --description New description for the project

  SETTINGS FORMAT:
    Settings must be valid JSON. Existing settings will be merged with new ones.
    Example: '{"chunk_size": 1000, "embedding_model": "custom-model"}'

Options:
  -s, --settings TEXT     JSON settings update
  -d, --description TEXT  Update project description
  --help                  Show this message and exit.
```

#### crawl
```
Usage: docbro crawl [OPTIONS] [NAME]

  Start crawling a documentation project.

  Enhanced flexible crawl modes: - docbro crawl myproject                  #
  Use existing URL - docbro crawl myproject --url "URL"      # Provide/update
  URL - docbro crawl myproject --depth 3        # Override depth

  Examples:   docbro crawl my-project                  # Crawl a specific
  project   docbro crawl my-project --url "URL"     # Set URL and crawl
  docbro crawl --update my-project        # Update an existing project
  docbro crawl --update --all             # Update all projects

Options:
  -u, --url TEXT           Set or update the project URL before crawling
  -m, --max-pages INTEGER  Maximum pages to crawl
  -r, --rate-limit FLOAT   Requests per second
  -d, --depth INTEGER      Override crawl depth for this session
  --update                 Update existing project(s)
  --all                    Process all projects
  --debug                  Show detailed crawl output
  --help                   Show this message and exit.
```

#### serve
```
Usage: docbro serve [OPTIONS]

  Start the MCP server for AI assistant integration.

  The MCP (Model Context Protocol) server provides documentation access to AI
  assistants like Claude.

  Examples:   docbro serve                   # Start server in background
  docbro serve --foreground      # Run in foreground (for debugging)   docbro
  serve --port 8080       # Use custom port   docbro serve --status          #
  Check if server is running

Options:
  --host TEXT       Server host
  --port INTEGER    Server port
  -f, --foreground  Run server in foreground
  --status          Check server status
  --help            Show this message and exit.
```

#### setup
```
Usage: docbro setup [OPTIONS]

  Unified setup command for DocBro configuration.

  This command consolidates all setup operations: - Initialize configuration
  (--init) - Uninstall DocBro (--uninstall) - Reset installation (--reset) -
  Interactive menu (no flags)

  Examples:     docbro setup                           # Interactive menu
  docbro setup --init --auto             # Quick setup with defaults
  docbro setup --init --vector-store sqlite_vec     docbro setup --uninstall
  --force       # Uninstall without confirmation     docbro setup --reset
  --preserve-data   # Reset but keep projects

Options:
  --init                          Initialize DocBro configuration
  --uninstall                     Uninstall DocBro completely
  --reset                         Reset DocBro to fresh state
  --force                         Skip confirmation prompts
  --auto                          Use automatic mode with defaults
  --non-interactive               Disable interactive prompts
  --vector-store [sqlite_vec|qdrant]
                                  Select vector store provider (with --init)
  --backup                        Create backup before uninstalling (with
                                  --uninstall)
  --dry-run                       Show what would be removed (with
                                  --uninstall)
  --preserve-data                 Keep user project data (with --uninstall or
                                  --reset)
  --help                          Show this message and exit.
```


#### health
```
Usage: docbro health [OPTIONS]

  Check health status of DocBro components with comprehensive validation.

  This unified health command provides comprehensive validation of: - System
  requirements (Python version, memory, disk space) - External services
  (Docker, Qdrant, Ollama, Git) - Configuration files (settings, projects,
  vector store) - Project-specific health (when projects exist)

  Category Options:
    --system      System requirements only
    --services    External services only
    --config      Configuration files only
    --projects    Project health only
    (default)     All categories except projects

  Output Formats:
    table         Formatted table with status indicators (default)
    json          Machine-readable JSON for automation
    yaml          YAML format for configuration tools

  Examples:
    docbro health                    # Complete health check
    docbro health --system           # System requirements only
    docbro health --format json     # JSON output for scripts
    docbro health --timeout 30      # Extended timeout

Options:
  -s, --system                    Check only system requirements
  -e, --services                  Check only external services
  -c, --config                    Check only configuration validity
  -p, --projects                  Check project-specific health
  -f, --format [table|json|yaml]  Output format
  -v, --verbose                   Include detailed diagnostic information
  -q, --quiet                     Suppress progress indicators, show only
                                  results
  -t, --timeout INTEGER RANGE     Maximum execution timeout in seconds
                                  [1<=x<=60]
  -P, --parallel INTEGER RANGE    Maximum parallel health checks  [1<=x<=8]
  --help                          Show this message and exit.
```