"""CLI command for unified fill operation in the Shelf-Box Rhyme System."""

import asyncio
import logging
from typing import Optional

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn

from src.models.box import BoxNotFoundError
from src.services.fill_service import FillService
from src.services.box_service import BoxService
from src.services.shelf_service import ShelfService
from src.services.database import DatabaseError
from src.core.lib_logger import get_component_logger

logger = get_component_logger("fill_cli")
console = Console()


@click.command()
@click.argument('box', type=str)
@click.option('--source', '-s', type=str, required=True, help='Source URL or path')
@click.option('--shelf', type=str, help='Shelf context (uses current if not specified)')
# Drag-specific options (website crawling)
@click.option('--max-pages', type=int, help='Maximum pages to crawl (drag boxes)')
@click.option('--rate-limit', type=float, help='Requests per second (drag boxes)')
@click.option('--depth', type=int, help='Crawl depth (drag boxes)')
# Rag-specific options (document import)
@click.option('--chunk-size', type=int, help='Text chunk size (rag boxes)')
@click.option('--overlap', type=int, help='Chunk overlap (rag boxes)')
# Bag-specific options (file storage)
@click.option('--recursive', '-r', is_flag=True, help='Include subdirectories (bag boxes)')
@click.option('--pattern', type=str, help='File pattern filter (bag boxes)')
def fill(
    box: str,
    source: str,
    shelf: Optional[str] = None,
    max_pages: Optional[int] = None,
    rate_limit: Optional[float] = None,
    depth: Optional[int] = None,
    chunk_size: Optional[int] = None,
    overlap: Optional[int] = None,
    recursive: bool = False,
    pattern: Optional[str] = None
):
    """Add content to a box (unified crawl/upload)."""

    async def _fill():
        try:
            fill_service = FillService()
            box_service = BoxService()
            shelf_service = ShelfService()

            # Ensure current shelf context if not specified
            if not shelf:
                current = await shelf_service.get_current_shelf()
                if not current:
                    console.print("[red]No current shelf set. Use 'docbro shelf current <name>' to set one.[/red]")
                    raise click.Abort()
                shelf = current.name

            # Get box info to show what we're doing
            box_obj = await box_service.get_box_by_name(box)
            if not box_obj:
                console.print(f"[red]Box '{box}' not found[/red]")
                raise click.Abort()

            # Prepare type-specific options
            options = {}

            if max_pages is not None:
                options['max_pages'] = max_pages
            if rate_limit is not None:
                options['rate_limit'] = rate_limit
            if depth is not None:
                options['depth'] = depth
            if chunk_size is not None:
                options['chunk_size'] = chunk_size
            if overlap is not None:
                options['overlap'] = overlap
            if recursive:
                options['recursive'] = recursive
            if pattern is not None:
                options['pattern'] = pattern

            # Show what we're about to do
            operation_messages = {
                'drag': f"[blue]Crawling {source} into drag box '{box}'...[/blue]",
                'rag': f"[blue]Importing {source} into rag box '{box}'...[/blue]",
                'bag': f"[blue]Storing {source} into bag box '{box}'...[/blue]"
            }

            console.print(operation_messages.get(box_obj.type.value, f"[blue]Filling {box_obj.type.value} box '{box}'...[/blue]"))

            # Show relevant options
            if options:
                console.print("[dim]Options:[/dim]")
                for key, value in options.items():
                    console.print(f"  [dim]{key}: {value}[/dim]")

            # Execute fill operation with progress indication
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task("Processing...", total=None)

                result = await fill_service.fill(
                    box_name=box,
                    source=source,
                    shelf_name=shelf,
                    **options
                )

                progress.stop()

            # Show results
            if result['success']:
                console.print(f"[green]Successfully filled box '{box}'[/green]")

                # Show operation-specific details
                if result.get('operation'):
                    console.print(f"  Operation: {result['operation']}")

                # Show some stats if available
                stats_shown = False
                for stat_key in ['max_pages', 'chunk_size', 'pattern']:
                    if stat_key in result:
                        if not stats_shown:
                            console.print("  Settings applied:")
                            stats_shown = True
                        console.print(f"    {stat_key}: {result[stat_key]}")

            else:
                error_msg = result.get('error', 'Unknown error')
                console.print(f"[red]Failed to fill: {error_msg}[/red]")
                raise click.Abort()

        except BoxNotFoundError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise click.Abort()
        except DatabaseError as e:
            console.print(f"[red]Failed to fill: {e}[/red]")
            raise click.Abort()
        except Exception as e:
            console.print(f"[red]Failed to fill box: {e}[/red]")
            raise click.Abort()

    asyncio.run(_fill())