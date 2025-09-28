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

### Command Details

#### project
```
Usage: docbro project [OPTIONS] [NAME]

  Manage documentation projects.

  USAGE:
    docbro project                    # Interactive menu
    docbro project <name>             # Show project details (same as --show)
    docbro project <flags> [options]  # Execute specific action

  FLAGS (mutually exclusive):
    --create, -c      Create a new project
    --list, -l, -ls   List projects
    --remove, -r, -rm Remove a project
    --show, -s        Show project details
    --update, -u      Update project settings

  EXAMPLES:
    docbro project                                    # Interactive menu
    docbro project myproject                          # Show project details (implicit)
    docbro project --create myproject --type data    # Create project
    docbro project --list --status active            # List active projects
    docbro project --remove myproject --confirm      # Remove project
    docbro project --show myproject --detailed       # Show project details (explicit)
    docbro project --update myproject --settings '{...}'  # Update settings

  PROJECT TYPES:
    crawling    Web documentation crawler projects
    data        Document upload and vector search projects
    storage     File storage with inventory management

Options:
  -c, --create                    Create a new project
  -l, -ls, --list                 List projects
  -r, -rm, --remove               Remove a project
  -s, --show                      Show project details
  -u, --update                    Update project settings
  -t, --type [crawling|data|storage]
                                  Project type (for create)
  -d, --description TEXT          Project description
  --settings TEXT                 JSON settings
  -f, --force                     Force operation
  -st, --status [active|inactive|error|processing]
                                  Filter by status (for list)
  --limit INTEGER                 Limit results (for list)
  -v, --verbose                   Verbose output
  --confirm                       Skip confirmation (for remove)
  -b, --backup                    Create backup (for remove)
  -dt, --detailed                 Detailed view (for show)
  --help                          Show this message and exit.
```

#### crawl
```
Usage: docbro crawl [OPTIONS] [NAME]

  Start crawling a documentation project.

  Crawl documentation websites to build a local searchable knowledge base. The
  crawler follows links, extracts content, and creates vector embeddings.

  CRAWL MODES:
    docbro crawl myproject                  # Crawl using project's configured URL
    docbro crawl myproject -u "URL"         # Set/update URL and crawl
    docbro crawl --update myproject         # Re-crawl to update content
    docbro crawl --update --all             # Update all projects

  PERFORMANCE OPTIONS:
    -m, --max-pages N    Limit crawl to N pages (useful for testing)
    -r, --rate-limit F   Requests per second (default: 1.0, be respectful!)
    -d, --depth N        Override default crawl depth for this session

  UPDATE MODES:
    --update             Re-crawl existing projects to get latest content
    --all                Process all projects (use with --update)

  EXAMPLES:
    docbro crawl django                     # Crawl Django project
    docbro crawl fastapi -d 2 -m 50         # Crawl FastAPI, depth 2, max 50 pages
    docbro crawl docs -u "https://new-url.com/"  # Update URL and crawl
    docbro crawl --update --all             # Update all projects
    docbro crawl myproject --debug          # Show detailed crawl progress

  WORKFLOW:
    1. Ensure project exists: docbro project --list
    2. Start crawling: docbro crawl myproject
    3. Check progress: look for completion message
    4. Use content: docbro serve (starts MCP server for AI assistants)

  RATE LIMITING:
    Please be respectful of target websites. Default rate limit is 1 req/sec.
    Increase only if you own the target site or have explicit permission.

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

  The MCP (Model Context Protocol) server exposes your documentation to AI
  assistants like Claude, enabling context-aware responses.

  SERVER MODES:
    docbro serve                   # Start in background (recommended)
    docbro serve --foreground      # Run in foreground (for debugging)
    docbro serve --status          # Check if server is running

  CONFIGURATION:
    --host HOST      Server bind address (default: 0.0.0.0, all interfaces)
    --port PORT      Server port (default: 9382)
    -f, --foreground Run in foreground instead of background

  MCP INTEGRATION:
    Once running, the server provides documentation access to AI assistants:
    - Real-time search across all your crawled projects
    - Semantic similarity matching for relevant content
    - Automatic context injection for better AI responses

  EXAMPLES:
    docbro serve                   # Start server (background)
    docbro serve -f                # Run in foreground for debugging
    docbro serve --port 8080       # Use custom port
    docbro serve --status          # Check if server is running

  CLIENT SETUP:
    Configure your AI assistant to connect to:
    - URL: http://localhost:9382 (or your custom host:port)
    - Protocol: MCP (Model Context Protocol)

  TROUBLESHOOTING:
    - Use --foreground to see real-time server logs
    - Check --status to verify server is responding
    - Ensure no other service is using the port
    - Run 'docbro health' to verify system components

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

  The one-stop command for all DocBro setup operations. Choose between
  interactive menu (no flags) or specific operations with flags.

  OPERATIONS:
    --init         Initialize configuration and vector store
    --uninstall    Remove DocBro completely from your system
    --reset        Reset to fresh state (keeps or removes data)
    (no flags)     Interactive menu with guided setup

  QUICK SETUPS:
    docbro setup                           # Interactive menu with help
    docbro setup --init --auto             # Quick setup with defaults
    docbro setup --init --vector-store sqlite_vec  # Choose vector store

  VECTOR STORE OPTIONS:
    sqlite_vec     Local SQLite with vector extension (recommended)
    qdrant         Scalable vector database (requires Docker)

  UNINSTALL & RESET:
    docbro setup --uninstall --force       # Uninstall without confirmation
    docbro setup --uninstall --backup      # Create backup first
    docbro setup --reset --preserve-data   # Reset but keep projects
    docbro setup --uninstall --dry-run     # Preview what would be removed

  FLAGS:
    --force            Skip confirmation prompts
    --auto             Use default values (with --init)
    --non-interactive  Disable all interactive prompts
    --backup           Create backup before destructive operations
    --dry-run          Preview changes without applying them
    --preserve-data    Keep user projects during reset/uninstall

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

  Verify that your DocBro installation is working correctly by checking system
  requirements, external services, configuration, and projects.

  WHAT IS CHECKED:
    System       Python version, memory, disk space, permissions
    Services     Docker, Qdrant, Ollama, Git availability
    Config       Settings files, vector store configuration
    Projects     Individual project health and integrity

  CATEGORY OPTIONS:
    --system     System requirements only (Python, memory, disk)
    --services   External services only (Docker, Qdrant, Ollama, Git)
    --config     Configuration files only (settings, vector store)
    --projects   Project health only (requires existing projects)
    (default)    System + Services + Config (recommended)

  OUTPUT FORMATS:
    table        Human-readable table with status indicators (default)
    json         Machine-readable JSON for automation/scripts
    yaml         YAML format for configuration management tools

  PERFORMANCE OPTIONS:
    -v, --verbose       Include detailed diagnostic information
    -q, --quiet         Suppress progress indicators
    -t, --timeout N     Maximum check timeout (1-60 seconds, default: 15)
    -P, --parallel N    Parallel checks (1-8 workers, default: 4)

  EXAMPLES:
    docbro health                    # Complete health check (recommended)
    docbro health --system           # System requirements only
    docbro health --services         # External services only
    docbro health --format json     # JSON output for scripts
    docbro health --verbose          # Detailed diagnostic information
    docbro health --timeout 30      # Extended timeout for slow systems

  TROUBLESHOOTING:
    Run this command after installation or when experiencing issues.
    Use --verbose for detailed error information and suggested fixes.

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

#### upload
```
Usage: docbro upload [OPTIONS] COMMAND [ARGS]...

  Upload files to documentation projects.

  Run without arguments to launch interactive menu: docbro upload

  Or use the command directly: docbro upload files --project my-docs --source
  /path/to/files --type local

Options:
  --help  Show this message and exit.

Commands:
  files   Upload files to a project from various sources.
  status  Show upload operation status.
```

##### upload files
```
Usage: docbro upload files [OPTIONS]

  Upload files to a project from various sources.

  SOURCE TYPES:
    local      Local filesystem files and directories
    http       Download files from HTTP URLs
    https      Download files from HTTPS URLs
    ftp        Upload from FTP server
    sftp       Upload from SFTP/SSH server
    smb        Upload from SMB/CIFS network shares

  EXAMPLES:
    docbro upload files --project docs --source /path/to/files --type local
    docbro upload files --project docs --source https://example.com/file.pdf --type https
    docbro upload files --project docs --source ftp://server.com/docs --type ftp --username user

  CONFLICT RESOLUTION:
    ask        Prompt for each conflict (default)
    skip       Skip conflicting files
    overwrite  Overwrite existing files

Options:
  -p, --project TEXT              Target project name  [required]
  -sr, --source TEXT              Source path/URL  [required]
  -t, --type [local|ftp|sftp|smb|http|https]
                                  Source type  [required]
  -u, --username TEXT             Authentication username
  -r, --recursive                 Recursive directory upload
  -e, --exclude TEXT              Exclude patterns
  -dr, --dry-run                  Show what would be uploaded
  -o, --overwrite [ask|skip|overwrite]
                                  Conflict resolution strategy
  -pr, --progress                 Show progress bar
  --help                          Show this message and exit.
```

##### upload status
```
Usage: docbro upload status [OPTIONS]

  Show upload operation status.

  EXAMPLES:
    docbro upload status                    # Show all upload operations
    docbro upload status --project docs    # Show uploads for specific project
    docbro upload status --active          # Show only active uploads
    docbro upload status --operation id123 # Show specific operation

Options:
  -p, --project TEXT     Filter by project
  -op, --operation TEXT  Specific operation ID
  -a, --active           Show only active uploads
  --help                 Show this message and exit.
```