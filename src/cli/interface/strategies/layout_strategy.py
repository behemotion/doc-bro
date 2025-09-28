"""
Layout strategy base class and implementations
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional

from ..models.enums import LayoutMode, ProcessingState, CompletionStatus


class LayoutStrategy(ABC):
    """Abstract base class for layout strategies"""

    @abstractmethod
    def start_operation(self, title: str, project_name: str) -> None:
        """Initialize progress display for an operation"""
        pass

    @abstractmethod
    def update_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update progress metrics display"""
        pass

    @abstractmethod
    def set_current_operation(self, operation: str) -> None:
        """Update current operation description"""
        pass

    @abstractmethod
    def show_embedding_status(self, model_name: str, project_name: str,
                             state: ProcessingState = ProcessingState.PROCESSING) -> None:
        """Display embedding model and processing status"""
        pass

    @abstractmethod
    def show_embedding_error(self, error_message: str) -> None:
        """Display embedding error in status area"""
        pass

    @abstractmethod
    def complete_operation(self, project_name: str, operation_type: str,
                          duration: float, success_metrics: Dict[str, Any],
                          status: CompletionStatus) -> None:
        """Show final results and hide progress display"""
        pass

    @abstractmethod
    def get_layout_mode(self) -> LayoutMode:
        """Get current layout mode"""
        pass


class FullWidthStrategy(LayoutStrategy):
    """Strategy for full-width Rich boxes display"""

    def __init__(self):
        """Initialize full-width strategy"""
        from ..components.full_width_display import FullWidthProgressDisplay
        self.display = FullWidthProgressDisplay()

    def start_operation(self, title: str, project_name: str) -> None:
        """Initialize progress display for an operation"""
        self.display.start_operation(title, project_name)

    def update_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update progress metrics display"""
        self.display.update_metrics(metrics)

    def set_current_operation(self, operation: str) -> None:
        """Update current operation description"""
        self.display.set_current_operation(operation)

    def show_embedding_status(self, model_name: str, project_name: str,
                             state: ProcessingState = ProcessingState.PROCESSING) -> None:
        """Display embedding model and processing status"""
        self.display.show_embedding_status(model_name, project_name, state)

    def show_embedding_error(self, error_message: str) -> None:
        """Display embedding error in status area"""
        self.display.show_embedding_error(error_message)

    def complete_operation(self, project_name: str, operation_type: str,
                          duration: float, success_metrics: Dict[str, Any],
                          status: CompletionStatus) -> None:
        """Show final results and hide progress display"""
        self.display.complete_operation(project_name, operation_type, duration, success_metrics, status)

    def get_layout_mode(self) -> LayoutMode:
        """Get current layout mode"""
        return LayoutMode.FULL_WIDTH


class CompactStrategy(LayoutStrategy):
    """Strategy for compact vertical text display"""

    def __init__(self):
        """Initialize compact strategy"""
        from ..components.compact_display import CompactProgressDisplay
        self.display = CompactProgressDisplay()

    def start_operation(self, title: str, project_name: str) -> None:
        """Initialize progress display for an operation"""
        self.display.start_operation(title, project_name)

    def update_metrics(self, metrics: Dict[str, Any]) -> None:
        """Update progress metrics display"""
        self.display.update_metrics(metrics)

    def set_current_operation(self, operation: str) -> None:
        """Update current operation description"""
        self.display.set_current_operation(operation)

    def show_embedding_status(self, model_name: str, project_name: str,
                             state: ProcessingState = ProcessingState.PROCESSING) -> None:
        """Display embedding model and processing status"""
        self.display.show_embedding_status(model_name, project_name, state)

    def show_embedding_error(self, error_message: str) -> None:
        """Display embedding error in status area"""
        self.display.show_embedding_error(error_message)

    def complete_operation(self, project_name: str, operation_type: str,
                          duration: float, success_metrics: Dict[str, Any],
                          status: CompletionStatus) -> None:
        """Show final results and hide progress display"""
        self.display.complete_operation(project_name, operation_type, duration, success_metrics, status)

    def get_layout_mode(self) -> LayoutMode:
        """Get current layout mode"""
        return LayoutMode.COMPACT