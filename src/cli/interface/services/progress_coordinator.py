"""
ProgressDisplayCoordinator with layout switching
"""

from typing import Any

from ..models.enums import CompletionStatus, LayoutMode, ProcessingState
from ..services.terminal_adapter import TerminalAdapter
from ..strategies.layout_strategy import (
    CompactStrategy,
    FullWidthStrategy,
    LayoutStrategy,
)


class ProgressDisplayCoordinator:
    """Coordinator for progress visualization with responsive layout switching"""

    def __init__(self, terminal_adapter: TerminalAdapter | None = None):
        """Initialize progress display coordinator"""
        self.terminal_adapter = terminal_adapter or TerminalAdapter()
        self.current_strategy: LayoutStrategy | None = None
        self.current_mode: LayoutMode | None = None
        self._initialize_strategy()

    def start_operation(self, title: str, project_name: str) -> None:
        """
        Initialize progress display for an operation

        Args:
            title: Operation title (e.g., "Crawling google-adk")
            project_name: Target project identifier
        """
        self._ensure_appropriate_strategy()
        if self.current_strategy:
            self.current_strategy.start_operation(title, project_name)

    def update_metrics(self, metrics: dict[str, Any]) -> None:
        """
        Update progress metrics display

        Args:
            metrics: Dictionary of metric names to values
        """
        if self.current_strategy:
            self.current_strategy.update_metrics(metrics)

    def set_current_operation(self, operation: str) -> None:
        """
        Update current operation description

        Args:
            operation: Description of current activity
        """
        if self.current_strategy:
            self.current_strategy.set_current_operation(operation)

    def show_embedding_status(self, model_name: str, project_name: str,
                             state: ProcessingState = ProcessingState.PROCESSING) -> None:
        """
        Display embedding model and processing status

        Args:
            model_name: Name of embedding model
            project_name: Target project identifier
            state: Current processing state
        """
        if self.current_strategy:
            self.current_strategy.show_embedding_status(model_name, project_name, state)

    def show_embedding_error(self, error_message: str) -> None:
        """
        Display embedding error in status area

        Args:
            error_message: Error description to display
        """
        if self.current_strategy:
            self.current_strategy.show_embedding_error(error_message)

    def complete_operation(self, project_name: str, operation_type: str,
                          duration: float, success_metrics: dict[str, Any],
                          status: CompletionStatus) -> None:
        """
        Show final results and hide progress display

        Args:
            project_name: Completed project identifier
            operation_type: Type of operation completed
            duration: Total operation time in seconds
            success_metrics: Final counts and statistics
            status: Final operation status
        """
        if self.current_strategy:
            self.current_strategy.complete_operation(project_name, operation_type, duration, success_metrics, status)

    def get_layout_mode(self) -> LayoutMode:
        """Get current layout mode"""
        if self.current_strategy:
            return self.current_strategy.get_layout_mode()
        return self._determine_optimal_layout_mode()

    def set_layout_mode(self, mode: LayoutMode) -> None:
        """Set layout mode (for responsive behavior)"""
        if mode != self.current_mode:
            self.current_mode = mode
            self._switch_strategy(mode)

    def refresh_layout(self) -> None:
        """Refresh layout based on current terminal width (for responsive behavior)"""
        optimal_mode = self._determine_optimal_layout_mode()
        if optimal_mode != self.current_mode:
            self.set_layout_mode(optimal_mode)

    def _initialize_strategy(self) -> None:
        """Initialize with appropriate strategy based on terminal width"""
        optimal_mode = self._determine_optimal_layout_mode()
        self._switch_strategy(optimal_mode)

    def _ensure_appropriate_strategy(self) -> None:
        """Ensure we have the right strategy for current terminal conditions"""
        if not self.current_strategy:
            self._initialize_strategy()
        else:
            # Check if we need to switch strategies
            self.refresh_layout()

    def _determine_optimal_layout_mode(self) -> LayoutMode:
        """Determine optimal layout mode based on terminal capabilities"""
        # Check terminal width
        if not self.terminal_adapter.is_width_sufficient_for_boxes(80):
            return LayoutMode.COMPACT

        # Check if terminal supports colors and unicode for rich display
        if not (self.terminal_adapter.supports_colors() and self.terminal_adapter.supports_unicode()):
            return LayoutMode.COMPACT

        # Check if we're in an interactive terminal
        if not self.terminal_adapter.is_interactive():
            return LayoutMode.COMPACT

        return LayoutMode.FULL_WIDTH

    def _switch_strategy(self, mode: LayoutMode) -> None:
        """Switch to appropriate strategy for the given mode"""
        # TODO: If we're switching mid-operation, we'd need to preserve state
        # For now, just switch the strategy
        if mode == LayoutMode.FULL_WIDTH:
            self.current_strategy = FullWidthStrategy()
        else:
            self.current_strategy = CompactStrategy()

        self.current_mode = mode

    def get_terminal_adapter(self) -> TerminalAdapter:
        """Get the terminal adapter instance"""
        return self.terminal_adapter
