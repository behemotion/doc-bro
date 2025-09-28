"""List command for DocBro CLI."""

import asyncio

import click
from rich.table import Table

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


@click.command(name="list")
@click.option("--status", "-s", help="Filter by status (e.g., 'ready', 'crawling', 'error')")
@click.option("--limit", "-l", type=int, help="Limit number of results")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.pass_context
def list_command(ctx: click.Context, status: str | None, limit: int | None, json: bool):
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
                    raise click.BadParameter(f"Invalid status: {status}. Valid values are: ready, crawling, error")

            projects = await app.db_manager.list_projects(
                status=status_filter,
                limit=limit
            )

            if not projects:
                if json:
                    import json as json_lib
                    app.console.print(json_lib.dumps([]))
                else:
                    app.console.print("No projects found.")
                return

            if json:
                # JSON output
                import json as json_lib

                project_data = []
                for project in projects:
                    project_data.append({
                        "name": project.name,
                        "url": project.source_url,
                        "status": project.status,
                        "pages": project.total_pages,
                        "last_crawl": project.last_crawl_at.isoformat() if project.last_crawl_at else None
                    })

                app.console.print(json_lib.dumps(project_data, indent=2))
            else:
                # Table output
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

                    # Color-code status
                    status_color = "green" if project.status == "ready" else "yellow" if project.status == "crawling" else "red"
                    status_display = f"[{status_color}]{project.status}[/{status_color}]"

                    table.add_row(
                        project.name,
                        project.source_url or "[dim]Not set[/dim]",
                        status_display,
                        str(project.total_pages),
                        last_crawl
                    )

                app.console.print(table)

                # Add helpful tips
                if any(not p.source_url for p in projects):
                    app.console.print("\n[yellow]Tip:[/yellow] Some projects don't have URLs set. Use [cyan]docbro crawl <name> --url \"URL\"[/cyan] to set and crawl.")

        except Exception as e:
            app.console.print(f"[red]✗ Failed to list projects: {e}[/red]")
            raise click.ClickException(str(e))
        finally:
            await app.cleanup()

    run_async(_list())


# Export the command using the name expected by Click
list = list_command
