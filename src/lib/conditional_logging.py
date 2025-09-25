"""Conditional logging handler for CLI output control."""

import logging
import sys
from typing import Optional, List, Dict, Any
from datetime import datetime


class ConditionalHandler(logging.Handler):
    """Logging handler that conditionally outputs based on debug state."""

    def __init__(self, debug_enabled: bool = False, stream=None):
        """Initialize conditional handler.

        Args:
            debug_enabled: Whether debug output is enabled
            stream: Output stream (defaults to stderr)
        """
        super().__init__()
        self.debug_enabled = debug_enabled
        self.stream = stream or sys.stderr
        self._suppressed_count = 0
        self._last_suppressed_time: Optional[datetime] = None

    def set_debug_enabled(self, enabled: bool) -> None:
        """Update debug state.

        Args:
            enabled: Whether debug should be enabled
        """
        self.debug_enabled = enabled
        if enabled and self._suppressed_count > 0:
            # Report suppressed messages when debug is enabled
            self.stream.write(
                f"\n[DEBUG] {self._suppressed_count} messages were suppressed. "
                f"Re-run with --debug to see all output.\n"
            )
            self._suppressed_count = 0

    def emit(self, record: logging.LogRecord) -> None:
        """Emit a log record based on debug state.

        Args:
            record: Log record to potentially emit
        """
        try:
            # Always show WARNING and above
            if record.levelno >= logging.WARNING:
                msg = self.format(record)
                self.stream.write(msg + '\n')
                self.flush()
            # Only show INFO and DEBUG if debug is enabled
            elif self.debug_enabled:
                msg = self.format(record)
                self.stream.write(msg + '\n')
                self.flush()
            else:
                # Track suppressed messages
                self._suppressed_count += 1
                self._last_suppressed_time = datetime.now()
        except Exception:
            self.handleError(record)

    def flush(self) -> None:
        """Flush the stream."""
        if self.stream and hasattr(self.stream, 'flush'):
            self.stream.flush()

    def get_suppressed_count(self) -> int:
        """Get count of suppressed messages.

        Returns:
            Number of messages suppressed
        """
        return self._suppressed_count

    def reset_suppressed_count(self) -> None:
        """Reset the suppressed message counter."""
        self._suppressed_count = 0
        self._last_suppressed_time = None


class CleanFormatter(logging.Formatter):
    """Clean formatter that shows minimal output when not in debug mode."""

    def __init__(self, debug_enabled: bool = False):
        """Initialize formatter.

        Args:
            debug_enabled: Whether to show detailed format
        """
        self.debug_enabled = debug_enabled
        self._debug_fmt = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        self._clean_fmt = '%(message)s'
        super().__init__()

    def set_debug_enabled(self, enabled: bool) -> None:
        """Update debug state.

        Args:
            enabled: Whether debug should be enabled
        """
        self.debug_enabled = enabled

    def format(self, record: logging.LogRecord) -> str:
        """Format a log record.

        Args:
            record: Log record to format

        Returns:
            Formatted log message
        """
        # Use detailed format in debug mode or for warnings/errors
        if self.debug_enabled or record.levelno >= logging.WARNING:
            self._style._fmt = self._debug_fmt
        else:
            self._style._fmt = self._clean_fmt

        result = super().format(record)

        # Add color for terminal output
        if sys.stderr.isatty():
            if record.levelno >= logging.ERROR:
                result = f"\033[91m{result}\033[0m"  # Red
            elif record.levelno >= logging.WARNING:
                result = f"\033[93m{result}\033[0m"  # Yellow
            elif self.debug_enabled and record.levelno == logging.DEBUG:
                result = f"\033[90m{result}\033[0m"  # Gray

        return result


class LoggingConfigurator:
    """Configures logging for the entire application."""

    def __init__(self):
        """Initialize the logging configurator."""
        self.handler: Optional[ConditionalHandler] = None
        self.formatter: Optional[CleanFormatter] = None
        self._original_handlers: List[logging.Handler] = []

    def configure(self, debug_enabled: bool = False, log_file: Optional[str] = None) -> None:
        """Configure application logging.

        Args:
            debug_enabled: Whether debug mode is enabled
            log_file: Optional file path for logging
        """
        # Store original handlers
        self._original_handlers = logging.root.handlers.copy()

        # Clear existing handlers
        logging.root.handlers.clear()

        # Create and configure conditional handler
        self.handler = ConditionalHandler(debug_enabled=debug_enabled)
        self.formatter = CleanFormatter(debug_enabled=debug_enabled)
        self.handler.setFormatter(self.formatter)

        # Add to root logger
        logging.root.addHandler(self.handler)

        # Add file handler if specified
        if log_file:
            file_handler = logging.FileHandler(log_file)
            file_handler.setFormatter(
                logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            )
            logging.root.addHandler(file_handler)

        # Set appropriate level
        logging.root.setLevel(logging.DEBUG if debug_enabled else logging.INFO)

        # Configure library logging
        self._configure_library_logging(debug_enabled)

    def _configure_library_logging(self, debug_enabled: bool) -> None:
        """Configure logging for third-party libraries.

        Args:
            debug_enabled: Whether debug mode is enabled
        """
        # Suppress noisy libraries unless in debug mode
        noisy_libs = [
            'urllib3.connectionpool',
            'requests.packages.urllib3',
            'httpx._client',
            'asyncio',
            'sqlalchemy.engine.Engine',
            'qdrant_client.http',
            'ollama'
        ]

        level = logging.DEBUG if debug_enabled else logging.WARNING
        for lib_name in noisy_libs:
            logging.getLogger(lib_name).setLevel(level)

    def update_debug_state(self, debug_enabled: bool) -> None:
        """Update debug state for all handlers and formatters.

        Args:
            debug_enabled: Whether debug should be enabled
        """
        if self.handler:
            self.handler.set_debug_enabled(debug_enabled)
        if self.formatter:
            self.formatter.set_debug_enabled(debug_enabled)

        # Update root logger level
        logging.root.setLevel(logging.DEBUG if debug_enabled else logging.INFO)

        # Update library logging
        self._configure_library_logging(debug_enabled)

    def restore_original(self) -> None:
        """Restore original logging configuration."""
        logging.root.handlers.clear()
        logging.root.handlers.extend(self._original_handlers)

    def get_suppressed_count(self) -> int:
        """Get count of suppressed messages.

        Returns:
            Number of messages suppressed
        """
        return self.handler.get_suppressed_count() if self.handler else 0


# Global configurator instance
_configurator: Optional[LoggingConfigurator] = None


def get_logging_configurator() -> LoggingConfigurator:
    """Get the global logging configurator.

    Returns:
        LoggingConfigurator instance
    """
    global _configurator
    if _configurator is None:
        _configurator = LoggingConfigurator()
    return _configurator


def configure_cli_logging(debug: bool = False, log_file: Optional[str] = None) -> None:
    """Convenience function to configure CLI logging.

    Args:
        debug: Whether debug mode is enabled
        log_file: Optional log file path
    """
    configurator = get_logging_configurator()
    configurator.configure(debug_enabled=debug, log_file=log_file)