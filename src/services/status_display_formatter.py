"""Status display formatter for consistent entity status presentation.

Provides formatting utilities for presenting entity status information
in a consistent, user-friendly manner across CLI commands.
"""

from typing import Dict, List, Optional, Any
from datetime import datetime
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich.columns import Columns
from rich import box

from src.models.command_context import CommandContext
from src.services.status_display_service import StatusDisplayService, EntityStatus


class StatusDisplayFormatter:
    """Formatter for consistent entity status presentation."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize status display formatter.

        Args:
            console: Rich console instance (creates new one if None)
        """
        self.console = console or Console()
        self.status_service = StatusDisplayService()

    def format_entity_status(self, context: CommandContext, verbose: bool = False) -> str:
        """Format entity status for display.

        Args:
            context: CommandContext with entity information
            verbose: Whether to include detailed information

        Returns:
            Formatted status string
        """
        status = self.status_service.determine_status(context)
        entity_type = context.entity_type.title()
        entity_name = context.entity_name

        # Basic status line
        status_line = f"{entity_type}: {entity_name} {self._get_status_indicator(status)}"

        if not verbose:
            return status_line

        # Add detailed information
        details = []
        if context.exists:
            if context.last_modified:
                details.append(f"Modified: {self._format_datetime(context.last_modified)}")

            if context.content_summary:
                details.append(f"Content: {context.content_summary}")

            # Add configuration details
            if context.configuration_state:
                config = context.configuration_state
                config_details = []
                if config.is_configured:
                    config_details.append("configured")
                if config.has_content:
                    config_details.append("has content")
                if config.needs_migration:
                    config_details.append("needs migration")

                if config_details:
                    details.append(f"Config: {', '.join(config_details)}")

        if details:
            status_line += f"\n  {' | '.join(details)}"

        return status_line

    def display_entity_status(self, context: CommandContext, verbose: bool = False) -> None:
        """Display entity status using rich formatting.

        Args:
            context: CommandContext with entity information
            verbose: Whether to include detailed information
        """
        status = self.status_service.determine_status(context)
        entity_type = context.entity_type.title()
        entity_name = context.entity_name

        # Create status panel
        panel_title = f"{entity_type}: {entity_name}"
        status_color = self._get_status_color(status)

        content_lines = []

        # Status line
        status_text = Text()
        status_text.append("Status: ", style="bold")
        status_text.append(status.value.replace("_", " ").title(), style=status_color)
        content_lines.append(status_text)

        if context.exists and verbose:
            # Add detailed information
            if context.last_modified:
                modified_text = Text()
                modified_text.append("Modified: ", style="bold")
                modified_text.append(self._format_datetime(context.last_modified))
                content_lines.append(modified_text)

            if context.content_summary:
                summary_text = Text()
                summary_text.append("Summary: ", style="bold")
                summary_text.append(context.content_summary)
                content_lines.append(summary_text)

            # Configuration details
            if context.configuration_state:
                config = context.configuration_state
                config_text = Text()
                config_text.append("Configuration: ", style="bold")

                config_parts = []
                if config.is_configured:
                    config_parts.append(("configured", "green"))
                else:
                    config_parts.append(("not configured", "red"))

                if config.has_content:
                    config_parts.append(("has content", "green"))
                else:
                    config_parts.append(("empty", "yellow"))

                if config.needs_migration:
                    config_parts.append(("needs migration", "red"))

                for i, (text, color) in enumerate(config_parts):
                    if i > 0:
                        config_text.append(" | ")
                    config_text.append(text, style=color)

                content_lines.append(config_text)

        # Create panel content
        panel_content = "\n".join(str(line) for line in content_lines)

        panel = Panel(
            panel_content,
            title=panel_title,
            border_style=status_color,
            box=box.ROUNDED
        )

        self.console.print(panel)

    def display_suggested_actions(self, context: CommandContext, box_type: Optional[str] = None) -> None:
        """Display suggested actions for entity.

        Args:
            context: CommandContext with entity information
            box_type: Box type for type-specific suggestions
        """
        actions = self.status_service.get_suggested_actions(context)

        # Add box type specific actions if applicable
        if box_type and context.entity_type == "box":
            type_actions = self.status_service.get_box_type_specific_actions(context, box_type)
            actions.extend(type_actions)

        if not actions:
            return

        self.console.print("\n[bold]Suggested Actions:[/bold]")

        for i, action in enumerate(actions, 1):
            action_text = Text()
            action_text.append(f"{i}. ", style="bold blue")
            action_text.append(action["description"], style="bold")
            action_text.append(f"\n   Command: ", style="dim")
            action_text.append(action["command"], style="cyan")

            self.console.print(action_text)

    def format_status_table(self, contexts: List[CommandContext], title: str = "Status") -> Table:
        """Format multiple entity statuses as a table.

        Args:
            contexts: List of CommandContext objects
            title: Table title

        Returns:
            Rich Table with formatted status information
        """
        table = Table(title=title, box=box.SIMPLE)

        table.add_column("Name", style="bold")
        table.add_column("Type", style="blue")
        table.add_column("Status", justify="center")
        table.add_column("Modified", style="dim")
        table.add_column("Content", style="green")

        for context in contexts:
            status = self.status_service.determine_status(context)
            status_color = self._get_status_color(status)

            status_text = Text(
                status.value.replace("_", " ").title(),
                style=status_color
            )

            modified_str = ""
            if context.last_modified:
                modified_str = self._format_datetime_short(context.last_modified)

            content_str = ""
            if context.content_summary:
                content_str = context.content_summary[:30] + "..." if len(context.content_summary) > 30 else context.content_summary

            table.add_row(
                context.entity_name,
                context.entity_type.title(),
                status_text,
                modified_str,
                content_str
            )

        return table

    def display_status_table(self, contexts: List[CommandContext], title: str = "Status") -> None:
        """Display multiple entity statuses as a table.

        Args:
            contexts: List of CommandContext objects
            title: Table title
        """
        table = self.format_status_table(contexts, title)
        self.console.print(table)

    def format_prompt_message(self, context: CommandContext) -> Optional[str]:
        """Format a prompt message for user action.

        Args:
            context: CommandContext with entity information

        Returns:
            Formatted prompt message or None if no action needed
        """
        should_prompt, message = self.status_service.should_prompt_for_action(context)

        if should_prompt and message:
            return f"[yellow]{message}[/yellow]"

        return None

    def display_content_statistics(self, context: CommandContext) -> None:
        """Display content statistics if available.

        Args:
            context: CommandContext with entity information
        """
        stats = self.status_service.get_content_statistics(context)

        if not stats:
            self.console.print("[dim]No content statistics available[/dim]")
            return

        self.console.print("\n[bold]Content Statistics:[/bold]")

        for key, value in stats.items():
            if key == "summary":
                self.console.print(f"  Summary: {value}")
            elif key == "last_modified":
                self.console.print(f"  Last Modified: {self._format_datetime(datetime.fromisoformat(value))}")
            elif key == "configured_at":
                self.console.print(f"  Configured: {self._format_datetime(datetime.fromisoformat(value))}")
            elif key == "is_configured":
                status = "[green]Yes[/green]" if value else "[red]No[/red]"
                self.console.print(f"  Configured: {status}")
            elif key == "has_content":
                status = "[green]Yes[/green]" if value else "[yellow]No[/yellow]"
                self.console.print(f"  Has Content: {status}")

    def _get_status_indicator(self, status: EntityStatus) -> str:
        """Get status indicator symbol.

        Args:
            status: EntityStatus value

        Returns:
            Status indicator string
        """
        indicators = {
            EntityStatus.NOT_FOUND: "❌",
            EntityStatus.UNCONFIGURED: "⚠️",
            EntityStatus.EMPTY: "📭",
            EntityStatus.CONFIGURED: "✅",
            EntityStatus.NEEDS_MIGRATION: "🔄",
            EntityStatus.ERROR: "❌"
        }
        return indicators.get(status, "❓")

    def _get_status_color(self, status: EntityStatus) -> str:
        """Get color for status display.

        Args:
            status: EntityStatus value

        Returns:
            Rich color name
        """
        colors = {
            EntityStatus.NOT_FOUND: "red",
            EntityStatus.UNCONFIGURED: "yellow",
            EntityStatus.EMPTY: "yellow",
            EntityStatus.CONFIGURED: "green",
            EntityStatus.NEEDS_MIGRATION: "blue",
            EntityStatus.ERROR: "red"
        }
        return colors.get(status, "white")

    def _format_datetime(self, dt: datetime) -> str:
        """Format datetime for display.

        Args:
            dt: Datetime to format

        Returns:
            Formatted datetime string
        """
        return dt.strftime("%Y-%m-%d %H:%M:%S")

    def _format_datetime_short(self, dt: datetime) -> str:
        """Format datetime for compact display.

        Args:
            dt: Datetime to format

        Returns:
            Compact formatted datetime string
        """
        now = datetime.now()
        diff = now - dt

        if diff.days == 0:
            return dt.strftime("%H:%M")
        elif diff.days == 1:
            return "Yesterday"
        elif diff.days < 7:
            return f"{diff.days}d ago"
        else:
            return dt.strftime("%m/%d")

    def create_status_summary_panel(self, contexts: List[CommandContext], title: str = "Summary") -> Panel:
        """Create a summary panel for multiple entities.

        Args:
            contexts: List of CommandContext objects
            title: Panel title

        Returns:
            Rich Panel with summary information
        """
        if not contexts:
            return Panel("No entities found", title=title)

        # Count statuses
        status_counts = {}
        for context in contexts:
            status = self.status_service.determine_status(context)
            status_counts[status] = status_counts.get(status, 0) + 1

        # Create summary text
        summary_lines = []
        total = len(contexts)
        summary_lines.append(f"Total entities: {total}")

        for status, count in status_counts.items():
            percentage = (count / total) * 100
            color = self._get_status_color(status)
            status_name = status.value.replace("_", " ").title()
            summary_lines.append(f"{status_name}: {count} ({percentage:.1f}%)")

        content = "\n".join(summary_lines)

        return Panel(
            content,
            title=title,
            border_style="blue",
            box=box.ROUNDED
        )