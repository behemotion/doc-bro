"""CLI commands for shelf management in the Shelf-Box Rhyme System."""

import asyncio
import logging
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.text import Text

from src.models.shelf import ShelfExistsError, ShelfValidationError, ShelfNotFoundError
from src.services.shelf_service import ShelfService
from src.services.database import DatabaseError
from src.core.lib_logger import get_component_logger

logger = get_component_logger("shelf_cli")
console = Console()


@click.group()
def shelf():
    """Manage documentation shelves (collections)."""
    pass


@shelf.command()
@click.argument('name', type=str)
@click.option('--description', '-d', type=str, help='Shelf description')
@click.option('--set-current', '-c', is_flag=True, help='Set as current shelf')
def create(name: str, description: Optional[str] = None, set_current: bool = False):
    """Create a new shelf."""

    async def _create():
        try:
            shelf_service = ShelfService()

            shelf = await shelf_service.create_shelf(
                name=name,
                description=description,
                set_current=set_current
            )

            console.print(f"[green]Created shelf '{name}'[/green]")

            if set_current:
                console.print(f"[blue]Set as current shelf[/blue]")

            # Show created shelf info
            console.print(f"  Auto-created: {name}_box (rag)")
            console.print(f"  Boxes: 1")

        except ShelfExistsError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise click.Abort()
        except ShelfValidationError as e:
            console.print(f"[red]Invalid name: {e}[/red]")
            raise click.Abort()
        except Exception as e:
            console.print(f"[red]Failed to create shelf: {e}[/red]")
            raise click.Abort()

    asyncio.run(_create())


@shelf.command()
@click.option('--verbose', '-v', is_flag=True, help='Show detailed information')
@click.option('--current-only', is_flag=True, help='Show only current shelf')
@click.option('--limit', type=int, default=10, help='Maximum shelves to display')
def list(verbose: bool = False, current_only: bool = False, limit: int = 10):
    """List all shelves."""

    async def _list():
        try:
            shelf_service = ShelfService()

            if current_only:
                current_shelf = await shelf_service.get_current_shelf()
                if current_shelf:
                    shelves = [current_shelf]
                else:
                    console.print("[yellow]No current shelf set[/yellow]")
                    return
            else:
                shelves = await shelf_service.list_shelves()

            if not shelves:
                console.print("[yellow]No shelves found[/yellow]")
                return

            # Apply limit
            if len(shelves) > limit:
                shelves = shelves[:limit]
                console.print(f"[dim]Showing first {limit} shelves[/dim]")

            # Create table
            table = Table(show_header=True, header_style="bold blue")
            table.add_column("Name", style="cyan")
            table.add_column("Boxes", justify="center")
            table.add_column("Current", justify="center")
            table.add_column("Created", style="dim")

            if verbose:
                table.add_column("ID", style="dim")
                table.add_column("Default", justify="center")

            # Get current shelf for marking
            current_shelf = await shelf_service.get_current_shelf()
            current_shelf_id = current_shelf.id if current_shelf else None

            for shelf in shelves:
                # Format current marker
                is_current = shelf.id == current_shelf_id
                current_marker = "→" if is_current else ""

                # Format created date
                created_date = shelf.created_at.strftime("%Y-%m-%d")

                row = [
                    shelf.name,
                    str(shelf.box_count),
                    current_marker,
                    created_date
                ]

                if verbose:
                    row.extend([
                        shelf.id[:12] + "...",
                        "✓" if shelf.is_default else ""
                    ])

                table.add_row(*row)

            console.print(table)

        except Exception as e:
            console.print(f"[red]Failed to list shelves: {e}[/red]")
            raise click.Abort()

    asyncio.run(_list())


@shelf.command()
@click.argument('name', type=str, required=False)
def current(name: Optional[str] = None):
    """Get or set current shelf."""

    async def _current():
        try:
            shelf_service = ShelfService()

            if name:
                # Set current shelf
                shelf = await shelf_service.set_current_shelf(name)
                console.print(f"[green]Set current shelf to '{name}'[/green]")
            else:
                # Get current shelf
                current_shelf = await shelf_service.get_current_shelf()
                if current_shelf:
                    console.print(f"Current shelf: [cyan]{current_shelf.name}[/cyan]")
                else:
                    console.print("[yellow]No current shelf set[/yellow]")

        except ShelfNotFoundError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise click.Abort()
        except Exception as e:
            console.print(f"[red]Failed to get/set current shelf: {e}[/red]")
            raise click.Abort()

    asyncio.run(_current())


@shelf.command()
@click.argument('old_name', type=str)
@click.argument('new_name', type=str)
def rename(old_name: str, new_name: str):
    """Rename a shelf."""

    async def _rename():
        try:
            shelf_service = ShelfService()

            shelf = await shelf_service.rename_shelf(old_name, new_name)
            console.print(f"[green]Renamed shelf '{old_name}' to '{new_name}'[/green]")

        except ShelfNotFoundError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise click.Abort()
        except ShelfExistsError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise click.Abort()
        except ShelfValidationError as e:
            console.print(f"[red]Invalid name: {e}[/red]")
            raise click.Abort()
        except Exception as e:
            console.print(f"[red]Failed to rename shelf: {e}[/red]")
            raise click.Abort()

    asyncio.run(_rename())


@shelf.command()
@click.argument('name', type=str)
@click.option('--force', '-f', is_flag=True, help='Skip confirmation')
@click.option('--no-backup', is_flag=True, help="Don't create backup")
def delete(name: str, force: bool = False, no_backup: bool = False):
    """Delete a shelf."""

    async def _delete():
        try:
            shelf_service = ShelfService()

            # Get shelf info first
            shelf = await shelf_service.get_shelf_by_name(name)
            if not shelf:
                console.print(f"[red]Shelf '{name}' not found[/red]")
                raise click.Abort()

            # Check protection
            if shelf.is_default:
                console.print(f"[red]Cannot delete: Default shelf is protected[/red]")
                raise click.Abort()

            # Confirmation
            if not force:
                box_warning = f" (contains {shelf.box_count} boxes)" if shelf.box_count > 0 else ""
                confirm = click.confirm(
                    f"Delete shelf '{name}'{box_warning}?",
                    default=False
                )
                if not confirm:
                    console.print("[yellow]Cancelled[/yellow]")
                    return

            # TODO: Implement backup if not no_backup

            # Delete shelf
            await shelf_service.delete_shelf(name)
            console.print(f"[green]Deleted shelf '{name}'[/green]")

        except DatabaseError as e:
            if "protected" in str(e) or "default" in str(e):
                console.print(f"[red]Cannot delete: {e}[/red]")
            else:
                console.print(f"[red]Failed to delete shelf: {e}[/red]")
            raise click.Abort()
        except Exception as e:
            console.print(f"[red]Failed to delete shelf: {e}[/red]")
            raise click.Abort()

    asyncio.run(_delete())