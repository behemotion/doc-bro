"""Crawl command for DocBro CLI."""

import asyncio
from datetime import datetime

import click

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
def crawl(ctx: click.Context, name: str | None, url: str | None, max_pages: int | None,
         rate_limit: float, depth: int | None, update: bool, all: bool, debug: bool):
    """Start crawling a documentation project.

    Crawl documentation websites to build a local searchable knowledge base.
    The crawler follows links, extracts content, and creates vector embeddings.

    \b
    CRAWL MODES:
      docbro crawl myproject                  # Crawl using project's configured URL
      docbro crawl myproject -u "URL"         # Set/update URL and crawl
      docbro crawl --update myproject         # Re-crawl to update content
      docbro crawl --update --all             # Update all projects

    \b
    PERFORMANCE OPTIONS:
      -m, --max-pages N    Limit crawl to N pages (useful for testing)
      -r, --rate-limit F   Requests per second (default: 1.0, be respectful!)
      -d, --depth N        Override default crawl depth for this session

    \b
    UPDATE MODES:
      --update             Re-crawl existing projects to get latest content
      --all                Process all projects (use with --update)

    \b
    EXAMPLES:
      docbro crawl django                     # Crawl Django project
      docbro crawl fastapi -d 2 -m 50         # Crawl FastAPI, depth 2, max 50 pages
      docbro crawl docs -u "https://new-url.com/"  # Update URL and crawl
      docbro crawl --update --all             # Update all projects
      docbro crawl myproject --debug          # Show detailed crawl progress

    \b
    WORKFLOW:
      1. Ensure project exists: docbro project list
      2. Start crawling: docbro crawl myproject
      3. Check progress: look for completion message
      4. Use content: docbro serve (starts MCP server for AI assistants)

    \b
    RATE LIMITING:
      Please be respectful of target websites. Default rate limit is 1 req/sec.
      Increase only if you own the target site or have explicit permission.
    """
    async def _crawl():
        app = get_app()
        await app.initialize()

        # Handle batch operations
        if all:
            if not update:
                raise click.ClickException("--all requires --update flag")

            from src.logic.crawler.core.batch import BatchCrawler

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


            # Use standardized progress display
            from src.cli.interface.factories.progress_factory import ProgressFactory
            from src.cli.interface.models.enums import CompletionStatus, ProcessingState
            from src.logic.crawler.analytics.reporter import ErrorReporter

            error_reporter = ErrorReporter(project_name=name)

            if not debug and not ctx.obj.get("no_progress"):
                # Create standardized progress display
                progress_coordinator = ProgressFactory.get_default_coordinator()

                # Start operation display
                progress_coordinator.start_operation(f"Crawling {name}", name)

                try:
                    # Clean up any incomplete sessions before starting
                    app.console.print(f"[cyan]Preparing project '{name}' for crawling...[/cyan]")
                    cleanup_result = await app.db_manager.cleanup_incomplete_sessions(
                        project_id=project.id,
                        reset_pages=True  # Reset pages to ensure fresh crawl from beginning
                    )

                    # Show cleanup results to user
                    if cleanup_result["incomplete_sessions_cleaned"] > 0:
                        app.console.print(f"[yellow]⚠[/yellow] Cleaned up {cleanup_result['incomplete_sessions_cleaned']} incomplete session(s)")

                    if cleanup_result["pages_reset"] > 0:
                        app.console.print(f"[yellow]⚠[/yellow] Reset {cleanup_result['pages_reset']} page(s) for fresh crawl")

                    if cleanup_result["incomplete_sessions_cleaned"] == 0 and cleanup_result["pages_reset"] == 0:
                        app.console.print("[green]✓[/green] Project is ready for crawling")
                    else:
                        app.console.print("[green]✓[/green] Project prepared - starting fresh crawl")

                    # Start crawl
                    session = await app.crawler.start_crawl(
                        project_id=project.id,
                        rate_limit=rate_limit,
                        max_pages=max_pages,
                        progress_display=None,  # We'll handle progress through coordinator
                        error_reporter=error_reporter
                    )

                    # Progress monitoring loop
                    while True:
                        await asyncio.sleep(1.0)
                        session = await app.db_manager.get_crawl_session(session.id)
                        if not session:
                            break

                        # Update progress metrics
                        progress_coordinator.update_metrics({
                            "depth": f"{session.current_depth}/{project.crawl_depth}",
                            "pages_crawled": session.pages_crawled,
                            "errors": session.error_count,
                            "queue": session.queue_size or 0
                        })

                        # Update current operation if we have current page info
                        if hasattr(session, 'current_url') and session.current_url:
                            progress_coordinator.set_current_operation(f"Processing {session.current_url}")

                        if session.is_completed():
                            break
                except Exception as e:
                    # Show error in progress display before propagating
                    progress_coordinator.show_embedding_error(f"Crawl failed: {str(e)}")
                    raise
            else:
                # Debug mode or no progress - simple output
                # Clean up any incomplete sessions before starting
                app.console.print(f"[cyan]Preparing project '{name}' for crawling...[/cyan]")
                cleanup_result = await app.db_manager.cleanup_incomplete_sessions(
                    project_id=project.id,
                    reset_pages=True  # Reset pages to ensure fresh crawl from beginning
                )

                # Show cleanup results to user
                if cleanup_result["incomplete_sessions_cleaned"] > 0:
                    app.console.print(f"[yellow]⚠[/yellow] Cleaned up {cleanup_result['incomplete_sessions_cleaned']} incomplete session(s)")

                if cleanup_result["pages_reset"] > 0:
                    app.console.print(f"[yellow]⚠[/yellow] Reset {cleanup_result['pages_reset']} page(s) for fresh crawl")

                if cleanup_result["incomplete_sessions_cleaned"] == 0 and cleanup_result["pages_reset"] == 0:
                    app.console.print("[green]✓[/green] Project is ready for crawling")
                else:
                    app.console.print("[green]✓[/green] Project prepared - starting fresh crawl")

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
                        app.console.print("\n[green]✓[/green] Crawl completed")
                    app.console.print(f"Error report saved to: {text_path}")
                    app.console.print(f"Review errors: open {text_path}")
                else:
                    app.console.print("\n[green]✓[/green] Crawl completed successfully")

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

                # Index crawled pages for search using standardized progress display
                indexed_chunks_count = 0
                if session.pages_crawled > 0 and not debug and not ctx.obj.get("no_progress"):
                    # Show embedding status in progress display
                    embedding_model = getattr(app.rag_service, 'embedding_model', 'mxbai-embed-large')
                    progress_coordinator.show_embedding_status(embedding_model, name, ProcessingState.PROCESSING)

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

                        def progress_callback(event_type: str, data: dict):
                            nonlocal indexed_chunks_count

                            if event_type == "indexing_started":
                                progress_coordinator.show_embedding_status(
                                    embedding_model, name, ProcessingState.PROCESSING
                                )

                            elif event_type == "embedding_progress":
                                # Update current operation to show embedding progress
                                doc_title = data.get('document_title', 'document')[:30]
                                current_doc = data.get('current_document', 0)
                                total_docs = data.get('total_documents', 0)
                                progress_coordinator.set_current_operation(
                                    f"Embedding '{doc_title}...' ({current_doc}/{total_docs})"
                                )

                            elif event_type == "storing_embeddings":
                                total_embeddings = data.get('total_embeddings', 0)
                                progress_coordinator.set_current_operation(
                                    f"Storing {total_embeddings} embeddings to vector database..."
                                )

                            elif event_type == "indexing_completed":
                                indexed_chunks_count = data['chunks_indexed']
                                progress_coordinator.show_embedding_status(
                                    embedding_model, name, ProcessingState.COMPLETE
                                )

                            elif event_type == "indexing_failed":
                                error_msg = data.get('error', 'Unknown error')
                                progress_coordinator.show_embedding_error(f"Indexing failed: {error_msg}")

                        try:
                            indexed = await app.rag_service.index_documents(
                                collection_name, documents, progress_callback=progress_callback
                            )

                        except Exception as e:
                            progress_coordinator.show_embedding_error(f"Indexing failed: {e}")
                            raise
                elif session.pages_crawled > 0:
                    # Handle indexing in debug mode or no progress mode
                    app.console.print("\n[cyan]Indexing pages for search...[/cyan]")
                    pages = await app.db_manager.get_project_pages(project.id)
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
                        try:
                            indexed = await app.rag_service.index_documents(collection_name, documents)
                            indexed_chunks_count = getattr(indexed, 'chunks_indexed', len(documents))
                            app.console.print(f"[green]✓[/green] Successfully indexed {indexed_chunks_count} chunks")
                        except Exception as e:
                            app.console.print(f"[red]✗[/red] Indexing failed: {e}")
                            raise

            # Use standardized completion summary
            if session and not debug and not ctx.obj.get("no_progress"):
                # Calculate final statistics
                total_time = session.get_duration()

                # Get final document count
                final_pages = await app.db_manager.get_project_pages(project.id) if session.pages_crawled > 0 else []
                documents_with_content = [p for p in final_pages if p.content_text]

                # Prepare success metrics
                success_metrics = {
                    "pages_crawled": session.pages_crawled,
                    "pages_failed": session.pages_failed,
                    "documents_indexed": len(documents_with_content),
                    "chunks_created": indexed_chunks_count,
                    "url": project.source_url
                }

                # Determine completion status
                if session.pages_failed == 0:
                    completion_status = CompletionStatus.SUCCESS
                elif session.pages_crawled > session.pages_failed:
                    completion_status = CompletionStatus.PARTIAL_SUCCESS
                else:
                    completion_status = CompletionStatus.FAILURE

                # Show standardized completion summary
                progress_coordinator.complete_operation(
                    project_name=name,
                    operation_type="crawl",
                    duration=total_time,
                    success_metrics=success_metrics,
                    status=completion_status
                )

                # Add next steps hint
                app.console.print("\n[cyan]Next steps:[/cyan]")
                app.console.print("  1. Start MCP server: [cyan]docbro serve[/cyan]")
                app.console.print("  2. Search documentation: Use Claude or other MCP clients")

            elif session:
                # Fallback for debug mode - show simplified completion
                app.console.print("\n" + "="*60)
                app.console.print("[bold green]🎉 CRAWL AND INDEXING COMPLETED SUCCESSFULLY 🎉[/bold green]")
                app.console.print("="*60)

                total_time = session.get_duration()
                success_rate = ((session.pages_crawled - session.pages_failed) / session.pages_crawled * 100) if session.pages_crawled > 0 else 0

                app.console.print(f"[bold]Project:[/bold] {name}")
                app.console.print(f"[bold]URL:[/bold] {project.source_url}")
                app.console.print(f"[bold]Duration:[/bold] {total_time:.1f}s")
                app.console.print(f"[bold]Pages Crawled:[/bold] {session.pages_crawled}")
                app.console.print(f"[bold]Pages Failed:[/bold] {session.pages_failed}")
                app.console.print(f"[bold]Success Rate:[/bold] {success_rate:.1f}%")

                if session.pages_crawled > 0:
                    final_pages = await app.db_manager.get_project_pages(project.id)
                    documents_with_content = [p for p in final_pages if p.content_text]
                    app.console.print(f"[bold]Documents Indexed:[/bold] {len(documents_with_content)}")
                    if indexed_chunks_count > 0:
                        app.console.print(f"[bold]Chunks Created:[/bold] {indexed_chunks_count}")

                app.console.print("[bold]Status:[/bold] [green]Ready for search[/green]")
                app.console.print("="*60)

        except Exception as e:
            app.console.print(f"[red]✗ Failed during crawl: {e}[/red]")
            raise click.ClickException(str(e))
        finally:
            await app.cleanup()

    run_async(_crawl())
