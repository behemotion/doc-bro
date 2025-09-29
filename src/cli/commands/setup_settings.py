"""Setup settings command for backward compatibility."""

import click
import asyncio
from rich.console import Console

from src.logic.setup.core.orchestrator import SetupOrchestrator
from src.logic.setup.services.configurator import SetupConfigurator

console = Console()


@click.command()
@click.option("--interactive", is_flag=True, help="Interactive settings configuration")
@click.option("--show", is_flag=True, help="Show current settings")
def setup_settings(interactive: bool, show: bool):
    """Configure DocBro settings (legacy command, use 'docbro setup' instead)."""

    console.print("[yellow]Warning: 'setup_settings' command is deprecated. Use 'docbro setup' instead.[/yellow]")

    async def run_setup():
        if show:
            from src.cli.commands.setup import display_global_settings
            display_global_settings()
        elif interactive:
            orchestrator = SetupOrchestrator()
            # Show interactive menu
            from src.logic.setup.core.menu import InteractiveMenu
            menu = InteractiveMenu()
            await menu.show_main_menu()
        else:
            console.print("No action specified. Use --interactive or --show")

    asyncio.run(run_setup())