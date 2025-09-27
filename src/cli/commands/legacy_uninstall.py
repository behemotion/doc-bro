"""Legacy uninstall command - redirects to setup --uninstall."""

import click
from rich.console import Console
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
    console.print("[yellow]⚠ Warning:[/yellow] 'docbro uninstall' is deprecated.")
    console.print("Use [cyan]docbro setup --uninstall[/cyan] instead.")
    console.print()

    # Redirect to setup command with --uninstall flag
    ctx.invoke(setup, uninstall=True, force=force, backup=backup, dry_run=dry_run)