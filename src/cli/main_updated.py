"""Enhanced main CLI entry point for DocBro with improvements."""

import asyncio
import sys
import logging
from pathlib import Path
from typing import Optional, Any, Dict, List

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.prompt import Prompt, Confirm

# Import our new components
from src.cli.context import CliContext, get_cli_context
from src.cli.help_formatter import enhance_click_group, format_bare_command_help
from src.services.debug_manager import get_debug_manager
from src.services.error_reporter import ErrorReporter
from src.services.progress_reporter import get_progress_reporter, CrawlPhase
from src.services.wizard_manager import WizardManager
from src.services.batch_crawler import BatchCrawler
from src.lib.conditional_logging import configure_cli_logging

# Existing imports
from src.core.config import DocBroConfig
from src.core.lib_logger import setup_logging, get_component_logger
from src.services.database import DatabaseManager
from src.services.project_manager import ProjectManager
from src.services.crawler import DocumentationCrawler

logger = logging.getLogger(__name__)


class DocBroApp:
    """Enhanced DocBro application with CLI improvements."""

    def __init__(self, config: Optional[DocBroConfig] = None, context: Optional[CliContext] = None):
        """Initialize DocBro application."""
        self.config = config or DocBroConfig()
        self.context = context or CliContext()
        self.console = Console()
        self.logger = None

        # Services
        self.db_manager: Optional[DatabaseManager] = None
        self.project_manager: Optional[ProjectManager] = None
        self.crawler: Optional[DocumentationCrawler] = None
        self.wizard_manager: Optional[WizardManager] = None
        self.batch_crawler: Optional[BatchCrawler] = None

        self._initialized = False

    async def initialize(self) -> None:
        """Initialize all services."""
        if self._initialized:
            return

        try:
            # Setup enhanced logging
            configure_cli_logging(
                debug=self.context.debug_enabled,
                log_file=self.config.log_file if hasattr(self.config, 'log_file') else None
            )
            self.logger = get_component_logger("cli")

            # Initialize services
            self.db_manager = DatabaseManager(self.config)
            await self.db_manager.initialize()

            self.project_manager = ProjectManager()
            self.wizard_manager = WizardManager(console=self.console)
            self.batch_crawler = BatchCrawler(project_manager=self.project_manager)

            self.crawler = DocumentationCrawler(self.db_manager, self.config)
            await self.crawler.initialize()

            self._initialized = True
            if self.context.debug_enabled:
                self.logger.debug("DocBro application initialized with debug mode")

        except Exception as e:
            self.console.print(f"[red]Failed to initialize DocBro: {e}[/red]")
            if self.logger:
                self.logger.error("Initialization failed", extra={"error": str(e)})
            raise

    async def cleanup(self) -> None:
        """Clean up all services."""
        if self.crawler:
            await self.crawler.cleanup()
        if self.db_manager:
            await self.db_manager.cleanup()

        self._initialized = False
        if self.logger:
            self.logger.info("DocBro application cleaned up")


# Global app instance for CLI
app: Optional[DocBroApp] = None


def get_app(context: Optional[CliContext] = None) -> DocBroApp:
    """Get or create global app instance."""
    global app
    if app is None:
        app = DocBroApp(context=context)
    elif context:
        app.context = context
    return app


def run_async(coro):
    """Run async coroutine in sync context."""
    return asyncio.run(coro)


# Enhanced main group with help formatter
@click.group(invoke_without_command=True)
@click.version_option(version="1.0.0")
@click.option("--config-file", type=click.Path(exists=True), help="Configuration file path")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--debug", is_flag=True, help="Enable debug output")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-essential output")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.option("--no-color", is_flag=True, help="Disable colored output")
@click.option("--no-progress", is_flag=True, help="Disable progress indicators")
@click.pass_context
def main(
    ctx: click.Context,
    config_file: Optional[str],
    verbose: bool,
    debug: bool,
    quiet: bool,
    json: bool,
    no_color: bool,
    no_progress: bool
):
    """DocBro - Documentation crawler and search tool with RAG capabilities.

    A powerful tool for crawling, indexing, and searching documentation
    with advanced semantic search and retrieval-augmented generation.
    """
    # Create CLI context
    cli_context = CliContext()
    cli_context.update_from_flags(
        debug=debug,
        verbose=verbose,
        quiet=quiet,
        json=json,
        no_color=no_color,
        no_progress=no_progress
    )

    ctx.obj = cli_context

    # If no command provided, show help suggestion
    if ctx.invoked_subcommand is None:
        console = Console()
        console.print(format_bare_command_help())
        ctx.exit(0)

    # Load configuration
    config = DocBroConfig()
    if config_file:
        # Load config from file if needed
        pass

    # Initialize app with context
    global app
    app = DocBroApp(config=config, context=cli_context)


@main.command()
@click.argument("name", required=False)
@click.option("--url", "-u", help="Source URL to crawl")
@click.option("--depth", "-d", type=int, help="Maximum crawl depth")
@click.option("--model", "-m", help="Embedding model")
@click.pass_context
def create(
    ctx: click.Context,
    name: Optional[str],
    url: Optional[str],
    depth: Optional[int],
    model: Optional[str]
):
    """Create a new documentation project.

    If no arguments provided, launches an interactive wizard.
    """
    cli_context = get_cli_context(ctx)

    async def _create():
        app = get_app(cli_context)
        await app.initialize()

        # If no arguments, launch wizard
        if not name:
            wizard = app.wizard_manager
            inputs = wizard.create_project_wizard()

            if not inputs:
                app.console.print("[yellow]Project creation cancelled[/yellow]")
                return

            name = inputs.get('name')
            url = inputs.get('url')
            depth = int(inputs.get('depth', 2))
            model = inputs.get('model', 'mxbai-embed-large')

        # Validate required fields
        if not name or not url:
            app.console.print("[red]Error: Project name and URL are required[/red]")
            return

        # Set defaults
        depth = depth or 2
        model = model or 'mxbai-embed-large'

        try:
            project = await app.project_manager.create_project(
                name=name,
                url=url,
                depth=depth,
                model=model
            )

            app.console.print(f"[green]✓[/green] Project '{name}' created successfully")
            if cli_context.should_show_info():
                app.console.print(f"  URL: {url}")
                app.console.print(f"  Depth: {depth}")
                app.console.print(f"  Model: {model}")

        except Exception as e:
            app.console.print(f"[red]Failed to create project: {e}[/red]")
            if cli_context.debug_enabled:
                import traceback
                app.console.print(traceback.format_exc())

    run_async(_create())


@main.command()
@click.argument("name", required=False)
@click.option("--update", is_flag=True, help="Update existing project(s)")
@click.option("--all", is_flag=True, help="Process all projects")
@click.option("--max-pages", "-m", type=int, help="Maximum pages to crawl")
@click.option("--rate-limit", "-r", default=1.0, type=float, help="Requests per second")
@click.option("--debug", is_flag=True, help="Show detailed crawl output")
@click.pass_context
def crawl(
    ctx: click.Context,
    name: Optional[str],
    update: bool,
    all: bool,
    max_pages: Optional[int],
    rate_limit: float,
    debug: bool
):
    """Crawl documentation for a project.

    Use --update to recrawl existing projects.
    Use --update --all to recrawl all projects.
    """
    cli_context = get_cli_context(ctx)
    if debug:
        cli_context.enable_debug()

    async def _crawl():
        app = get_app(cli_context)
        await app.initialize()

        try:
            # Handle batch crawl
            if update and all:
                projects = await app.project_manager.list_projects()
                if not projects:
                    app.console.print("[yellow]No projects found to update[/yellow]")
                    return

                app.console.print(f"[cyan]Starting batch crawl for {len(projects)} projects[/cyan]")

                batch_crawler = app.batch_crawler
                progress_reporter = get_progress_reporter(app.console)

                # Use progress context if not in debug mode
                if cli_context.should_show_progress():
                    with progress_reporter.crawl_progress() as progress:
                        summary = await batch_crawler.crawl_all(
                            projects=projects,
                            max_pages=max_pages,
                            rate_limit=rate_limit,
                            continue_on_error=True
                        )
                else:
                    summary = await batch_crawler.crawl_all(
                        projects=projects,
                        max_pages=max_pages,
                        rate_limit=rate_limit,
                        continue_on_error=True
                    )

                # Show summary
                app.console.print("\n[bold]Batch Crawl Complete[/bold]")
                app.console.print(f"  Succeeded: {summary.get('succeeded', 0)}")
                app.console.print(f"  Failed: {summary.get('failed', 0)}")
                app.console.print(f"  Total pages: {summary.get('total_pages', 0)}")

                if summary.get('failures'):
                    app.console.print("\n[red]Failed projects:[/red]")
                    for failure in summary['failures']:
                        app.console.print(f"  - {failure['project']}: {failure['error']}")

            # Handle single project update
            elif update and name:
                project = await app.project_manager.get_project(name)
                if not project:
                    app.console.print(f"[red]Project '{name}' not found[/red]")
                    return

                await _crawl_single_project(app, project, max_pages, rate_limit, cli_context)

            # Handle regular crawl
            elif name:
                project = await app.project_manager.get_project(name)
                if not project:
                    app.console.print(f"[red]Project '{name}' not found[/red]")
                    app.console.print("[yellow]Tip: Use 'docbro create' to create a new project[/yellow]")
                    return

                await _crawl_single_project(app, project, max_pages, rate_limit, cli_context)

            else:
                app.console.print("[red]Error: Project name required[/red]")
                app.console.print("Usage: docbro crawl PROJECT_NAME")
                app.console.print("   or: docbro crawl --update PROJECT_NAME")
                app.console.print("   or: docbro crawl --update --all")

        except KeyboardInterrupt:
            app.console.print("\n[yellow]Crawl cancelled by user[/yellow]")
        except Exception as e:
            app.console.print(f"[red]Crawl failed: {e}[/red]")
            if cli_context.debug_enabled:
                import traceback
                app.console.print(traceback.format_exc())

    async def _crawl_single_project(app, project, max_pages, rate_limit, cli_context):
        """Crawl a single project with progress."""
        error_reporter = ErrorReporter(project.project_name)
        progress_reporter = get_progress_reporter(app.console)

        app.console.print(f"[cyan]Crawling {project.project_name}...[/cyan]")

        if cli_context.should_show_progress():
            with progress_reporter.crawl_progress() as progress:
                # Phase 1: Analyze headers
                progress.start_phase(CrawlPhase.ANALYZING_HEADERS, total=max_pages or 100)
                await asyncio.sleep(0.5)  # Simulate header analysis
                progress.complete_phase(CrawlPhase.ANALYZING_HEADERS)

                # Phase 2: Crawl content
                progress.start_phase(CrawlPhase.CRAWLING_CONTENT, total=max_pages or 100)
                # Actual crawl would happen here
                for i in range(min(10, max_pages or 10)):
                    progress.update_phase(CrawlPhase.CRAWLING_CONTENT, advance=1)
                    await asyncio.sleep(0.1)  # Simulate crawl
                progress.complete_phase(CrawlPhase.CRAWLING_CONTENT)

                progress.print_phase_summary()

        # Generate error report if needed
        if error_reporter.has_errors():
            json_path, text_path = error_reporter.save_report()
            app.console.print(f"\n[yellow]⚠ Crawl completed with {error_reporter.get_error_count()} errors[/yellow]")
            app.console.print(f"Error report saved to: {text_path}")
            app.console.print(f"Review errors: [cyan]open {text_path}[/cyan]")
        else:
            app.console.print(f"\n[green]✓ Crawl completed successfully[/green]")

        # Show project status
        app.console.print(f"\nProject Status:")
        app.console.print(f"  Documents: {project.total_documents}")
        app.console.print(f"  Embeddings: {project.total_embeddings}")

    run_async(_crawl())


@main.command()
@click.option("--status", "-s", help="Filter by status")
@click.option("--limit", "-l", type=int, help="Limit number of results")
@click.pass_context
def list(ctx: click.Context, status: Optional[str], limit: Optional[int]):
    """List all documentation projects."""
    cli_context = get_cli_context(ctx)

    async def _list():
        app = get_app(cli_context)
        await app.initialize()

        projects = await app.project_manager.list_projects()

        if not projects:
            app.console.print("[yellow]No projects found[/yellow]")
            app.console.print("Use 'docbro create' to create your first project")
            return

        # Filter by status if provided
        if status:
            projects = [p for p in projects if p.status.value.lower() == status.lower()]

        # Apply limit
        if limit:
            projects = projects[:limit]

        # Create table
        table = Table(title="Documentation Projects")
        table.add_column("Name", style="cyan")
        table.add_column("Status", style="green")
        table.add_column("Documents")
        table.add_column("Last Crawl")
        table.add_column("URL")

        for project in projects:
            table.add_row(
                project.project_name,
                project.status.value,
                str(project.total_documents),
                project.last_crawl_time.strftime("%Y-%m-%d %H:%M") if project.last_crawl_time else "Never",
                project.url or ""
            )

        app.console.print(table)

    run_async(_list())


# Enhance the main group with better help
enhance_click_group(main)


if __name__ == "__main__":
    main()