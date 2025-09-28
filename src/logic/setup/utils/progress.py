"""Progress reporting utilities."""

import time
from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

from rich.console import Console
from rich.progress import (
    BarColumn,
    Progress,
    SpinnerColumn,
    TaskProgressColumn,
    TextColumn,
    TimeElapsedColumn,
    TimeRemainingColumn,
)

from src.core.lib_logger import get_logger

logger = get_logger(__name__)


class ProgressReporter:
    """Advanced progress reporting with Rich."""

    def __init__(self, console: Console | None = None):
        """Initialize progress reporter.

        Args:
            console: Optional Rich console
        """
        self.console = console or Console()
        self._progress = None
        self._task_ids = {}

    @contextmanager
    def progress_bar(
        self,
        description: str,
        total: int | None = None,
        auto_refresh: bool = True
    ) -> Iterator[Any]:
        """Create a progress bar context.

        Args:
            description: Task description
            total: Total number of steps (None for indeterminate)
            auto_refresh: Whether to auto-refresh display

        Yields:
            Progress task for updating
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeElapsedColumn(),
            console=self.console,
            auto_refresh=auto_refresh
        ) as progress:
            task = progress.add_task(description, total=total)
            try:
                yield lambda n=1: progress.update(task, advance=n)
            finally:
                progress.update(task, completed=total or progress.tasks[task].completed)

    def start_progress(self) -> None:
        """Start a persistent progress display."""
        if self._progress:
            return

        self._progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console
        )
        self._progress.start()

    def stop_progress(self) -> None:
        """Stop the persistent progress display."""
        if self._progress:
            self._progress.stop()
            self._progress = None
            self._task_ids.clear()

    def add_task(
        self,
        description: str,
        total: int | None = None,
        start: bool = True
    ) -> int:
        """Add a task to the progress display.

        Args:
            description: Task description
            total: Total steps (None for indeterminate)
            start: Whether to start the task immediately

        Returns:
            Task ID for updates
        """
        if not self._progress:
            self.start_progress()

        task_id = self._progress.add_task(
            description,
            total=total,
            start=start
        )
        self._task_ids[description] = task_id
        return task_id

    def update_task(
        self,
        task_id: int,
        advance: int = 1,
        description: str | None = None,
        **kwargs
    ) -> None:
        """Update a task's progress.

        Args:
            task_id: Task ID from add_task
            advance: Number of steps to advance
            description: Optional new description
            **kwargs: Additional update parameters
        """
        if self._progress:
            update_kwargs = {"advance": advance}
            if description:
                update_kwargs["description"] = description
            update_kwargs.update(kwargs)
            self._progress.update(task_id, **update_kwargs)

    def complete_task(self, task_id: int) -> None:
        """Mark a task as complete.

        Args:
            task_id: Task ID to complete
        """
        if self._progress:
            task = self._progress.tasks[task_id]
            self._progress.update(
                task_id,
                completed=task.total or task.completed
            )

    @contextmanager
    def spinner(self, description: str) -> Iterator[None]:
        """Show a spinner for an operation.

        Args:
            description: Operation description

        Yields:
            None
        """
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=self.console
        ) as progress:
            progress.add_task(description)
            yield

    def print_success(self, message: str) -> None:
        """Print a success message.

        Args:
            message: Success message
        """
        self.console.print(f"[green]✓[/green] {message}")

    def print_error(self, message: str) -> None:
        """Print an error message.

        Args:
            message: Error message
        """
        self.console.print(f"[red]✗[/red] {message}")

    def print_warning(self, message: str) -> None:
        """Print a warning message.

        Args:
            message: Warning message
        """
        self.console.print(f"[yellow]⚠[/yellow] {message}")

    def print_info(self, message: str) -> None:
        """Print an info message.

        Args:
            message: Info message
        """
        self.console.print(f"[blue]ℹ[/blue] {message}")


def create_progress_bar(
    description: str,
    total: int | None = None,
    console: Console | None = None
) -> Progress:
    """Create a simple progress bar.

    Args:
        description: Task description
        total: Total number of steps
        console: Optional Rich console

    Returns:
        Progress instance
    """
    progress = Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TaskProgressColumn(),
        TimeElapsedColumn(),
        console=console or Console()
    )

    progress.add_task(description, total=total)
    return progress


class StepTracker:
    """Track progress through a series of steps."""

    def __init__(self, steps: list, console: Console | None = None):
        """Initialize step tracker.

        Args:
            steps: List of step descriptions
            console: Optional Rich console
        """
        self.steps = steps
        self.console = console or Console()
        self.current_step = 0
        self.start_time = time.time()

    def next_step(self) -> None:
        """Move to the next step."""
        if self.current_step < len(self.steps):
            self._complete_current()
            self.current_step += 1
            if self.current_step < len(self.steps):
                self._start_current()

    def _complete_current(self) -> None:
        """Mark current step as complete."""
        if self.current_step < len(self.steps):
            step = self.steps[self.current_step]
            self.console.print(f"[green]✓[/green] {step}")

    def _start_current(self) -> None:
        """Start the current step."""
        if self.current_step < len(self.steps):
            step = self.steps[self.current_step]
            self.console.print(f"[yellow]→[/yellow] {step}...")

    def complete_all(self) -> None:
        """Mark all remaining steps as complete."""
        while self.current_step < len(self.steps):
            self.next_step()

        elapsed = time.time() - self.start_time
        self.console.print(f"\n[green]All steps completed in {elapsed:.1f}s[/green]")
