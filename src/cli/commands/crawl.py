"""Crawl command for DocBro CLI."""

import asyncio
from typing import Optional
from datetime import datetime

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn, TimeElapsedColumn

# Optional uvloop for better performance
try:
    import uvloop
    UVLOOP_AVAILABLE = True
except ImportError:
    UVLOOP_AVAILABLE = False


def run_async(coro):
    """Run async coroutine in sync context."""
    if UVLOOP_AVAILABLE:
        try:
            uvloop.install()
        except Exception:
            pass

    return asyncio.run(coro)


def get_app():
    """Get or create global app instance."""
    from src.cli.main import get_app as main_get_app
    return main_get_app()


@click.command(name="crawl")
@click.argument("name", required=False)
@click.option("--url", "-u", help="Set or update the project URL before crawling")
@click.option("--max-pages", "-m", type=int, help="Maximum pages to crawl")
@click.option("--rate-limit", "-r", default=1.0, type=float, help="Requests per second")
@click.option("--depth", "-d", type=int, help="Override crawl depth for this session")
@click.option("--update", is_flag=True, help="Update existing project(s)")
@click.option("--all", is_flag=True, help="Process all projects")
@click.option("--debug", is_flag=True, help="Show detailed crawl output")
@click.pass_context
def crawl(ctx: click.Context, name: Optional[str], url: Optional[str], max_pages: Optional[int],
         rate_limit: float, depth: Optional[int], update: bool, all: bool, debug: bool):
    """Start crawling a documentation project.

    Enhanced flexible crawl modes:
    - docbro crawl myproject                  # Use existing URL
    - docbro crawl myproject --url "URL"      # Provide/update URL
    - docbro crawl myproject --depth 3        # Override depth

    Examples:
      docbro crawl my-project                  # Crawl a specific project
      docbro crawl my-project --url "URL"     # Set URL and crawl
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

            from src.logic.crawler.core.batch import BatchCrawler
            from src.logic.crawler.utils.progress import ProgressReporter

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

            # Handle URL update if provided
            if url:
                app.console.print(f"[cyan]Updating URL for project '{name}'...[/cyan]")
                await app.db_manager.update_project(
                    project.id,
                    source_url=url
                )
                project.source_url = url
                app.console.print(f"[green]✓[/green] URL updated: {url}")

            # Check if project has URL
            if not project.source_url:
                app.console.print(f"[red]Error:[/red] Project '{name}' has no URL set.")
                app.console.print(f"[yellow]Tip:[/yellow] Provide a URL using: [cyan]docbro crawl {name} --url \"YOUR_URL\"[/cyan]")
                raise click.ClickException("No URL configured for project")

            # Handle depth override if provided
            if depth:
                app.console.print(f"[cyan]Using crawl depth override: {depth}[/cyan]")
                # Temporarily update the project's crawl depth for this session
                original_depth = project.crawl_depth
                project.crawl_depth = depth

            # Use simple progress display
            from src.logic.crawler.utils.progress import CrawlProgressDisplay
            from src.logic.crawler.analytics.reporter import ErrorReporter

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
                    app.console.print(f"  URL: {project.source_url}")
                    app.console.print(f"  Depth: {project.crawl_depth}")
                    app.console.print(f"  Rate limit: {rate_limit} req/s")

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
                app.console.print(f"[bold]URL:[/bold] {project.source_url}")
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
            app.console.print("\n[cyan]Next steps:[/cyan]")
            app.console.print("  1. Start MCP server: [cyan]docbro serve[/cyan]")
            app.console.print("  2. Search documentation: Use Claude or other MCP clients")

        except Exception as e:
            app.console.print(f"[red]✗ Failed during crawl: {e}[/red]")
            raise click.ClickException(str(e))
        finally:
            await app.cleanup()

    run_async(_crawl())