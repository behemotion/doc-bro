"""
Progress reporting utilities for upload operations

Provides progress tracking and reporting including:
- Rich-based progress bars
- Real-time upload status updates
- Multi-operation progress aggregation
- Error and warning tracking
- CLI-friendly progress display
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any

from rich.console import Console
from rich.progress import (
    BarColumn,
    DownloadColumn,
    Progress,
    SpinnerColumn,
    TaskID,
    TextColumn,
    TimeRemainingColumn,
    TransferSpeedColumn,
)
from rich.table import Table

logger = logging.getLogger(__name__)

logger = logging.getLogger(__name__)


@dataclass
class ProgressUpdate:
    """Single progress update event"""
    operation_id: str
    files_processed: int
    files_total: int
    bytes_processed: int
    bytes_total: int
    current_file: str | None = None
    stage: str = "processing"  # validating, downloading, processing, complete, error
    timestamp: datetime = field(default_factory=datetime.now)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class OperationSummary:
    """Summary of completed operation"""
    operation_id: str
    start_time: datetime
    end_time: datetime
    files_processed: int
    files_total: int
    bytes_processed: int
    bytes_total: int
    success: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def duration(self) -> timedelta:
        return self.end_time - self.start_time

    @property
    def success_rate(self) -> float:
        if self.files_total == 0:
            return 0.0
        return self.files_processed / self.files_total


class UploadProgressReporter:
    """Progress reporter specifically for upload operations"""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()
        self.operations: dict[str, dict[str, Any]] = {}
        self.active_progress: Progress | None = None
        self.task_mapping: dict[str, TaskID] = {}

    async def start_operation(
        self,
        operation_id: str,
        description: str,
        total_files: int = 0,
        total_bytes: int = 0
    ) -> None:
        """Start tracking a new upload operation"""
        try:
            self.operations[operation_id] = {
                "description": description,
                "start_time": datetime.now(),
                "total_files": total_files,
                "total_bytes": total_bytes,
                "current_files": 0,
                "current_bytes": 0,
                "current_file": None,
                "stage": "initializing",
                "active": True,
                "errors": [],
                "warnings": []
            }

            # Initialize progress bar if not already active
            if not self.active_progress:
                self.active_progress = Progress(
                    SpinnerColumn(),
                    TextColumn("[progress.description]{task.description}"),
                    BarColumn(),
                    "[progress.percentage]{task.percentage:>3.1f}%",
                    "•",
                    DownloadColumn(),
                    "•",
                    TransferSpeedColumn(),
                    "•",
                    TimeRemainingColumn(),
                    console=self.console,
                    expand=True
                )
                self.active_progress.start()

            # Add task to progress bar
            task_id = self.active_progress.add_task(
                description=description,
                total=total_bytes if total_bytes > 0 else total_files
            )
            self.task_mapping[operation_id] = task_id

            logger.info(f"Started upload operation: {operation_id} - {description}")

        except Exception as e:
            logger.error(f"Error starting operation {operation_id}: {e}")

    async def update_progress(self, update: ProgressUpdate) -> None:
        """Update progress for an operation"""
        try:
            if update.operation_id not in self.operations:
                logger.warning(f"Unknown operation ID: {update.operation_id}")
                return

            op = self.operations[update.operation_id]

            # Update operation data
            op["current_files"] = update.files_processed
            op["current_bytes"] = update.bytes_processed
            op["current_file"] = update.current_file
            op["stage"] = update.stage
            op["errors"].extend(update.errors)
            op["warnings"].extend(update.warnings)

            # Update totals if they've changed
            if update.files_total > 0:
                op["total_files"] = update.files_total
            if update.bytes_total > 0:
                op["total_bytes"] = update.bytes_total

            # Update progress bar
            if self.active_progress and update.operation_id in self.task_mapping:
                task_id = self.task_mapping[update.operation_id]

                # Calculate completed amount
                if op["total_bytes"] > 0:
                    completed = update.bytes_processed
                    total = op["total_bytes"]
                else:
                    completed = update.files_processed
                    total = op["total_files"]

                # Update task description with current file
                description = op["description"]
                if update.current_file:
                    filename = update.current_file.split('/')[-1]  # Get just filename
                    if len(filename) > 30:
                        filename = f"...{filename[-27:]}"
                    description = f"{op['description']} • {filename}"

                self.active_progress.update(
                    task_id,
                    completed=completed,
                    total=max(total, completed),  # Ensure total is not less than completed
                    description=description
                )

        except Exception as e:
            logger.error(f"Error updating progress for {update.operation_id}: {e}")

    async def complete_operation(
        self,
        operation_id: str,
        success: bool,
        message: str | None = None
    ) -> OperationSummary:
        """Complete an operation and return summary"""
        try:
            if operation_id not in self.operations:
                logger.warning(f"Unknown operation ID: {operation_id}")
                return None

            op = self.operations[operation_id]
            op["active"] = False
            op["end_time"] = datetime.now()
            op["success"] = success

            # Remove from progress bar
            if self.active_progress and operation_id in self.task_mapping:
                task_id = self.task_mapping[operation_id]

                if success:
                    # Complete the task
                    total = op["total_bytes"] if op["total_bytes"] > 0 else op["total_files"]
                    self.active_progress.update(task_id, completed=total)

                    # Update description to show completion
                    description = f"✓ {op['description']} - Complete"
                    self.active_progress.update(task_id, description=description)
                else:
                    # Mark as failed
                    description = f"✗ {op['description']} - Failed"
                    self.active_progress.update(task_id, description=description)

                # Remove task after brief delay
                await asyncio.sleep(1)
                self.active_progress.remove_task(task_id)
                del self.task_mapping[operation_id]

            # Stop progress if no more active operations
            if not any(op["active"] for op in self.operations.values()):
                if self.active_progress:
                    self.active_progress.stop()
                    self.active_progress = None

            # Create summary
            summary = OperationSummary(
                operation_id=operation_id,
                start_time=op["start_time"],
                end_time=op["end_time"],
                files_processed=op["current_files"],
                files_total=op["total_files"],
                bytes_processed=op["current_bytes"],
                bytes_total=op["total_bytes"],
                success=success,
                errors=op["errors"].copy(),
                warnings=op["warnings"].copy()
            )

            if message:
                if success:
                    self.console.print(f"[green]✓[/green] {message}")
                else:
                    self.console.print(f"[red]✗[/red] {message}")

            logger.info(f"Completed operation: {operation_id} - Success: {success}")
            return summary

        except Exception as e:
            logger.error(f"Error completing operation {operation_id}: {e}")
            return None

    async def show_error(
        self,
        error: str,
        suggestions: list[str] | None = None,
        operation_id: str | None = None
    ) -> None:
        """Display error with optional suggestions"""
        try:
            if operation_id and operation_id in self.operations:
                self.operations[operation_id]["errors"].append(error)

            # Display error
            self.console.print(f"[red]Error:[/red] {error}")

            # Display suggestions if provided
            if suggestions:
                self.console.print("\n[yellow]Suggestions:[/yellow]")
                for suggestion in suggestions:
                    self.console.print(f"  • {suggestion}")

        except Exception as e:
            logger.error(f"Error displaying error message: {e}")

    async def show_warning(
        self,
        warning: str,
        operation_id: str | None = None
    ) -> None:
        """Display warning message"""
        try:
            if operation_id and operation_id in self.operations:
                self.operations[operation_id]["warnings"].append(warning)

            self.console.print(f"[yellow]Warning:[/yellow] {warning}")

        except Exception as e:
            logger.error(f"Error displaying warning message: {e}")

    def get_operation_status(self, operation_id: str) -> dict[str, Any] | None:
        """Get current status of an operation"""
        return self.operations.get(operation_id)

    def get_all_operations(self) -> dict[str, dict[str, Any]]:
        """Get status of all operations"""
        return self.operations.copy()

    def get_active_operations(self) -> dict[str, dict[str, Any]]:
        """Get only active operations"""
        return {
            op_id: op for op_id, op in self.operations.items()
            if op.get("active", False)
        }

    async def show_operation_summary(self, summary: OperationSummary) -> None:
        """Display detailed operation summary"""
        try:
            # Create summary table
            table = Table(title=f"Upload Summary - {summary.operation_id}")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green" if summary.success else "red")

            # Add metrics
            table.add_row("Status", "Success" if summary.success else "Failed")
            table.add_row("Files Processed", f"{summary.files_processed}/{summary.files_total}")
            table.add_row("Data Processed", self._format_bytes(summary.bytes_processed))
            table.add_row("Success Rate", f"{summary.success_rate:.1%}")
            table.add_row("Duration", str(summary.duration).split('.')[0])  # Remove microseconds

            if summary.bytes_processed > 0 and summary.duration.total_seconds() > 0:
                rate = summary.bytes_processed / summary.duration.total_seconds()
                table.add_row("Average Speed", f"{self._format_bytes(rate)}/s")

            # Display table
            self.console.print(table)

            # Show errors and warnings
            if summary.errors:
                self.console.print(f"\n[red]Errors ({len(summary.errors)}):[/red]")
                for error in summary.errors[:5]:  # Show max 5 errors
                    self.console.print(f"  • {error}")
                if len(summary.errors) > 5:
                    self.console.print(f"  ... and {len(summary.errors) - 5} more")

            if summary.warnings:
                self.console.print(f"\n[yellow]Warnings ({len(summary.warnings)}):[/yellow]")
                for warning in summary.warnings[:3]:  # Show max 3 warnings
                    self.console.print(f"  • {warning}")
                if len(summary.warnings) > 3:
                    self.console.print(f"  ... and {len(summary.warnings) - 3} more")

        except Exception as e:
            logger.error(f"Error showing operation summary: {e}")

    def _format_bytes(self, bytes_count: int) -> str:
        """Format bytes for human-readable display"""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} PB"

    async def cleanup(self) -> None:
        """Clean up resources"""
        try:
            if self.active_progress:
                self.active_progress.stop()
                self.active_progress = None

            self.task_mapping.clear()
            self.operations.clear()

        except Exception as e:
            logger.error(f"Error during cleanup: {e}")


class SimpleProgressReporter:
    """Simplified progress reporter for basic operations"""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()

    async def report_file_progress(
        self,
        filename: str,
        processed: int,
        total: int,
        stage: str = "processing"
    ) -> None:
        """Report progress for a single file"""
        percentage = (processed / total * 100) if total > 0 else 0
        size_str = f"{self._format_bytes(processed)}/{self._format_bytes(total)}"

        self.console.print(
            f"[cyan]{stage.title()}:[/cyan] {filename} - {percentage:.1f}% ({size_str})"
        )

    async def report_operation_complete(
        self,
        operation: str,
        files_count: int,
        success: bool = True
    ) -> None:
        """Report completion of an operation"""
        status = "[green]✓[/green]" if success else "[red]✗[/red]"
        self.console.print(f"{status} {operation} - {files_count} files")

    def _format_bytes(self, bytes_count: int) -> str:
        """Format bytes for human-readable display"""
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} TB"
