"""
FullWidthProgressDisplay component for rich colored boxes
"""

from typing import Any

from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from ..models.completion_summary import CompletionSummary
from ..models.embedding_status import EmbeddingStatus
from ..models.enums import CompletionStatus, LayoutMode, ProcessingState
from ..models.progress_box import ProgressBox
from ..services.terminal_adapter import TerminalAdapter
from ..services.text_truncator import TextTruncator


class FullWidthProgressDisplay:
    """Component for full-width Rich colored box progress display"""

    def __init__(self, terminal_adapter: TerminalAdapter | None = None,
                 text_truncator: TextTruncator | None = None):
        """Initialize full-width progress display"""
        self.terminal_adapter = terminal_adapter or TerminalAdapter()
        self.text_truncator = text_truncator or TextTruncator()
        self.console = self.terminal_adapter.get_console()
        self.layout_mode = LayoutMode.FULL_WIDTH
        self.current_live: Live | None = None
        self.progress_box: ProgressBox | None = None
        self.embedding_status: EmbeddingStatus | None = None

    def start_operation(self, title: str, project_name: str) -> None:
        """
        Initialize progress display for an operation

        Args:
            title: Operation title (e.g., "Crawling google-adk")
            project_name: Target project identifier
        """
        self.progress_box = ProgressBox(
            title=title,
            project_name=project_name,
            width=self.terminal_adapter.get_terminal_width()
        )
        self._update_display()

    def update_metrics(self, metrics: dict[str, Any]) -> None:
        """
        Update progress metrics display

        Args:
            metrics: Dictionary of metric names to values
        """
        if self.progress_box:
            self.progress_box.metrics = metrics
            self._update_display()

    def set_current_operation(self, operation: str) -> None:
        """
        Update current operation description

        Args:
            operation: Description of current activity
        """
        if self.progress_box:
            # Truncate operation text to fit in box
            max_width = self.terminal_adapter.get_max_content_width() - 20  # Account for label
            truncated_operation = self.text_truncator.truncate_url(operation, max_width)
            self.progress_box.current_operation = truncated_operation
            self._update_display()

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
        if self.progress_box and state == ProcessingState.PROCESSING:
            self.progress_box.title = f"Embedding is running - {project_name}"

        self._update_display()

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
                project_name=self.progress_box.project_name if self.progress_box else "unknown",
                processing_state=ProcessingState.ERROR,
                error_message=error_message
            )
        self._update_display()

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
        # Stop the live display
        if self.current_live:
            self.current_live.stop()
            self.current_live = None

        # Create and display completion summary
        summary = CompletionSummary(
            project_name=project_name,
            operation_type=operation_type,
            duration=duration,
            success_metrics=success_metrics,
            status=status
        )

        self._display_completion_summary(summary)

        # Clear progress state
        self.progress_box = None
        self.embedding_status = None

    def get_layout_mode(self) -> LayoutMode:
        """Get current layout mode"""
        return self.layout_mode

    def set_layout_mode(self, mode: LayoutMode) -> None:
        """Set layout mode (for responsive behavior)"""
        self.layout_mode = mode
        self._update_display()

    def _update_display(self) -> None:
        """Update the live display with current progress"""
        if not self.progress_box:
            return

        if self.layout_mode == LayoutMode.FULL_WIDTH:
            panel = self._create_progress_panel()
        else:
            # In compact mode, don't show boxes
            return

        if self.current_live:
            self.current_live.update(panel)
        else:
            self.current_live = Live(panel, console=self.console, refresh_per_second=10)
            self.current_live.start()

    def _create_progress_panel(self) -> Panel:
        """Create Rich panel for progress display"""
        if not self.progress_box:
            return Panel("No operation in progress")

        # Create table for organized layout
        table = Table.grid(padding=1)
        table.add_column("Label", style="bold blue")
        table.add_column("Value")

        # Add project information
        table.add_row("Project:", self.progress_box.project_name)

        # Add metrics
        for key, value in self.progress_box.metrics.items():
            label = key.replace('_', ' ').title() + ":"
            table.add_row(label, str(value))

        # Add current operation if set
        if self.progress_box.current_operation:
            table.add_row("Current:", self.progress_box.current_operation)

        # Add embedding status if present
        if self.embedding_status:
            embedding_text = f"Embedding with: {self.embedding_status.model_name}"
            if self.embedding_status.error_message:
                embedding_text += f" {self.embedding_status.get_status_text()}"
            table.add_row("", embedding_text)

        # Create panel with full width
        return Panel(
            table,
            title=self.progress_box.title,
            border_style="blue",  # Use valid Rich color instead of "rounded"
            width=self.progress_box.width
        )

    def _display_completion_summary(self, summary: CompletionSummary) -> None:
        """Display completion summary"""
        emoji = summary.get_status_emoji()
        status_text = summary.status.value.replace('_', ' ').upper()

        # Create formatted output
        self.console.print()
        self.console.print(f"{emoji} {summary.operation_type.upper()} {status_text} {emoji}")
        self.console.print("=" * 60)
        self.console.print(f"Project: {summary.project_name}")

        # Display metrics
        for key, value in summary.success_metrics.items():
            label = key.replace('_', ' ').title()
            self.console.print(f"{label}: {value}")

        # Display duration and success rate
        self.console.print(f"Duration: {summary.format_duration()}")
        success_rate = summary.get_success_rate()
        self.console.print(f"Success Rate: {success_rate:.1f}%")

        # Status
        final_status = "Ready for search" if summary.status == CompletionStatus.SUCCESS else "Check logs for details"
        self.console.print(f"Status: {final_status}")
        self.console.print("=" * 60)
