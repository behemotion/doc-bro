"""Create command for DocBro CLI."""

import asyncio
from typing import Optional

import click
from rich.console import Console

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


@click.command(name="create")
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

    Flexible creation modes:
    - docbro create                      # Interactive wizard
    - docbro create myproject            # Create without URL (lazy mode)
    - docbro create myproject -u "URL"  # Create with URL (complete mode)
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
            # Support lazy creation - URL is optional when name is provided
            if not url:
                app.console.print(f"[yellow]Creating project '{name}' without URL.[/yellow]")
                app.console.print("[yellow]You can provide the URL later when crawling:[/yellow]")
                app.console.print(f"[yellow]  docbro crawl {name} --url \"YOUR_URL_HERE\"[/yellow]")
                url_to_use = None
            else:
                url_to_use = url

            name_to_use = name
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

            # Create project with optional URL
            project = await app.db_manager.create_project(
                name=name_to_use,
                source_url=url_to_use,
                crawl_depth=depth_to_use,
                embedding_model=model_to_use
            )

            app.console.print(f"[green]✓[/green] Project '{name_to_use}' created successfully")
            app.console.print(f"  ID: {project.id}")
            if project.source_url:
                app.console.print(f"  URL: {project.source_url}")
            else:
                app.console.print(f"  URL: [yellow]Not set (provide when crawling)[/yellow]")
            app.console.print(f"  Depth: {project.crawl_depth}")

            if not url_to_use:
                app.console.print("\n[cyan]Next steps:[/cyan]")
                app.console.print(f"  1. Crawl documentation: [cyan]docbro crawl {name_to_use} --url \"YOUR_URL\"[/cyan]")
                app.console.print(f"  2. Start MCP server: [cyan]docbro serve[/cyan]")
            else:
                app.console.print("\n[cyan]Next step:[/cyan] Run [cyan]docbro crawl {name_to_use}[/cyan] to start crawling")

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