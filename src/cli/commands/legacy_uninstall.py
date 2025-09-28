"""Legacy uninstall command - redirects to setup --uninstall."""

import click
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm
from src.cli.commands.setup import setup

console = Console()

@click.command(deprecated=True)
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompts"
)
@click.option(
    "--backup",
    is_flag=True,
    help="Create backup before uninstalling"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be removed without removing"
)
@click.pass_context
def uninstall(ctx: click.Context, force: bool, backup: bool, dry_run: bool):
    """Uninstall DocBro completely (DEPRECATED).

    This command is deprecated. Use 'docbro setup --uninstall' instead.
    """
    # Show deprecation warning
    warning_panel = Panel(
        "This command is deprecated. Use 'docbro setup --uninstall' instead.",
        title="⚠️  Deprecation Warning",
        style="yellow",
        border_style="yellow"
    )
    console.print(warning_panel)

    # Skip confirmation if force flag is used
    if not force:
        # Show confirmation prompt with consequences
        if not Confirm.ask(
            "[yellow]This will remove all DocBro data and configuration[/yellow]\n[bold]Continue?[/bold]",
            default=False
        ):
            console.print("Operation cancelled", style="yellow")
            sys.exit(1)

    # Redirect to setup command with --uninstall flag
    ctx.invoke(setup, uninstall=True, force=force, backup=backup, dry_run=dry_run)