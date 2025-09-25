"""Enhanced CLI context for managing debug flags and runtime state."""

from typing import Optional, Dict, Any, TYPE_CHECKING
from enum import Enum
import click
from src.services.debug_manager import get_debug_manager

if TYPE_CHECKING:
    from pathlib import Path


class OutputFormat(Enum):
    """Output format options for CLI commands."""
    HUMAN = "human"
    JSON = "json"
    MINIMAL = "minimal"


class CliContext:
    """Enhanced context for CLI command execution.

    Manages debug state, output formatting, and runtime configuration
    across all CLI commands.
    """

    def __init__(self):
        """Initialize CLI context with default values."""
        self.debug_enabled = False
        self.output_format = OutputFormat.HUMAN
        self.interactive_mode = True
        self.config_path: Optional['Path'] = None
        self.progress_enabled = True
        self.verbose = False
        self._debug_manager = get_debug_manager()
        self._extra_data: Dict[str, Any] = {}

    def enable_debug(self) -> None:
        """Enable debug mode for the current CLI session."""
        self.debug_enabled = True
        self._debug_manager.enable_debug()

    def disable_debug(self) -> None:
        """Disable debug mode for the current CLI session."""
        self.debug_enabled = False
        self._debug_manager.disable_debug()

    def set_output_format(self, format_str: str) -> None:
        """Set the output format for CLI commands.

        Args:
            format_str: Output format (human, json, minimal)
        """
        try:
            self.output_format = OutputFormat(format_str.lower())
        except ValueError:
            self.output_format = OutputFormat.HUMAN

    def should_show_progress(self) -> bool:
        """Check if progress indicators should be shown.

        Returns:
            True if progress should be shown
        """
        return (
            self.progress_enabled
            and self.interactive_mode
            and self.output_format == OutputFormat.HUMAN
            and not self.debug_enabled  # Hide progress in debug mode for cleaner logs
        )

    def should_show_info(self) -> bool:
        """Check if INFO level messages should be shown.

        Returns:
            True if INFO messages should be displayed
        """
        return self.debug_enabled or self.verbose

    def set_data(self, key: str, value: Any) -> None:
        """Store arbitrary data in the context.

        Args:
            key: Data key
            value: Data value
        """
        self._extra_data[key] = value

    def get_data(self, key: str, default: Any = None) -> Any:
        """Retrieve data from the context.

        Args:
            key: Data key
            default: Default value if key not found

        Returns:
            The stored value or default
        """
        return self._extra_data.get(key, default)

    def configure_from_click_context(self, ctx: click.Context) -> None:
        """Configure this context from Click's context.

        Args:
            ctx: Click context object
        """
        # Check for debug flag
        if ctx.params.get('debug', False):
            self.enable_debug()

        # Check for verbose flag
        self.verbose = ctx.params.get('verbose', False)

        # Check for output format
        if 'format' in ctx.params:
            self.set_output_format(ctx.params['format'])

        # Check for no-progress flag
        if ctx.params.get('no_progress', False):
            self.progress_enabled = False

        # Check if running in non-interactive mode (piped output)
        import sys
        self.interactive_mode = sys.stdout.isatty()

    def get_debug_manager(self):
        """Get the associated debug manager.

        Returns:
            DebugManager instance
        """
        return self._debug_manager


def get_cli_context(ctx: click.Context) -> CliContext:
    """Get or create CLI context from Click context.

    Args:
        ctx: Click context object

    Returns:
        CliContext instance
    """
    if not hasattr(ctx, 'obj') or ctx.obj is None:
        ctx.obj = CliContext()
        ctx.obj.configure_from_click_context(ctx)
    elif not isinstance(ctx.obj, CliContext):
        # Wrap existing object
        cli_ctx = CliContext()
        cli_ctx.configure_from_click_context(ctx)
        cli_ctx.set_data('original_obj', ctx.obj)
        ctx.obj = cli_ctx
    return ctx.obj


def pass_cli_context(f):
    """Decorator to pass CLI context to command functions.

    Usage:
        @click.command()
        @pass_cli_context
        def my_command(cli_ctx: CliContext):
            if cli_ctx.debug_enabled:
                print("Debug mode is on")
    """
    def wrapper(*args, **kwargs):
        ctx = click.get_current_context()
        cli_ctx = get_cli_context(ctx)
        return f(cli_ctx, *args, **kwargs)
    return click.decorators.make_pass_decorator(CliContext, ensure=True)(wrapper)