"""Legacy init command - redirects to setup --init."""

import click
from rich.console import Console
from src.cli.commands.setup import setup

console = Console()


@click.command(deprecated=True)
@click.option(
    "--auto",
    is_flag=True,
    help="Use automatic mode with defaults"
)
@click.option(
    "--force",
    is_flag=True,
    help="Force initialization even if already exists"
)
@click.option(
    "--vector-store",
    type=click.Choice(["sqlite_vec", "qdrant"]),
    help="Select vector store provider"
)
@click.pass_context
def init(ctx: click.Context, auto: bool, force: bool, vector_store: str):
    """Initialize DocBro configuration (DEPRECATED).

    This command is deprecated. Use 'docbro setup --init' instead.
    """
    # Show deprecation warning
    console.print("[yellow]⚠ Warning:[/yellow] 'docbro init' is deprecated.")
    console.print("Use [cyan]docbro setup --init[/cyan] instead.")
    console.print()

    # Redirect to setup command with --init flag
    ctx.invoke(setup, init=True, auto=auto, force=force, vector_store=vector_store)