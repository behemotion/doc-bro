"""Legacy init command - redirects to setup --init."""

import click
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
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
    warning_panel = Panel(
        "This command is deprecated. Use 'docbro setup --init' instead.",
        title="⚠️  Deprecation Warning",
        style="yellow",
        border_style="yellow"
    )
    console.print(warning_panel)

    # Show confirmation prompt with consequences
    if not Confirm.ask(
        "[yellow]This will initialize DocBro and create configuration files[/yellow]\n[bold]Continue?[/bold]",
        default=False
    ):
        console.print("Operation cancelled", style="yellow")
        sys.exit(1)

    # Redirect to setup command with --init flag
    ctx.invoke(setup, init=True, auto=auto, force=force, vector_store=vector_store)