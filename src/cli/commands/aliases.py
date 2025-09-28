"""
Command Alias Support for DocBro
Maps legacy commands to setup subcommands with deprecation warnings
"""

import sys
from typing import Optional
import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm


class CommandAlias:
    """Maps legacy commands to setup subcommands"""

    def __init__(
        self,
        name: str,
        target: str,
        confirmation_prompt: str,
        deprecation_message: Optional[str] = None
    ):
        """
        Initialize command alias.

        Args:
            name: Alias command name (e.g., "uninstall")
            target: Target setup command (e.g., "setup --uninstall")
            confirmation_prompt: Y/N prompt text with consequences
            deprecation_message: Warning about future removal
        """
        self.name = name
        self.target = target
        self.confirmation_prompt = confirmation_prompt
        self.deprecation_message = deprecation_message or (
            f"This command is deprecated. Use 'docbro {target}' instead."
        )
        self.console = Console()

    def execute(self) -> int:
        """
        Show prompt, route to target command.

        Returns:
            int: Exit code (0=success, 1=cancelled, 2=error)
        """
        # Show deprecation warning
        self.show_deprecation_warning()

        # Show confirmation prompt with consequences
        if not self._confirm_action():
            self.console.print("Operation cancelled", style="yellow")
            return 1

        # Route to target command
        try:
            from src.cli.main import cli
            # Parse target command
            parts = self.target.split()
            if parts[0] == 'setup':
                # Import setup command and execute
                from src.cli.commands.setup import setup_command
                # Parse flags from target
                flags = {}
                for part in parts[1:]:
                    if part.startswith('--'):
                        flag_name = part[2:].replace('-', '_')
                        flags[flag_name] = True

                # Execute setup with appropriate flags
                ctx = click.Context(cli)
                result = setup_command.invoke(ctx, **flags)
                return 0 if result is None else result
            else:
                self.console.print(f"Unknown target command: {self.target}", style="red")
                return 2
        except Exception as e:
            self.console.print(f"Error executing command: {e}", style="red")
            return 2

    def show_deprecation_warning(self) -> None:
        """Display deprecation notice."""
        warning_panel = Panel(
            self.deprecation_message,
            title="⚠️  Deprecation Warning",
            style="yellow",
            border_style="yellow"
        )
        self.console.print(warning_panel)

    def _confirm_action(self) -> bool:
        """
        Show detailed confirmation prompt.

        Returns:
            bool: True if user confirms, False otherwise
        """
        # Use Rich's Confirm for better Y/N validation
        # It only accepts y/Y/n/N and re-prompts on invalid input
        return Confirm.ask(
            f"[yellow]{self.confirmation_prompt}[/yellow]\n[bold]Continue?[/bold]",
            default=False
        )


# Pre-defined aliases for legacy commands
UNINSTALL_ALIAS = CommandAlias(
    name="uninstall",
    target="setup --uninstall",
    confirmation_prompt="This will remove all DocBro data and configuration",
    deprecation_message="This command is deprecated. Use 'docbro setup --uninstall' instead."
)

INIT_ALIAS = CommandAlias(
    name="init",
    target="setup --init",
    confirmation_prompt="This will initialize DocBro and create configuration files",
    deprecation_message="This command is deprecated. Use 'docbro setup --init' instead."
)

RESET_ALIAS = CommandAlias(
    name="reset",
    target="setup --reset",
    confirmation_prompt="This will reset DocBro to default settings. Projects will be preserved",
    deprecation_message="This command is deprecated. Use 'docbro setup --reset' instead."
)