"""CliContext model for CLI command execution state."""

from typing import Optional
from enum import Enum
from pydantic import BaseModel, Field
from pathlib import Path


class OutputFormat(str, Enum):
    """Output format options for CLI commands."""
    HUMAN = "human"
    JSON = "json"
    MINIMAL = "minimal"


class LogLevel(str, Enum):
    """Logging level options."""
    DEBUG = "DEBUG"
    INFO = "INFO"
    WARNING = "WARNING"
    ERROR = "ERROR"
    CRITICAL = "CRITICAL"


class CliContext(BaseModel):
    """Runtime context for CLI command execution."""

    debug_enabled: bool = Field(default=False)
    output_format: OutputFormat = Field(default=OutputFormat.HUMAN)
    interactive_mode: bool = Field(default=True)
    config_path: Optional[Path] = None
    log_level: LogLevel = Field(default=LogLevel.INFO)
    progress_enabled: bool = Field(default=True)
    verbose: bool = Field(default=False)
    no_color: bool = Field(default=False)
    quiet: bool = Field(default=False)
    force: bool = Field(default=False)
    dry_run: bool = Field(default=False)

    def should_show_progress(self) -> bool:
        """Check if progress indicators should be shown.

        Returns:
            True if progress should be shown
        """
        return (
            self.progress_enabled
            and self.interactive_mode
            and self.output_format == OutputFormat.HUMAN
            and not self.debug_enabled
            and not self.quiet
        )

    def should_show_info(self) -> bool:
        """Check if INFO level messages should be shown.

        Returns:
            True if INFO messages should be displayed
        """
        return (
            self.debug_enabled
            or self.verbose
            or self.log_level in [LogLevel.DEBUG, LogLevel.INFO]
        )

    def should_show_debug(self) -> bool:
        """Check if DEBUG level messages should be shown.

        Returns:
            True if DEBUG messages should be displayed
        """
        return self.debug_enabled or self.log_level == LogLevel.DEBUG

    def should_use_color(self) -> bool:
        """Check if colored output should be used.

        Returns:
            True if color should be used
        """
        return not self.no_color and self.interactive_mode

    def get_effective_log_level(self) -> LogLevel:
        """Get the effective log level based on flags.

        Returns:
            Effective log level
        """
        if self.debug_enabled:
            return LogLevel.DEBUG
        elif self.verbose:
            return LogLevel.INFO
        elif self.quiet:
            return LogLevel.ERROR
        else:
            return self.log_level

    def is_json_output(self) -> bool:
        """Check if output should be JSON formatted.

        Returns:
            True if JSON output is requested
        """
        return self.output_format == OutputFormat.JSON

    def update_from_flags(self, **kwargs) -> None:
        """Update context from CLI flags.

        Args:
            **kwargs: CLI flag values
        """
        if kwargs.get('debug'):
            self.debug_enabled = True
            self.log_level = LogLevel.DEBUG

        if kwargs.get('verbose'):
            self.verbose = True
            if not self.debug_enabled:
                self.log_level = LogLevel.INFO

        if kwargs.get('quiet'):
            self.quiet = True
            self.log_level = LogLevel.ERROR

        if kwargs.get('no_color'):
            self.no_color = True

        if kwargs.get('json'):
            self.output_format = OutputFormat.JSON

        if kwargs.get('no_progress'):
            self.progress_enabled = False

        if kwargs.get('force'):
            self.force = True

        if kwargs.get('dry_run'):
            self.dry_run = True

        # Check if running in non-interactive mode
        import sys
        self.interactive_mode = sys.stdout.isatty()

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization.

        Returns:
            Dictionary representation
        """
        return {
            "debug_enabled": self.debug_enabled,
            "output_format": self.output_format.value,
            "interactive_mode": self.interactive_mode,
            "config_path": str(self.config_path) if self.config_path else None,
            "log_level": self.log_level.value,
            "progress_enabled": self.progress_enabled,
            "verbose": self.verbose,
            "no_color": self.no_color,
            "quiet": self.quiet,
            "force": self.force,
            "dry_run": self.dry_run,
            "effective_log_level": self.get_effective_log_level().value
        }

    class Config:
        """Pydantic configuration."""
        use_enum_values = False
        arbitrary_types_allowed = True