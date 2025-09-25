"""Simple crawl progress display service."""

from typing import Optional
from rich.console import Console
from rich.live import Live
from rich.table import Table
from rich.panel import Panel


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

        return Panel(
            table,
            title=f"[bold cyan]Crawling {self.project_name}[/bold cyan]",
            border_style="cyan"
        )

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()