"""Legacy reset command - redirects to setup --reset."""

import click
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from src.cli.commands.setup import setup

console = Console()

@click.command(deprecated=True)
@click.option(
    "--preserve-data",
    is_flag=True,
    help="Preserve project data during reset"
)
@click.pass_context
def reset(ctx: click.Context, preserve_data: bool):
    """Reset DocBro to defaults (DEPRECATED).

    This command is deprecated. Use 'docbro setup --reset' instead.
    """
    # Show deprecation warning
    warning_panel = Panel(
        "This command is deprecated. Use 'docbro setup --reset' instead.",
        title="⚠️  Deprecation Warning",
        style="yellow",
        border_style="yellow"
    )
    console.print(warning_panel)

    # Show confirmation prompt with consequences
    if not Confirm.ask(
        "[yellow]This will reset DocBro to default settings. Projects will be preserved[/yellow]\n[bold]Continue?[/bold]",
        default=False
    ):
        console.print("Operation cancelled", style="yellow")
        sys.exit(1)

    # Redirect to setup command with --reset flag
    ctx.invoke(setup, reset=True, preserve_data=preserve_data)