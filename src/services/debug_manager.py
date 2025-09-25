"""Debug infrastructure for conditional logging and output control."""

import logging
from typing import Optional, Dict, Any
from contextlib import contextmanager
import sys


class DebugManager:
    """Manages debug state and logging configuration for CLI operations."""

    def __init__(self):
        """Initialize debug manager with default settings."""
        self._debug_enabled = False
        self._original_log_level = logging.INFO
        self._suppressed_loggers = set()
        self._handlers_backup = {}

    @property
    def debug_enabled(self) -> bool:
        """Check if debug mode is enabled."""
        return self._debug_enabled

    def enable_debug(self, log_level: int = logging.DEBUG) -> None:
        """Enable debug mode with verbose logging.

        Args:
            log_level: Logging level to set when debug is enabled
        """
        self._debug_enabled = True
        self._original_log_level = logging.root.level

        # Configure root logger
        logging.root.setLevel(log_level)

        # Ensure console handler exists
        if not any(isinstance(h, logging.StreamHandler) for h in logging.root.handlers):
            handler = logging.StreamHandler(sys.stderr)
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            handler.setFormatter(formatter)
            logging.root.addHandler(handler)

    def disable_debug(self) -> None:
        """Disable debug mode and restore original logging configuration."""
        self._debug_enabled = False
        logging.root.setLevel(self._original_log_level)

    def suppress_logger(self, logger_name: str) -> None:
        """Suppress output from a specific logger when not in debug mode.

        Args:
            logger_name: Name of the logger to suppress
        """
        if not self._debug_enabled:
            logger = logging.getLogger(logger_name)
            self._handlers_backup[logger_name] = logger.handlers.copy()
            logger.handlers = []
            self._suppressed_loggers.add(logger_name)

    def restore_logger(self, logger_name: str) -> None:
        """Restore a previously suppressed logger.

        Args:
            logger_name: Name of the logger to restore
        """
        if logger_name in self._suppressed_loggers:
            logger = logging.getLogger(logger_name)
            if logger_name in self._handlers_backup:
                logger.handlers = self._handlers_backup[logger_name]
                del self._handlers_backup[logger_name]
            self._suppressed_loggers.remove(logger_name)

    def restore_all_loggers(self) -> None:
        """Restore all suppressed loggers."""
        for logger_name in list(self._suppressed_loggers):
            self.restore_logger(logger_name)

    @contextmanager
    def conditional_output(self, force: bool = False):
        """Context manager for conditional output based on debug state.

        Args:
            force: If True, always allow output regardless of debug state

        Yields:
            bool: True if output should be shown, False otherwise
        """
        should_output = force or self._debug_enabled
        yield should_output

    def format_debug_info(self, info: Dict[str, Any]) -> str:
        """Format debug information for display.

        Args:
            info: Dictionary of debug information

        Returns:
            Formatted debug string
        """
        if not self._debug_enabled:
            return ""

        lines = ["DEBUG INFO:"]
        for key, value in info.items():
            lines.append(f"  {key}: {value}")
        return "\n".join(lines)

    def should_show_traceback(self) -> bool:
        """Check if full tracebacks should be shown.

        Returns:
            True if debug mode is enabled
        """
        return self._debug_enabled

    def get_log_level(self) -> int:
        """Get the appropriate log level based on debug state.

        Returns:
            Current log level
        """
        return logging.DEBUG if self._debug_enabled else logging.WARNING

    def configure_library_logging(self) -> None:
        """Configure logging for common libraries based on debug state."""
        libraries = [
            'urllib3', 'requests', 'httpx', 'asyncio',
            'sqlalchemy.engine', 'qdrant_client'
        ]

        for lib in libraries:
            logger = logging.getLogger(lib)
            if self._debug_enabled:
                logger.setLevel(logging.DEBUG)
            else:
                logger.setLevel(logging.WARNING)


# Global instance for singleton pattern
_debug_manager_instance: Optional[DebugManager] = None


def get_debug_manager() -> DebugManager:
    """Get the global debug manager instance.

    Returns:
        The singleton DebugManager instance
    """
    global _debug_manager_instance
    if _debug_manager_instance is None:
        _debug_manager_instance = DebugManager()
    return _debug_manager_instance