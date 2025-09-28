"""Progress reporting service for CLI operations."""

import asyncio
import logging
import time
from typing import Optional, Dict, Any, Callable, List
from contextlib import contextmanager
from enum import Enum

from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel
from rich.progress import (
    Progress, SpinnerColumn, TextColumn, BarColumn,
    TimeRemainingColumn, MofNCompleteColumn, TaskID
)
from rich.table import Table
from rich.live import Live

logger = logging.getLogger(__name__)


class CrawlPhase(Enum):
    """Phases of crawl operation."""
    INITIALIZING = "Initializing"
    ANALYZING_HEADERS = "Analyzing headers"
    CRAWLING_CONTENT = "Crawling content"
    GENERATING_EMBEDDINGS = "Generating embeddings"
    FINALIZING = "Finalizing"


class ProgressReporter:
    """Service for reporting progress of long-running operations."""

    def __init__(self, console: Optional[Console] = None, refresh_rate: float = 0.5):
        """Initialize progress reporter.

        Args:
            console: Rich console for output
            refresh_rate: Update frequency in seconds
        """
        self.console = console or Console()
        self.refresh_rate = refresh_rate
        self.progress: Optional[Progress] = None
        self.live: Optional[Live] = None
        self.tasks: Dict[str, TaskID] = {}
        self._phase_stats: Dict[CrawlPhase, Dict[str, Any]] = {}
        self._start_times: Dict[str, float] = {}
        self._is_active = False

    def create_progress_bar(self, show_percentage: bool = True) -> Progress:
        """Create a configured progress bar.

        Args:
            show_percentage: Whether to show percentage

        Returns:
            Configured Progress instance
        """
        columns = [
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
        ]

        if show_percentage:
            columns.append(TextColumn("[progress.percentage]{task.percentage:>3.0f}%"))

        columns.extend([
            MofNCompleteColumn(),
            TimeRemainingColumn()
        ])

        return Progress(*columns, console=self.console, refresh_per_second=1/self.refresh_rate)

    @contextmanager
    def crawl_progress(self):
        """Context manager for crawl progress tracking.

        Yields:
            Self for task management
        """
        self.progress = self.create_progress_bar()
        self.live = Live(self.progress, console=self.console, refresh_per_second=1/self.refresh_rate)

        try:
            self.live.start()
            self._is_active = True
            yield self
        finally:
            self.live.stop()
            self._is_active = False
            self.progress = None
            self.live = None
            self.tasks.clear()

    def start_phase(
        self,
        phase: CrawlPhase,
        total: int = 100,
        description: Optional[str] = None
    ) -> Optional[TaskID]:
        """Start a new crawl phase.

        Args:
            phase: The phase to start
            total: Total units for this phase
            description: Custom description (uses phase name if not provided)

        Returns:
            Task ID if progress is active
        """
        if not self.progress:
            return None

        # Complete previous phase if any
        self._complete_current_phase()

        desc = description or phase.value
        task_id = self.progress.add_task(desc, total=total)
        self.tasks[phase.value] = task_id
        self._start_times[phase.value] = time.time()
        self._phase_stats[phase] = {
            'started': time.time(),
            'total': total,
            'completed': 0
        }

        logger.debug(f"Started phase: {phase.value}")
        return task_id

    def update_phase(
        self,
        phase: CrawlPhase,
        advance: int = 1,
        description: Optional[str] = None,
        completed: Optional[int] = None
    ) -> None:
        """Update progress for a phase.

        Args:
            phase: The phase to update
            advance: Units to advance by
            description: Optional description update
            completed: Set completed count directly
        """
        if not self.progress or phase.value not in self.tasks:
            return

        task_id = self.tasks[phase.value]

        update_kwargs = {}
        if description:
            update_kwargs['description'] = description
        if completed is not None:
            update_kwargs['completed'] = completed
            if phase in self._phase_stats:
                self._phase_stats[phase]['completed'] = completed

        if update_kwargs:
            self.progress.update(task_id, **update_kwargs)

        if advance > 0:
            self.progress.advance(task_id, advance)
            if phase in self._phase_stats:
                self._phase_stats[phase]['completed'] += advance

    def _complete_current_phase(self) -> None:
        """Mark the current active phase as complete."""
        for phase_name, task_id in list(self.tasks.items()):
            if self.progress:
                # Mark as complete
                task = self.progress.tasks[task_id]
                if task.completed < task.total:
                    self.progress.update(task_id, completed=task.total)

    def complete_phase(self, phase: CrawlPhase) -> None:
        """Mark a phase as complete.

        Args:
            phase: The phase to complete
        """
        if not self.progress or phase.value not in self.tasks:
            return

        task_id = self.tasks[phase.value]
        task = self.progress.tasks[task_id]
        self.progress.update(task_id, completed=task.total)

        if phase in self._phase_stats:
            self._phase_stats[phase]['completed'] = self._phase_stats[phase]['total']
            self._phase_stats[phase]['duration'] = time.time() - self._phase_stats[phase]['started']

        logger.debug(f"Completed phase: {phase.value}")

    @contextmanager
    def simple_progress(self, description: str, total: Optional[int] = None):
        """Simple progress context manager for non-crawl operations.

        Args:
            description: Description of the operation
            total: Total units (None for indeterminate)

        Yields:
            Task ID for updates
        """
        progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn() if total else TextColumn(""),
            console=self.console
        )

        with progress:
            if total:
                task_id = progress.add_task(description, total=total)
            else:
                task_id = progress.add_task(description)

            yield lambda advance=1: progress.advance(task_id, advance) if total else None

    def display_summary(self, stats: Dict[str, Any]) -> None:
        """Display a summary table.

        Args:
            stats: Statistics to display
        """
        table = Table(title="Crawl Summary", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        for key, value in stats.items():
            if isinstance(value, float):
                value = f"{value:.2f}"
            table.add_row(key.replace('_', ' ').title(), str(value))

        self.console.print(table)

    def print_phase_summary(self) -> None:
        """Print summary of all phases."""
        if not self._phase_stats:
            return

        table = Table(title="Phase Summary", show_header=True)
        table.add_column("Phase", style="cyan")
        table.add_column("Completed", style="green")
        table.add_column("Total", style="yellow")
        table.add_column("Duration (s)", style="magenta")

        for phase, stats in self._phase_stats.items():
            duration = stats.get('duration', time.time() - stats['started'])
            table.add_row(
                phase.value,
                str(stats.get('completed', 0)),
                str(stats.get('total', 0)),
                f"{duration:.2f}"
            )

        self.console.print(table)

    async def update_periodically(
        self,
        phase: CrawlPhase,
        get_current: Callable[[], int],
        get_total: Callable[[], int],
        interval: float = 0.5
    ) -> None:
        """Update progress periodically in background.

        Args:
            phase: Phase to update
            get_current: Function to get current progress
            get_total: Function to get total items
            interval: Update interval in seconds
        """
        if not self._is_active:
            return

        while self._is_active and phase.value in self.tasks:
            try:
                current = get_current()
                total = get_total()

                if total > 0:
                    self.update_phase(phase, completed=current)

                await asyncio.sleep(interval)
            except Exception as e:
                logger.debug(f"Error updating progress: {e}")
                break

    def is_active(self) -> bool:
        """Check if progress reporting is active.

        Returns:
            True if active
        """
        return self._is_active

    def log_progress(self, message: str, level: int = logging.INFO) -> None:
        """Log a message that respects progress display.

        Args:
            message: Message to log
            level: Logging level
        """
        if self.live and self._is_active:
            # Temporarily stop live display to show message
            self.live.console.print(message)
        else:
            logger.log(level, message)


# Global progress reporter instance
_progress_reporter: Optional[ProgressReporter] = None


def get_progress_reporter(console: Optional[Console] = None) -> ProgressReporter:
    """Get the global progress reporter instance.

    Args:
        console: Optional Rich console

    Returns:
        ProgressReporter instance
    """
    global _progress_reporter
    if _progress_reporter is None:
        _progress_reporter = ProgressReporter(console=console)
    return _progress_reporter


class CrawlProgressDisplay:
    """Simple progress display for crawling operations."""

    def __init__(self, project_name: str, max_depth: int, max_pages: Optional[int] = None):
        """Initialize crawl progress display."""
        self.project_name = project_name
        self.max_depth = max_depth
        self.max_pages = max_pages
        self.console = Console()

        # State tracking
        self.current_depth = 0
        self.pages_crawled = 0
        self.pages_errors = 0
        self.queue_size = 0
        self.current_url = ""
        self.current_phase = CrawlPhase.CRAWLING_CONTENT  # Track current phase

        self.live: Optional[Live] = None

    def start(self):
        """Start the live display."""
        self.live = Live(self._get_display(), console=self.console, refresh_per_second=2)
        self.live.start()

    def stop(self):
        """Stop the live display."""
        if self.live:
            self.live.stop()

    def update(self, depth: int, pages: int, errors: int, queue: int, url: str = ""):
        """Update the progress display."""
        self.current_depth = depth
        self.pages_crawled = pages
        self.pages_errors = errors
        self.queue_size = queue
        if url:
            self.current_url = url

        if self.live:
            self.live.update(self._get_display())

    def set_phase(self, phase: CrawlPhase):
        """Update the current phase."""
        self.current_phase = phase
        if self.live:
            self.live.update(self._get_display())

    def _get_display(self) -> Panel:
        """Generate the display panel."""
        table = Table(show_header=False, box=None, padding=0)
        table.add_column(style="cyan", width=20)
        table.add_column(style="white")

        table.add_row("Project:", self.project_name)
        table.add_row("Depth:", f"{self.current_depth}/{self.max_depth}")
        table.add_row("Pages crawled:", f"{self.pages_crawled}{f'/{self.max_pages}' if self.max_pages else ''}")

        if self.pages_errors > 0:
            table.add_row("[red]Errors:[/red]", f"[red]{self.pages_errors}[/red]")
        else:
            table.add_row("Errors:", "0")

        table.add_row("Queue:", str(self.queue_size))

        if self.current_url:
            # Truncate URL if too long
            url_display = self.current_url
            if len(url_display) > 60:
                url_display = url_display[:57] + "..."
            table.add_row("Current:", url_display)

        # Determine title based on current phase
        if self.current_phase == CrawlPhase.GENERATING_EMBEDDINGS:
            title = f"[bold cyan]Embedding is running - {self.project_name}[/bold cyan]"
        else:
            title = f"[bold cyan]Crawling {self.project_name}[/bold cyan]"

        return Panel(
            table,
            title=title,
            border_style="cyan"
        )

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()