"""
CompactProgressDisplay component for simple vertical layout
"""

from typing import Any

from ..models.completion_summary import CompletionSummary
from ..models.embedding_status import EmbeddingStatus
from ..models.enums import CompletionStatus, LayoutMode, ProcessingState
from ..services.terminal_adapter import TerminalAdapter
from ..services.text_truncator import TextTruncator


class CompactProgressDisplay:
    """Component for compact vertical text layout progress display"""

    def __init__(self, terminal_adapter: TerminalAdapter | None = None,
                 text_truncator: TextTruncator | None = None):
        """Initialize compact progress display"""
        self.terminal_adapter = terminal_adapter or TerminalAdapter()
        self.text_truncator = text_truncator or TextTruncator()
        self.console = self.terminal_adapter.get_console()
        self.layout_mode = LayoutMode.COMPACT
        self.current_title: str | None = None
        self.current_project: str | None = None
        self.embedding_status: EmbeddingStatus | None = None

    def start_operation(self, title: str, project_name: str) -> None:
        """
        Initialize progress display for an operation

        Args:
            title: Operation title (e.g., "Crawling google-adk")
            project_name: Target project identifier
        """
        self.current_title = title
        self.current_project = project_name
        self.console.print(f"\\n{title}")
        self.console.print(f"Project: {project_name}")

    def update_metrics(self, metrics: dict[str, Any]) -> None:
        """
        Update progress metrics display

        Args:
            metrics: Dictionary of metric names to values
        """
        # In compact mode, show simplified metrics
        for key, value in metrics.items():
            label = key.replace('_', ' ').title()
            self.console.print(f"{label}: {value}")

    def set_current_operation(self, operation: str) -> None:
        """
        Update current operation description

        Args:
            operation: Description of current activity
        """
        # Truncate for narrow terminals
        max_width = self.terminal_adapter.get_terminal_width() - 10
        truncated_operation = self.text_truncator.truncate_url(operation, max_width)
        self.console.print(f"Current: {truncated_operation}")

    def show_embedding_status(self, model_name: str, project_name: str,
                             state: ProcessingState = ProcessingState.PROCESSING) -> None:
        """
        Display embedding model and processing status

        Args:
            model_name: Name of embedding model
            project_name: Target project identifier
            state: Current processing state
        """
        self.embedding_status = EmbeddingStatus(
            model_name=model_name,
            project_name=project_name,
            processing_state=state
        )

        # Update title to indicate embedding is running
        if state == ProcessingState.PROCESSING:
            self.current_title = f"Embedding is running - {project_name}"
            self.console.print()
            self.console.print(self.current_title)

        status_text = self.embedding_status.get_status_text()
        self.console.print(f"Embedding with: {model_name} {status_text}")
        self.console.print(f"Project: {project_name}")

    def show_embedding_error(self, error_message: str) -> None:
        """
        Display embedding error in status area

        Args:
            error_message: Error description to display
        """
        if self.embedding_status:
            self.embedding_status.error_message = error_message
            self.embedding_status.processing_state = ProcessingState.ERROR
        else:
            # Create embedding status just for error display
            self.embedding_status = EmbeddingStatus(
                model_name="unknown",
                project_name=self.current_project or "unknown",
                processing_state=ProcessingState.ERROR,
                error_message=error_message
            )

        status_text = self.embedding_status.get_status_text()
        self.console.print(f"Embedding: {status_text}")

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
        summary = CompletionSummary(
            project_name=project_name,
            operation_type=operation_type,
            duration=duration,
            success_metrics=success_metrics,
            status=status
        )

        self._display_completion_summary(summary)

        # Clear state
        self.current_title = None
        self.current_project = None
        self.embedding_status = None

    def get_layout_mode(self) -> LayoutMode:
        """Get current layout mode"""
        return self.layout_mode

    def set_layout_mode(self, mode: LayoutMode) -> None:
        """Set layout mode (for responsive behavior)"""
        self.layout_mode = mode

    def _display_completion_summary(self, summary: CompletionSummary) -> None:
        """Display completion summary in compact format"""
        status_symbol = {
            CompletionStatus.SUCCESS: "✓",
            CompletionStatus.PARTIAL_SUCCESS: "⚠",
            CompletionStatus.FAILURE: "✗"
        }

        symbol = status_symbol.get(summary.status, "?")
        status_text = summary.status.value.replace('_', ' ')

        self.console.print()
        self.console.print(f"{symbol} {summary.operation_type.title()} {status_text}")
        self.console.print(f"Project: {summary.project_name}")
        self.console.print(f"Duration: {summary.format_duration()}")

        # Show key metrics
        pages_crawled = summary.success_metrics.get('pages_crawled', 0)
        if pages_crawled > 0:
            success_rate = summary.get_success_rate()
            self.console.print(f"Pages Crawled: {pages_crawled}")
            self.console.print(f"Success Rate: {success_rate:.1f}%")

        # Final status
        final_status = "Ready" if summary.status == CompletionStatus.SUCCESS else "Check logs"
        self.console.print(f"Status: {final_status}")
