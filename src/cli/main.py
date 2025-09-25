"""Main CLI entry point for DocBro."""

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Any, Dict, List

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Confirm

# Optional uvloop for better performance
try:
    import uvloop
    UVLOOP_AVAILABLE = True
except ImportError:
    UVLOOP_AVAILABLE = False

from src.core.config import DocBroConfig
from src.core.lib_logger import setup_logging, get_component_logger
from src.services.database import DatabaseManager
from src.services.vector_store import VectorStoreService
from src.services.embeddings import EmbeddingService
from src.services.rag import RAGSearchService
from src.services.crawler import DocumentationCrawler
from src.services.setup import SetupWizardService
from src.services.config import ConfigService
from src.services.detection import ServiceDetectionService
from src.version import __version__

# Auto-setup imports
from src.services.installation_wizard import InstallationWizardService
from src.models.installation import InstallationRequest


class DocBroApp:
    """Main DocBro application."""

    def __init__(self, config: Optional[DocBroConfig] = None):
        """Initialize DocBro application."""
        self.config = config or DocBroConfig()
        self.console = Console()
        self.logger = None

        # Services
        self.db_manager: Optional[DatabaseManager] = None
        self.vector_store: Optional[VectorStoreService] = None
        self.embedding_service: Optional[EmbeddingService] = None
        self.rag_service: Optional[RAGSearchService] = None
        self.crawler: Optional[DocumentationCrawler] = None

        self._initialized = False

    async def initialize(self, debug: bool = False) -> None:
        """Initialize all services."""
        if self._initialized:
            return

        try:
            # Setup logging with debug override
            if debug:
                self.config.debug = True
                self.config.log_level = "DEBUG"
            setup_logging(self.config)
            self.logger = get_component_logger("cli")

            # Initialize services
            self.db_manager = DatabaseManager(self.config)
            await self.db_manager.initialize()

            self.vector_store = VectorStoreService(self.config)
            await self.vector_store.initialize()

            self.embedding_service = EmbeddingService(self.config)
            await self.embedding_service.initialize()

            self.rag_service = RAGSearchService(
                self.vector_store,
                self.embedding_service,
                self.config
            )

            self.crawler = DocumentationCrawler(self.db_manager, self.config)
            await self.crawler.initialize()

            self._initialized = True
            self.logger.info("DocBro application initialized")

        except Exception as e:
            self.console.print(f"[red]Failed to initialize DocBro: {e}[/red]")
            if self.logger:
                self.logger.error("Initialization failed", extra={"error": str(e)})
            raise

    async def cleanup(self) -> None:
        """Clean up all services."""
        if self.crawler:
            await self.crawler.cleanup()
        if self.embedding_service:
            await self.embedding_service.cleanup()
        if self.vector_store:
            await self.vector_store.cleanup()
        if self.db_manager:
            await self.db_manager.cleanup()

        self._initialized = False
        if self.logger:
            self.logger.info("DocBro application cleaned up")

    def invoke_command(self, args: List[str]) -> Any:
        """Invoke CLI command for testing."""
        # This is a simplified implementation for testing
        # In a full implementation, you would use Click's testing utilities
        raise NotImplementedError("CLI testing interface not implemented yet")


# Global app instance for CLI
app: Optional[DocBroApp] = None


def get_app() -> DocBroApp:
    """Get or create global app instance."""
    global app
    if app is None:
        app = DocBroApp()
    return app


def _is_first_time_installation() -> bool:
    """Check if this is a first-time installation.

    Returns:
        True if no previous installation context exists
    """
    try:
        config_service = ConfigService()

        # Check for existing installation context
        context = config_service.load_installation_context()
        if context:
            return False

        # Check for any existing configuration
        config_dir = config_service.config_dir
        if config_dir.exists():
            # Look for any configuration files
            config_files = list(config_dir.glob("*.json"))
            if config_files:
                return False

        return True
    except Exception:
        # If we can't determine, assume first time for safety
        return True


def _detect_uv_installation() -> bool:
    """Detect if this is running from a UV tool installation.

    Returns:
        True if this appears to be a UV tool installation
    """
    import os
    import sys
    from pathlib import Path

    # Check for UV environment variables
    if "UV_TOOL_DIR" in os.environ or "UVX_ROOT" in os.environ:
        return True

    # Check if running from UV virtual environment
    current_executable = Path(sys.executable)
    if "uv" in str(current_executable).lower():
        return True

    # Check if docbro is in a UV-managed location
    try:
        import shutil
        docbro_path = shutil.which("docbro")
        if docbro_path:
            path_str = str(Path(docbro_path))
            if ".local" in path_str and "uv" in path_str.lower():
                return True
    except Exception:
        pass

    return False


async def _run_auto_setup() -> bool:
    """Run the installation wizard automatically for first-time UV installations.

    Returns:
        True if setup completed successfully, False otherwise
    """
    console = Console()

    try:
        console.print("\n[cyan]🚀 Welcome to DocBro![/cyan]")
        console.print("[dim]Detected first-time installation - running automatic setup...[/dim]")

        # Set environment variable to signal auto-setup mode
        import os
        os.environ["DOCBRO_AUTO_SETUP"] = "true"

        installation_wizard = InstallationWizardService()

        # Create installation request for auto-setup
        request = InstallationRequest(
            install_method="uv-tool",
            version=__version__,
            user_preferences={
                "auto_setup": True,
                "install_source": "uv-auto-setup"
            }
        )

        # Start installation process
        response = await installation_wizard.start_installation(request)

        if response.status == "started":
            # Wait for completion with timeout
            max_wait_time = 180  # 3 minutes
            wait_interval = 2  # 2 seconds
            waited = 0

            while waited < max_wait_time:
                await asyncio.sleep(wait_interval)
                waited += wait_interval

                status_info = installation_wizard.get_installation_status()

                if status_info["status"] == "complete":
                    console.print("[green]✅ Auto-setup completed successfully![/green]")
                    console.print("[dim]DocBro is now ready to use.[/dim]\n")
                    return True
                elif status_info["status"] == "error":
                    console.print(f"[yellow]⚠ Auto-setup encountered issues: {status_info.get('message', 'Unknown error')}[/yellow]")
                    console.print("[dim]You can run 'docbro setup' manually to configure services.[/dim]\n")
                    return False

            # Timeout reached
            console.print("[yellow]⚠ Auto-setup timed out.[/yellow]")
            console.print("[dim]You can run 'docbro setup' manually to configure services.[/dim]\n")
            return False
        else:
            console.print(f"[yellow]⚠ Failed to start auto-setup: {response.message}[/yellow]")
            console.print("[dim]You can run 'docbro setup' manually to configure services.[/dim]\n")
            return False

    except Exception as e:
        console.print(f"[yellow]⚠ Auto-setup failed: {str(e)}[/yellow]")
        console.print("[dim]You can run 'docbro setup' manually to configure services.[/dim]\n")
        return False


def _should_run_auto_setup() -> bool:
    """Determine if auto-setup should run.

    Returns:
        True if auto-setup should be triggered
    """
    import os
    import sys

    # Skip if explicitly disabled
    if os.environ.get("DOCBRO_SKIP_AUTO_SETUP", "").lower() in ("1", "true", "yes"):
        return False

    # Skip in CI/automated environments
    ci_indicators = [
        "CI", "CONTINUOUS_INTEGRATION", "BUILD_NUMBER",
        "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL"
    ]
    if any(var in os.environ for var in ci_indicators):
        return False

    # Skip if no TTY (non-interactive)
    if not sys.stdout.isatty():
        return False

    # Only run for first-time UV installations
    return _is_first_time_installation() and _detect_uv_installation()


def run_async(coro):
    """Run async coroutine in sync context."""
    if UVLOOP_AVAILABLE:
        try:
            uvloop.install()
        except Exception:
            pass

    return asyncio.run(coro)


@click.group(invoke_without_command=True)
@click.option("--version", "-v", is_flag=True, expose_value=False, is_eager=True, callback=lambda ctx, param, value: click.echo(__version__) or ctx.exit() if value else None, help="Show version and exit")
@click.option("--config-file", type=click.Path(exists=True), help="Configuration file path")
@click.option("--debug", is_flag=True, help="Enable debug output")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-essential output")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.option("--no-color", is_flag=True, help="Disable colored output")
@click.option("--no-progress", is_flag=True, help="Disable progress indicators")
@click.option("--health", is_flag=True, help="Show health check for all services")
@click.option("--skip-auto-setup", is_flag=True, help="Skip automatic setup for first-time installations")
@click.pass_context
def main(ctx: click.Context, config_file: Optional[str], debug: bool,
         quiet: bool, json: bool, no_color: bool, no_progress: bool, health: bool, skip_auto_setup: bool):
    """DocBro - Documentation crawler and search tool with RAG capabilities.

    Create projects, crawl documentation, and access content through MCP server integration.
    """
    ctx.ensure_object(dict)

    # Store all flags in context
    ctx.obj["config_file"] = config_file
    ctx.obj["debug"] = debug
    ctx.obj["quiet"] = quiet
    ctx.obj["json"] = json
    ctx.obj["no_color"] = no_color
    ctx.obj["no_progress"] = no_progress
    ctx.obj["health"] = health
    ctx.obj["skip_auto_setup"] = skip_auto_setup

    # Handle debug mode
    if debug:
        # Import and configure debug manager
        from src.services.debug_manager import DebugManager
        debug_mgr = DebugManager()
        debug_mgr.enable_debug()

    # Handle health check
    if health:
        run_async(_handle_health_check(json))
        ctx.exit(0)

    # Check for auto-setup before showing help or processing commands
    if not skip_auto_setup and _should_run_auto_setup():
        # Run auto-setup asynchronously
        run_async(_run_auto_setup())

    # Show help suggestion when no command provided
    if ctx.invoked_subcommand is None:
        console = Console()
        console.print("DocBro - Documentation crawler and search tool\n")
        console.print("No command specified. Try 'docbro --help' for available commands.\n")
        console.print("Quick start:")
        console.print("  docbro setup                  Interactive setup wizard")
        console.print("  docbro create myproject -u URL   Create a documentation project")
        console.print("  docbro crawl myproject        Crawl and index documentation")
        console.print("  docbro list                   List all projects")
        console.print("  docbro serve                  Start MCP server (port 9382)")
        console.print("\nAdditional commands:")
        console.print("  docbro remove <project>       Remove a project")
        console.print("  docbro uninstall              Uninstall DocBro completely")
        console.print("  docbro --health               Check service health status")
        console.print("  docbro --help                Show all available commands")
        ctx.exit(0)

    # Initialize app
    global app
    config = DocBroConfig()
    if config_file:
        # Load config from file if needed
        pass

    # Apply debug flag to config
    if debug:
        config.debug = True
        config.log_level = "DEBUG"

    app = DocBroApp(config)


async def _handle_health_check(output_json: bool) -> None:
    """Handle health check command."""
    from src.services.detection import ServiceDetectionService

    console = Console()
    detection_service = ServiceDetectionService()

    try:
        # Check all services
        statuses = await detection_service.check_all_services()

        if output_json:
            import json
            health_data = {
                "version": __version__,
                "services": {}
            }
            for name, status in statuses.items():
                health_data["services"][name] = {
                    "available": status.available,
                    "version": status.version,
                    "status": "healthy" if status.available else "unhealthy",
                    "error": status.error_message if not status.available else None
                }
            print(json.dumps(health_data, indent=2))
            return

        console.print(f"📊 DocBro Health Check (v{__version__})\n")

        # Create health table
        table = Table(title="Service Health Status")
        table.add_column("Service", style="cyan", no_wrap=True)
        table.add_column("Status", style="green")
        table.add_column("Version", style="yellow")
        table.add_column("Details", style="dim")

        overall_healthy = True

        for name, status in statuses.items():
            status_text = "✅ Healthy" if status.available else "❌ Unhealthy"
            if not status.available:
                overall_healthy = False

            version_text = status.version or "unknown"
            details = status.error_message if not status.available else "OK"

            table.add_row(
                name.title().replace('_', ' '),
                status_text,
                version_text,
                details[:50] + "..." if len(details) > 50 else details
            )

        console.print(table)

        # Overall status
        if overall_healthy:
            console.print("\n✅ [bold green]All services are healthy[/bold green]")
        else:
            console.print("\n⚠️  [bold yellow]Some services need attention[/bold yellow]")
            console.print("💡 Run [cyan]docbro setup[/cyan] to fix issues")

    except Exception as e:
        console.print(f"❌ Health check failed: {e}")
        raise


@main.command()
@click.argument("name", required=False)
@click.option("--url", "-u", help="Source URL to crawl (quote URLs with special characters)")
@click.option("--depth", "-d", default=2, type=int, help="Maximum crawl depth")
@click.option("--model", "-m", default="mxbai-embed-large", help="Embedding model")
@click.pass_context
def create(ctx: click.Context, name: Optional[str], url: Optional[str], depth: int, model: str):
    """Create a new documentation project.

    Note: URLs with special characters (?, &, etc.) must be quoted:
    docbro create myproject -u "https://example.com?param=value"

    Run without arguments to launch interactive wizard:
    docbro create
    """
    async def _create():
        app = get_app()

        # If no name provided, launch interactive wizard
        if not name:
            from src.services.wizard_manager import WizardManager
            wizard = WizardManager()

            project_config = await wizard.create_project_wizard()

            if not project_config:
                app.console.print("[yellow]Wizard cancelled[/yellow]")
                return

            # Use wizard results
            name_to_use = project_config["name"]
            url_to_use = project_config["url"]
            depth_to_use = project_config.get("depth", depth)
            model_to_use = project_config.get("model", model)
        else:
            # Require URL if name is provided
            if not url:
                raise click.ClickException("URL is required when providing project name")
            name_to_use = name
            url_to_use = url
            depth_to_use = depth
            model_to_use = model

        await app.initialize()

        try:
            # Check if URL looks suspicious (might have been affected by shell glob expansion)
            if url_to_use and not url_to_use.startswith(('http://', 'https://', 'file://')):
                app.console.print("[yellow]⚠ Warning: URL doesn't start with http://, https://, or file://[/yellow]")
                app.console.print("[yellow]  If your URL contains special characters (?, &, *, [, ]), you must quote it:[/yellow]")
                app.console.print('[yellow]  Example: docbro create myproject -u "https://example.com?param=value"[/yellow]')

            # Additional check for common shell expansion issues
            import os
            if url_to_use and os.path.exists(url_to_use) and not url_to_use.startswith('file://'):
                app.console.print("[yellow]⚠ Warning: URL appears to be a local file path.[/yellow]")
                app.console.print("[yellow]  This might be due to shell glob expansion of special characters.[/yellow]")
                app.console.print('[yellow]  Try quoting your URL: docbro create myproject -u "YOUR_URL_HERE"[/yellow]')

            project = await app.db_manager.create_project(
                name=name_to_use,
                source_url=url_to_use,
                crawl_depth=depth_to_use,
                embedding_model=model_to_use
            )

            app.console.print(f"[green]✓[/green] Project '{name_to_use}' created successfully")
            app.console.print(f"  ID: {project.id}")
            app.console.print(f"  URL: {project.source_url}")
            app.console.print(f"  Depth: {project.crawl_depth}")

        except Exception as e:
            # Check for common URL-related errors
            error_msg = str(e).lower()
            if 'invalid url' in error_msg or 'url' in error_msg:
                app.console.print("[yellow]Tip: If your URL contains special characters, make sure to quote it:[/yellow]")
                app.console.print('[yellow]     docbro create myproject -u "https://example.com?param=value"[/yellow]')
            app.console.print(f"[red]✗ Failed to create project: {e}[/red]")
            raise click.ClickException(str(e))
        finally:
            await app.cleanup()

    run_async(_create())


@main.command()
@click.option("--status", "-s", help="Filter by status")
@click.option("--limit", "-l", type=int, help="Limit number of results")
@click.pass_context
def list(ctx: click.Context, status: Optional[str], limit: Optional[int]):
    """List all documentation projects."""
    async def _list():
        app = get_app()
        await app.initialize()

        try:
            from src.models import ProjectStatus
            status_filter = None
            if status:
                try:
                    status_filter = ProjectStatus(status)
                except ValueError:
                    raise click.BadParameter(f"Invalid status: {status}")

            projects = await app.db_manager.list_projects(
                status=status_filter,
                limit=limit
            )

            if not projects:
                app.console.print("No projects found.")
                return

            # Create table
            table = Table(title="Documentation Projects")
            table.add_column("Name", style="cyan")
            table.add_column("URL", style="blue")
            table.add_column("Status", style="green")
            table.add_column("Pages", justify="right")
            table.add_column("Last Crawl", style="dim")

            for project in projects:
                last_crawl = (
                    project.last_crawl_at.strftime("%Y-%m-%d %H:%M")
                    if project.last_crawl_at else "Never"
                )

                table.add_row(
                    project.name,
                    project.source_url,
                    project.status,
                    str(project.total_pages),
                    last_crawl
                )

            app.console.print(table)

        except Exception as e:
            app.console.print(f"[red]✗ Failed to list projects: {e}[/red]")
            raise click.ClickException(str(e))
        finally:
            await app.cleanup()

    run_async(_list())


@main.command()
@click.argument("name", required=False)
@click.option("--max-pages", "-m", type=int, help="Maximum pages to crawl")
@click.option("--rate-limit", "-r", default=1.0, type=float, help="Requests per second")
@click.option("--update", is_flag=True, help="Update existing project(s)")
@click.option("--all", is_flag=True, help="Process all projects")
@click.option("--debug", is_flag=True, help="Show detailed crawl output")
@click.pass_context
def crawl(ctx: click.Context, name: Optional[str], max_pages: Optional[int],
         rate_limit: float, update: bool, all: bool, debug: bool):
    """Start crawling a project.

    Examples:
      docbro crawl my-project                  # Crawl a specific project
      docbro crawl --update my-project        # Update an existing project
      docbro crawl --update --all             # Update all projects
    """
    async def _crawl():
        app = get_app()
        await app.initialize()

        # Handle batch operations
        if all:
            if not update:
                raise click.ClickException("--all requires --update flag")

            from src.services.batch_crawler import BatchCrawler
            from src.services.progress_reporter import ProgressReporter

            try:
                # Get all projects
                projects = await app.db_manager.list_projects()
                if not projects:
                    app.console.print("No projects found.")
                    return

                app.console.print(f"Starting batch crawl for {len(projects)} projects\n")

                # Use batch crawler
                batch_crawler = BatchCrawler()

                # Process each project sequentially
                results = await batch_crawler.crawl_all(
                    projects=projects,
                    max_pages=max_pages,
                    rate_limit=rate_limit,
                    continue_on_error=True,
                    progress_reporter=None
                )

                # Show summary
                app.console.print("\n[bold]Batch Crawl Complete[/bold]")
                app.console.print(f"  Succeeded: {results['succeeded']}")
                app.console.print(f"  Failed: {results['failed']}")
                if 'total_pages' in results:
                    app.console.print(f"  Total pages: {results['total_pages']}")

                if results.get('failures'):
                    app.console.print("\n[yellow]Failed projects:[/yellow]")
                    for failure in results['failures']:
                        app.console.print(f"  - {failure['project']}: {failure['error']}")

            except Exception as e:
                app.console.print(f"[red]✗ Batch crawl failed: {e}[/red]")
                raise click.ClickException(str(e))
            finally:
                await app.cleanup()
            return

        # Single project crawl
        if not name:
            raise click.ClickException("Project name required (or use --all for batch)")

        try:
            project = await app.db_manager.get_project_by_name(name)
            if not project:
                raise click.ClickException(f"Project '{name}' not found")

            # Use simple progress display
            from src.services.crawl_progress import CrawlProgressDisplay
            from src.services.error_reporter import ErrorReporter

            error_reporter = ErrorReporter(project_name=name)

            if not debug and not ctx.obj.get("no_progress"):
                # Use the new crawl progress display
                progress_display = CrawlProgressDisplay(
                    project_name=name,
                    max_depth=project.crawl_depth,
                    max_pages=max_pages
                )

                with progress_display:
                    # Start crawl
                    session = await app.crawler.start_crawl(
                        project_id=project.id,
                        rate_limit=rate_limit,
                        max_pages=max_pages,
                        progress_display=progress_display,
                        error_reporter=error_reporter
                    )

                    # Wait for completion
                    while True:
                        await asyncio.sleep(1.0)
                        session = await app.db_manager.get_crawl_session(session.id)
                        if not session or session.is_completed():
                            break
            else:
                # Debug mode or no progress - simple output
                session = await app.crawler.start_crawl(
                    project_id=project.id,
                    rate_limit=rate_limit,
                    max_pages=max_pages,
                    progress_display=None,
                    error_reporter=error_reporter
                )

                if debug:
                    app.console.print(f"[green]✓[/green] Crawl started for project '{name}'")
                    app.console.print(f"  Session ID: {session.id}")

                # Wait for completion with periodic status updates
                while True:
                    await asyncio.sleep(2.0)
                    session = await app.db_manager.get_crawl_session(session.id)
                    if not session:
                        break

                    if debug:
                        app.console.print(f"[cyan]Status: Pages={session.pages_crawled}, Errors={session.error_count}")

                    if session.is_completed():
                        break

            # Final status
            if session:
                # Check for errors and save report if needed
                if error_reporter.has_errors():
                    json_path, text_path = error_reporter.save_report()
                    if session.pages_failed > 0:
                        app.console.print(f"\n⚠ Crawl completed with {session.pages_failed} errors")
                    else:
                        app.console.print(f"\n[green]✓[/green] Crawl completed")
                    app.console.print(f"Error report saved to: {text_path}")
                    app.console.print(f"Review errors: open {text_path}")
                else:
                    app.console.print(f"\n[green]✓[/green] Crawl completed successfully")

                app.console.print(f"  Pages crawled: {session.pages_crawled}")
                app.console.print(f"  Pages failed: {session.pages_failed}")
                app.console.print(f"  Duration: {session.get_duration():.1f}s")

                # Update project statistics
                try:
                    await app.db_manager.update_project_statistics(
                        project.id,
                        total_pages=session.pages_crawled,
                        successful_pages=session.pages_crawled - session.pages_failed,
                        failed_pages=session.pages_failed,
                        last_crawl_at=session.completed_at or datetime.utcnow()
                    )
                except Exception as e:
                    app.console.print(f"[yellow]⚠ Warning: Failed to update project statistics: {e}[/yellow]")

                # Index crawled pages for search
                indexed_chunks_count = 0
                if session.pages_crawled > 0:
                    from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

                    app.console.print("\n[cyan]Indexing pages for search...[/cyan]")

                    # Get crawled pages
                    pages = await app.db_manager.get_project_pages(project.id)

                    # Convert to documents for indexing
                    documents = [
                        {
                            "id": page.id,
                            "title": page.title or "Untitled",
                            "content": page.content_text or "",
                            "url": page.url,
                            "project": project.name,
                            "project_id": project.id
                        }
                        for page in pages
                        if page.content_text
                    ]
                    if documents:
                        collection_name = f"project_{project.id}"

                        # Progress tracking variables
                        embedding_task = None
                        progress = None

                        def progress_callback(event_type: str, data: dict):
                            nonlocal embedding_task, progress, indexed_chunks_count

                            if event_type == "indexing_started":
                                app.console.print(f"[cyan]Processing {data['total_documents']} documents into ~{data['estimated_chunks']} chunks[/cyan]")
                                progress = Progress(
                                    SpinnerColumn(),
                                    TextColumn("[progress.description]{task.description}"),
                                    BarColumn(),
                                    TaskProgressColumn(),
                                    TimeElapsedColumn(),
                                    console=app.console
                                )
                                progress.start()
                                embedding_task = progress.add_task(
                                    "Creating embeddings...",
                                    total=data['estimated_chunks']
                                )

                            elif event_type == "embedding_progress":
                                if progress and embedding_task is not None:
                                    progress.update(
                                        embedding_task,
                                        completed=data['current_chunk'],
                                        description=f"Embedding '{data['document_title'][:30]}...' ({data['current_document']}/{data['total_documents']})"
                                    )

                            elif event_type == "storing_embeddings":
                                if progress and embedding_task is not None:
                                    progress.update(
                                        embedding_task,
                                        description=f"Storing {data['total_embeddings']} embeddings to vector database..."
                                    )

                            elif event_type == "indexing_completed":
                                if progress:
                                    progress.stop()
                                indexed_chunks_count = data['chunks_indexed']
                                app.console.print(f"[green]✓[/green] Successfully indexed {data['chunks_indexed']} chunks from {data['original_documents']} documents")

                            elif event_type == "indexing_failed":
                                if progress:
                                    progress.stop()
                                app.console.print(f"[red]✗[/red] Indexing failed: {data['error']}")

                        try:
                            indexed = await app.rag_service.index_documents(
                                collection_name, documents, progress_callback=progress_callback
                            )

                        except Exception as e:
                            if progress:
                                progress.stop()
                            app.console.print(f"[red]✗[/red] Indexing failed: {e}")
                            raise

            # Final completion summary
            app.console.print("\n" + "="*60)
            app.console.print("[bold green]🎉 CRAWL AND INDEXING COMPLETED SUCCESSFULLY 🎉[/bold green]")
            app.console.print("="*60)

            if session:
                # Calculate final statistics
                total_time = session.get_duration()
                success_rate = ((session.pages_crawled - session.pages_failed) / session.pages_crawled * 100) if session.pages_crawled > 0 else 0

                app.console.print(f"[bold]Project:[/bold] {name}")
                app.console.print(f"[bold]Duration:[/bold] {total_time:.1f}s")
                app.console.print(f"[bold]Pages Crawled:[/bold] {session.pages_crawled}")
                app.console.print(f"[bold]Pages Failed:[/bold] {session.pages_failed}")
                app.console.print(f"[bold]Success Rate:[/bold] {success_rate:.1f}%")

                if session.pages_crawled > 0:
                    # Get final document count
                    final_pages = await app.db_manager.get_project_pages(project.id)
                    documents_with_content = [p for p in final_pages if p.content_text]

                    app.console.print(f"[bold]Documents Indexed:[/bold] {len(documents_with_content)}")
                    if indexed_chunks_count > 0:
                        app.console.print(f"[bold]Chunks Created:[/bold] {indexed_chunks_count}")

                app.console.print(f"[bold]Status:[/bold] [green]Ready for search[/green]")

            app.console.print("="*60)
            app.console.print(f"[dim]Project '{name}' is now ready for use[/dim]")
            app.console.print()

        except Exception as e:
            app.console.print(f"[red]✗ Failed during crawl: {e}[/red]")
            raise click.ClickException(str(e))
        finally:
            await app.cleanup()

    run_async(_crawl())




@main.command()
@click.argument("name")
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@click.pass_context
def remove(ctx: click.Context, name: str, confirm: bool):
    """Remove a project and all its data."""
    async def _remove():
        app = get_app()
        await app.initialize()

        try:
            project = await app.db_manager.get_project_by_name(name)
            if not project:
                raise click.ClickException(f"Project '{name}' not found")

            if not confirm:
                if not Confirm.ask(f"Are you sure you want to remove project '{name}'?"):
                    app.console.print("Operation cancelled.")
                    return

            # Clean up project data
            cleanup_result = await app.db_manager.cleanup_project(project.id)

            if cleanup_result["success"]:
                app.console.print(f"[green]✓[/green] Project '{name}' removed successfully")
            else:
                error = cleanup_result.get("error", "Unknown error")
                raise click.ClickException(f"Failed to remove project: {error}")

        except Exception as e:
            app.console.print(f"[red]✗ Failed to remove project: {e}[/red]")
            raise click.ClickException(str(e))
        finally:
            await app.cleanup()

    run_async(_remove())


@main.command()
@click.option("--host", default="0.0.0.0", help="Server host")
@click.option("--port", default=9382, type=int, help="Server port")
@click.option("--foreground", "-f", is_flag=True, help="Run server in foreground")
@click.pass_context
def serve(ctx: click.Context, host: str, port: int, foreground: bool):
    """Start the MCP server for agent integration."""
    from src.services.mcp_server import run_mcp_server
    import subprocess
    import os
    import signal

    app = get_app()

    if foreground:
        # Run in foreground (original behavior)
        app.console.print(f"[green]Starting MCP server on {host}:{port}...[/green]")
        app.console.print("[dim]Press Ctrl+C to stop[/dim]\n")

        try:
            run_mcp_server(host=host, port=port, config=app.config)
        except KeyboardInterrupt:
            app.console.print("\n[yellow]Server stopped[/yellow]")
        except Exception as e:
            app.console.print(f"[red]✗ Server error: {e}[/red]")
            raise click.ClickException(str(e))
    else:
        # Run in background (default behavior)
        app.console.print(f"[green]✅ MCP server starting on {host}:{port}[/green]")

        # Fork the process to run in background
        pid = os.fork()
        if pid == 0:
            # Child process - redirect stdout/stderr to suppress INFO messages
            with open(os.devnull, 'w') as devnull:
                os.dup2(devnull.fileno(), 1)  # stdout
                os.dup2(devnull.fileno(), 2)  # stderr

            try:
                run_mcp_server(host=host, port=port, config=app.config)
            except Exception:
                pass
        else:
            # Parent process - just show status and exit
            app.console.print(f"[dim]Process ID: {pid}[/dim]")
            app.console.print(f"[dim]Use 'kill {pid}' to stop the server[/dim]")




# Import enhanced setup command
from .setup import setup as enhanced_setup

# Add the enhanced setup command to main CLI
main.add_command(enhanced_setup, name="setup")






# Import and register uninstall command
from .uninstall import uninstall
main.add_command(uninstall)


# Create an alias for backward compatibility with tests
cli = main

if __name__ == "__main__":
    main()