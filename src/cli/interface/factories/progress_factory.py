"""
CLI progress reporter factory
"""


from ..services.progress_coordinator import ProgressDisplayCoordinator
from ..services.terminal_adapter import TerminalAdapter


class ProgressFactory:
    """Factory for creating progress display components"""

    def __init__(self, terminal_adapter: TerminalAdapter | None = None):
        """Initialize progress factory"""
        self.terminal_adapter = terminal_adapter or TerminalAdapter()

    def create_progress_coordinator(self) -> ProgressDisplayCoordinator:
        """Create a progress display coordinator with automatic layout detection"""
        return ProgressDisplayCoordinator(self.terminal_adapter)

    def create_terminal_adapter(self) -> TerminalAdapter:
        """Create a terminal adapter instance"""
        return TerminalAdapter()

    @classmethod
    def get_default_coordinator(cls) -> ProgressDisplayCoordinator:
        """Get a default progress coordinator instance"""
        factory = cls()
        return factory.create_progress_coordinator()
