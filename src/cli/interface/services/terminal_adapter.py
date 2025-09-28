"""
TerminalAdapter service for terminal capability detection
"""

import os
import sys
from rich.console import Console


class TerminalAdapter:
    """Service for terminal capability detection and adaptation"""

    def __init__(self):
        """Initialize terminal adapter with Rich console"""
        self.console = Console()

    def get_terminal_width(self) -> int:
        """Get current terminal width in characters"""
        try:
            # Use Rich's console size detection
            return self.console.size.width
        except (AttributeError, OSError):
            # Fallback to environment or default
            try:
                return int(os.environ.get('COLUMNS', 80))
            except (ValueError, TypeError):
                return 80

    def supports_colors(self) -> bool:
        """Check if terminal supports color output"""
        return self.console.color_system is not None

    def supports_unicode(self) -> bool:
        """Check if terminal supports Unicode box drawing"""
        # Rich handles Unicode detection internally
        # Check if we can encode Unicode characters
        try:
            "╭─╮│╰─╯".encode(sys.stdout.encoding or 'utf-8')
            return True
        except (UnicodeEncodeError, AttributeError):
            return False

    def is_width_sufficient_for_boxes(self, min_width: int = 80) -> bool:
        """Check if terminal width supports full-width boxes"""
        return self.get_terminal_width() >= min_width

    def get_max_content_width(self, border_width: int = 4) -> int:
        """Get maximum content width considering borders"""
        terminal_width = self.get_terminal_width()
        return max(terminal_width - border_width, 40)  # Minimum 40 chars for content

    def is_interactive(self) -> bool:
        """Check if running in an interactive terminal"""
        return sys.stdout.isatty() and sys.stdin.isatty()

    def get_console(self) -> Console:
        """Get the Rich console instance"""
        return self.console