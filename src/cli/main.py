"""Main CLI entry point for DocBro."""

import asyncio
import sys
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

from ..lib.config import DocBroConfig
from ..lib.logging import setup_logging, get_component_logger
from ..services.database import DatabaseManager
from ..services.vector_store import VectorStoreService
from ..services.embeddings import EmbeddingService
from ..services.rag import RAGSearchService
from ..services.crawler import DocumentationCrawler


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

    async def initialize(self) -> None:
        """Initialize all services."""
        if self._initialized:
            return

        try:
            # Setup logging
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


def run_async(coro):
    """Run async coroutine in sync context."""
    if UVLOOP_AVAILABLE:
        try:
            uvloop.install()
        except Exception:
            pass

    return asyncio.run(coro)


@click.group()
@click.version_option(version="1.0.0")
@click.option("--config-file", type=click.Path(exists=True), help="Configuration file path")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.pass_context
def main(ctx: click.Context, config_file: Optional[str], verbose: bool):
    """DocBro - Documentation crawler and search tool."""
    ctx.ensure_object(dict)

    # Load configuration
    if config_file:
        ctx.obj["config_file"] = config_file

    ctx.obj["verbose"] = verbose

    # Initialize app
    global app
    config = DocBroConfig()
    if config_file:
        # Load config from file if needed
        pass

    app = DocBroApp(config)


@main.command()
@click.argument("name")
@click.option("--url", "-u", required=True, help="Source URL to crawl")
@click.option("--depth", "-d", default=2, type=int, help="Maximum crawl depth")
@click.option("--model", "-m", default="mxbai-embed-large", help="Embedding model")
@click.pass_context
def create(ctx: click.Context, name: str, url: str, depth: int, model: str):
    """Create a new documentation project."""
    async def _create():
        app = get_app()
        await app.initialize()

        try:
            project = await app.db_manager.create_project(
                name=name,
                source_url=url,
                crawl_depth=depth,
                embedding_model=model
            )

            app.console.print(f"[green]✓[/green] Project '{name}' created successfully")
            app.console.print(f"  ID: {project.id}")
            app.console.print(f"  URL: {project.source_url}")
            app.console.print(f"  Depth: {project.crawl_depth}")

        except Exception as e:
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
            from ..models import ProjectStatus
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
@click.argument("name")
@click.option("--max-pages", "-m", type=int, help="Maximum pages to crawl")
@click.option("--rate-limit", "-r", default=1.0, type=float, help="Requests per second")
@click.pass_context
def crawl(ctx: click.Context, name: str, max_pages: Optional[int], rate_limit: float):
    """Start crawling a project."""
    async def _crawl():
        app = get_app()
        await app.initialize()

        try:
            project = await app.db_manager.get_project_by_name(name)
            if not project:
                raise click.ClickException(f"Project '{name}' not found")

            # Start crawl with progress display
            with app.console.status(f"[yellow]Starting crawl for project '{name}'...[/yellow]"):
                session = await app.crawler.start_crawl(
                    project_id=project.id,
                    rate_limit=rate_limit,
                    max_pages=max_pages
                )

            app.console.print(f"[green]✓[/green] Crawl started for project '{name}'")
            app.console.print(f"  Session ID: {session.id}")
            app.console.print(f"  Status: {session.status}")

            # Show progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True
            ) as progress:
                task = progress.add_task("[cyan]Crawling...", total=None)

                # Wait for completion with periodic updates
                while True:
                    await asyncio.sleep(2.0)
                    # Give other tasks a chance to run
                    await asyncio.sleep(0)

                    # Get updated session
                    session = await app.db_manager.get_crawl_session(session.id)
                    if not session:
                        break

                    # Update progress description
                    progress.update(
                        task,
                        description=f"[cyan]Crawling... Pages: {session.pages_crawled}, Errors: {session.error_count}"
                    )

                    # Check if completed
                    if session.is_completed():
                        break

            # Final status
            if session:
                app.console.print(f"\n[green]✓[/green] Crawl completed")
                app.console.print(f"  Pages crawled: {session.pages_crawled}")
                app.console.print(f"  Pages failed: {session.pages_failed}")
                app.console.print(f"  Duration: {session.get_duration():.1f}s")

                # Index crawled pages for search
                if session.pages_crawled > 0:
                    app.console.print("\n[yellow]Indexing pages for search...[/yellow]")

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
                        indexed = await app.rag_service.index_documents(
                            collection_name, documents
                        )
                        app.console.print(f"[green]✓[/green] Indexed {indexed} document chunks")

        except Exception as e:
            app.console.print(f"[red]✗ Failed during crawl: {e}[/red]")
            raise click.ClickException(str(e))
        finally:
            await app.cleanup()

    run_async(_crawl())


@main.command()
@click.argument("query")
@click.option("--project", "-p", help="Search specific project")
@click.option("--limit", "-l", default=10, type=int, help="Maximum results")
@click.option("--strategy", default="semantic", help="Search strategy")
@click.pass_context
def search(ctx: click.Context, query: str, project: Optional[str], limit: int, strategy: str):
    """Search documentation."""
    async def _search():
        app = get_app()
        await app.initialize()

        try:
            if project:
                # Search specific project
                project_obj = await app.db_manager.get_project_by_name(project)
                if not project_obj:
                    raise click.ClickException(f"Project '{project}' not found")

                collection_name = f"project_{project_obj.id}"
                results = await app.rag_service.search(
                    query=query,
                    collection_name=collection_name,
                    limit=limit,
                    strategy=strategy
                )
            else:
                # Search all projects
                projects = await app.db_manager.list_projects()
                project_names = [p.name for p in projects]
                results = await app.rag_service.search_multi_project(
                    query=query,
                    project_names=project_names,
                    limit=limit,
                    strategy=strategy
                )

            if not results:
                app.console.print("No results found.")
                return

            # Display results
            app.console.print(f"\n[bold]Search Results for:[/bold] {query}")
            app.console.print(f"[dim]Found {len(results)} results[/dim]\n")

            for i, result in enumerate(results, 1):
                score = result.get("score", 0)
                title = result.get("title", "Untitled")
                url = result.get("url", "")
                content = result.get("content", "")[:200] + "..." if len(result.get("content", "")) > 200 else result.get("content", "")

                app.console.print(f"[bold]{i}. {title}[/bold] (Score: {score:.3f})")
                app.console.print(f"[blue]{url}[/blue]")
                app.console.print(f"{content}")
                app.console.print()

        except Exception as e:
            app.console.print(f"[red]✗ Search failed: {e}[/red]")
            raise click.ClickException(str(e))
        finally:
            await app.cleanup()

    run_async(_search())


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
@click.option("--port", default=8000, type=int, help="Server port")
@click.pass_context
def serve(ctx: click.Context, host: str, port: int):
    """Start the MCP server for agent integration."""
    from ..services.mcp_server import run_mcp_server

    app = get_app()
    app.console.print(f"[green]Starting MCP server on {host}:{port}...[/green]")
    app.console.print("[dim]Press Ctrl+C to stop[/dim]\n")

    try:
        run_mcp_server(host=host, port=port, config=app.config)
    except KeyboardInterrupt:
        app.console.print("\n[yellow]Server stopped[/yellow]")
    except Exception as e:
        app.console.print(f"[red]✗ Server error: {e}[/red]")
        raise click.ClickException(str(e))


@main.command()
@click.pass_context
def status(ctx: click.Context):
    """Show DocBro system status."""
    async def _status():
        app = get_app()

        try:
            await app.initialize()

            app.console.print("[bold]DocBro System Status[/bold]\n")

            # Database status
            try:
                projects_count = len(await app.db_manager.list_projects())
                app.console.print(f"[green]✓[/green] Database: Connected ({projects_count} projects)")
            except Exception as e:
                app.console.print(f"[red]✗[/red] Database: {e}")

            # Vector store status
            try:
                health_ok, health_msg = await app.vector_store.health_check()
                status_icon = "[green]✓[/green]" if health_ok else "[red]✗[/red]"
                app.console.print(f"{status_icon} Vector Store: {health_msg}")
            except Exception as e:
                app.console.print(f"[red]✗[/red] Vector Store: {e}")

            # Embedding service status
            try:
                health_ok, health_msg = await app.embedding_service.health_check()
                status_icon = "[green]✓[/green]" if health_ok else "[red]✗[/red]"
                app.console.print(f"{status_icon} Embeddings: {health_msg}")
            except Exception as e:
                app.console.print(f"[red]✗[/red] Embeddings: {e}")

        except Exception as e:
            app.console.print(f"[red]✗ Failed to get status: {e}[/red]")
            raise click.ClickException(str(e))
        finally:
            await app.cleanup()

    run_async(_status())


if __name__ == "__main__":
    main()