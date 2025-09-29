"""CLI commands for shelf management."""

import asyncio
import logging
from datetime import datetime
from typing import Optional

import click
from rich.console import Console
from rich.table import Table

from src.models.shelf import ShelfExistsError, ShelfValidationError, ShelfNotFoundError
from src.services.shelf_service import ShelfService

logger = logging.getLogger(__name__)
console = Console()


class ShelfCommands:
    """Commands for shelf management."""

    def __init__(self, shelf_service: Optional[ShelfService] = None):
        """Initialize shelf commands."""
        self.shelf_service = shelf_service or ShelfService()

    async def create_shelf(
        self,
        name: str,
        description: Optional[str] = None,
        set_current: bool = False,
        force: bool = False
    ) -> dict:
        """Create a new shelf.

        Args:
            name: Name of the shelf
            description: Optional description
            set_current: Whether to set as current shelf
            force: Force creation even if shelf exists

        Returns:
            Result dictionary with success status and details
        """
        try:
            shelf = await self.shelf_service.create_shelf(
                name=name,
                description=description,
                set_current=set_current,
                force=force
            )

            return {
                "success": True,
                "shelf_name": shelf.name,
                "message": f"Shelf '{shelf.name}' created successfully with default basket created",
                "is_current": shelf.is_current,
                "description": description,
                "details": {
                    "shelf_id": shelf.id,
                    "created_at": shelf.created_at.isoformat(),
                    "is_current": shelf.is_current,
                    "default_basket_created": True
                }
            }

        except ShelfExistsError as e:
            return {
                "success": False,
                "error": "shelf_exists",
                "message": f"Shelf '{name}' already exists. Use --force to overwrite.",
                "shelf_name": name
            }

        except ShelfValidationError as e:
            return {
                "success": False,
                "error": "invalid_shelf_name",
                "message": f"Invalid shelf name: {str(e)}".lower()
            }

        except Exception as e:
            logger.error(f"Failed to create shelf: {e}")
            return {
                "success": False,
                "error": "creation_error",
                "message": f"Failed to create shelf: {str(e)}"
            }

    async def list_shelfs(
        self,
        verbose: bool = False,
        current_only: bool = False,
        limit: Optional[int] = None
    ) -> dict:
        """List shelfs.

        Args:
            verbose: Include detailed information
            current_only: Only show current shelf
            limit: Maximum number of shelfs to return

        Returns:
            Result dictionary with shelf list
        """
        try:
            shelfs = await self.shelf_service.list_shelfs(
                verbose=verbose,
                current_only=current_only,
                limit=limit
            )

            current_shelf = await self.shelf_service.get_current_shelf()
            current_shelf_name = current_shelf.name if current_shelf else None

            if not shelfs:
                return {
                    "success": True,
                    "shelfs": [],
                    "total_shelfs": 0,
                    "current_shelf": None,
                    "message": "No shelfs found"
                }

            shelf_data = []
            table_rows = []

            for shelf in shelfs:
                data = {
                    "name": shelf.name,
                    "is_current": shelf.is_current,
                    "created_at": shelf.created_at.isoformat(),
                    "basket_count": shelf.basket_count
                }

                if verbose:
                    data["created_at"] = shelf.created_at.isoformat()
                    data["updated_at"] = shelf.updated_at.isoformat()
                    data["basket_count"] = shelf.basket_count
                    data["metadata"] = shelf.metadata
                    if shelf.baskets:
                        data["baskets"] = shelf.baskets

                shelf_data.append(data)

                # Table row for display
                table_rows.append([
                    shelf.name,
                    str(shelf.basket_count),
                    "✓" if shelf.is_current else "",
                    shelf.created_at.strftime("%Y-%m-%d %H:%M")
                ])

            result = {
                "success": True,
                "shelfs": shelf_data,
                "total_shelfs": len(shelfs),
                "current_shelf": current_shelf_name,
                "message": f"Found {len(shelfs)} shelf(s)"
            }

            if verbose:
                result["verbose"] = True

            if limit:
                result["limit_applied"] = limit

            # Add table format for display
            result["table_format"] = {
                "headers": ["Name", "Baskets", "Current", "Created"],
                "rows": table_rows
            }

            return result

        except Exception as e:
            logger.error(f"Failed to list shelfs: {e}")
            return {
                "success": False,
                "error": "database_error",
                "message": "Failed to retrieve shelf list",
                "details": {
                    "error_message": str(e)
                }
            }

    async def remove_shelf(
        self,
        name: str,
        force: bool = False,
        backup: bool = True
    ) -> dict:
        """Remove a shelf.

        Args:
            name: Name of the shelf to remove
            force: Force removal even if shelf has baskets
            backup: Create backup before removal

        Returns:
            Result dictionary
        """
        try:
            shelf = await self.shelf_service.get_shelf_by_name(name)
            if not shelf:
                return {
                    "success": False,
                    "error": "shelf_not_found",
                    "message": f"Shelf '{name}' not found"
                }

            await self.shelf_service.remove_shelf(
                shelf_id=shelf.id,
                force=force,
                backup=backup
            )

            return {
                "success": True,
                "message": f"Shelf '{name}' removed successfully",
                "details": {
                    "backed_up": backup,
                    "baskets_removed": shelf.basket_count
                }
            }

        except ValueError as e:
            return {
                "success": False,
                "error": "has_baskets",
                "message": str(e)
            }

        except Exception as e:
            logger.error(f"Failed to remove shelf: {e}")
            return {
                "success": False,
                "error": "removal_error",
                "message": f"Failed to remove shelf: {str(e)}"
            }

    async def set_current_shelf(self, name: str) -> dict:
        """Set a shelf as current.

        Args:
            name: Name of the shelf

        Returns:
            Result dictionary
        """
        try:
            shelf = await self.shelf_service.get_shelf_by_name(name)
            if not shelf:
                return {
                    "success": False,
                    "error": "shelf_not_found",
                    "message": f"Shelf '{name}' not found"
                }

            shelf = await self.shelf_service.set_current_shelf(shelf.id)

            return {
                "success": True,
                "message": f"Set current shelf to '{shelf.name}'",
                "shelf_name": shelf.name
            }

        except Exception as e:
            logger.error(f"Failed to set current shelf: {e}")
            return {
                "success": False,
                "error": "set_current_error",
                "message": f"Failed to set current shelf: {str(e)}"
            }


@click.group(name="shelf")
def shelf_group():
    """Manage documentation shelfs (collections)."""
    pass


@shelf_group.command(name="create")
@click.argument("name")
@click.option("--description", "-d", help="Shelf description")
@click.option("--set-current", "-c", is_flag=True, help="Set as current shelf")
@click.option("--force", "-f", is_flag=True, help="Force creation if exists")
def create_shelf_cmd(name: str, description: Optional[str], set_current: bool, force: bool):
    """Create a new shelf."""
    commands = ShelfCommands()
    result = asyncio.run(commands.create_shelf(name, description, set_current, force))

    if result["success"]:
        console.print(f"✅ {result['message']}", style="green")
        if result.get("is_current"):
            console.print("   Set as current shelf", style="dim")
    else:
        console.print(f"❌ {result['message']}", style="red")


@shelf_group.command(name="list")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
@click.option("--current-only", "-c", is_flag=True, help="Show only current shelf")
@click.option("--limit", "-l", type=int, help="Maximum number of shelfs to show")
def list_shelfs_cmd(verbose: bool, current_only: bool, limit: Optional[int]):
    """List all shelfs."""
    commands = ShelfCommands()
    result = asyncio.run(commands.list_shelfs(verbose, current_only, limit))

    if not result["success"]:
        console.print(f"❌ {result['message']}", style="red")
        return

    if result["total_shelfs"] == 0:
        console.print("No shelfs found. Create one with 'docbro shelf create <name>'", style="yellow")
        return

    # Display table
    table = Table(title="Documentation Shelfs")
    for header in result["table_format"]["headers"]:
        table.add_column(header)

    for row in result["table_format"]["rows"]:
        table.add_row(*row)

    console.print(table)

    if result.get("current_shelf"):
        console.print(f"\nCurrent shelf: {result['current_shelf']}", style="cyan")


@shelf_group.command(name="remove")
@click.argument("name")
@click.option("--force", "-f", is_flag=True, help="Force removal even if shelf has baskets")
@click.option("--no-backup", is_flag=True, help="Skip backup creation")
def remove_shelf_cmd(name: str, force: bool, no_backup: bool):
    """Remove a shelf."""
    commands = ShelfCommands()
    result = asyncio.run(commands.remove_shelf(name, force, not no_backup))

    if result["success"]:
        console.print(f"✅ {result['message']}", style="green")
    else:
        console.print(f"❌ {result['message']}", style="red")


@shelf_group.command(name="current")
@click.argument("name", required=False)
def set_current_shelf_cmd(name: Optional[str]):
    """Get or set current shelf."""
    commands = ShelfCommands()

    if name:
        # Set current shelf
        result = asyncio.run(commands.set_current_shelf(name))
        if result["success"]:
            console.print(f"✅ {result['message']}", style="green")
        else:
            console.print(f"❌ {result['message']}", style="red")
    else:
        # Get current shelf
        result = asyncio.run(commands.list_shelfs(current_only=True))
        if result["success"] and result["shelfs"]:
            shelf = result["shelfs"][0]
            console.print(f"Current shelf: {shelf['name']}", style="cyan")
            console.print(f"  Baskets: {shelf['basket_count']}")
            console.print(f"  Created: {shelf['created_at']}")
        else:
            console.print("No current shelf set", style="yellow")