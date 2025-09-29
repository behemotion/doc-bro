"""CLI help formatter for backward compatibility."""

import click
from typing import Dict, Any


class CliHelpFormatter:
    """Help formatter for CLI commands."""

    def __init__(self):
        """Initialize the help formatter."""
        pass

    def format_help(self, command: str, context: Dict[str, Any] = None) -> str:
        """Format help text for a command."""
        help_text = f"Help for command: {command}"
        if context:
            help_text += f"\nContext: {context}"
        return help_text

    def format_command_list(self, commands: list) -> str:
        """Format a list of available commands."""
        if not commands:
            return "No commands available"

        formatted = "Available commands:\n"
        for cmd in commands:
            formatted += f"  {cmd}\n"
        return formatted