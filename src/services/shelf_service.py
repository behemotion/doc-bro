"""Service for managing shelves in the Shelf-Box Rhyme System."""

import logging
from datetime import datetime, timezone
from typing import List, Optional

from src.models.shelf import Shelf, ShelfExistsError, ShelfNotFoundError, ShelfValidationError
from src.models.box_type import BoxType
from src.services.database import DatabaseManager, DatabaseError
from src.core.lib_logger import get_component_logger

logger = get_component_logger("shelf_service")


class ShelfService:
    """
    Service for managing shelves (collections of boxes).

    Provides CRUD operations for shelves and implements protection rules
    such as preventing deletion of the default shelf.
    """

    def __init__(self, database: Optional[DatabaseManager] = None):
        """Initialize shelf service."""
        self.db = database or DatabaseManager()

    async def initialize(self) -> None:
        """Initialize the shelf service."""
        if not self.db._initialized:
            await self.db.initialize()

    async def create_shelf(
        self,
        name: str,
        description: Optional[str] = None,
        set_current: bool = False
    ) -> Shelf:
        """
        Create a new shelf with auto-generated default box.

        Args:
            name: Name of the shelf
            description: Optional description for metadata
            set_current: Whether to set as current shelf

        Returns:
            Created shelf model

        Raises:
            ShelfExistsError: If shelf with same name already exists
            ShelfValidationError: If shelf name is invalid
        """
        await self.initialize()

        try:
            # Validate shelf name using model
            shelf_model = Shelf(name=name)

            # Create shelf in database
            shelf_id = await self.db.create_shelf(name)

            # Create default box for this shelf
            default_box_name = f"{name}_box"
            box_id = await self.db.create_box(default_box_name, BoxType.RAG.value)

            # Add box to shelf
            await self.db.add_box_to_shelf(shelf_id, box_id)

            # Set as current if requested
            if set_current:
                await self.db.set_current_shelf(shelf_id)

            # Get created shelf with box count
            shelf_data = await self.db.get_shelf(shelf_id=shelf_id)
            if shelf_data:
                shelf_data['box_count'] = 1  # We just added one box
                return Shelf.model_validate(shelf_data)

            raise ShelfNotFoundError(f"Failed to retrieve created shelf: {name}")

        except DatabaseError as e:
            if "already exists" in str(e):
                raise ShelfExistsError(f"Shelf with name '{name}' already exists")
            raise

    async def get_shelf_by_name(self, name: str) -> Optional[Shelf]:
        """
        Get shelf by name.

        Args:
            name: Name of the shelf

        Returns:
            Shelf model or None if not found
        """
        await self.initialize()

        shelf_data = await self.db.get_shelf(name=name)
        if shelf_data:
            # Get box count for this shelf
            boxes = await self.db.list_boxes(shelf_id=shelf_data['id'])
            shelf_data['box_count'] = len(boxes)
            return Shelf.model_validate(shelf_data)

        return None

    async def get_shelf_by_id(self, shelf_id: str) -> Optional[Shelf]:
        """
        Get shelf by ID.

        Args:
            shelf_id: ID of the shelf

        Returns:
            Shelf model or None if not found
        """
        await self.initialize()

        shelf_data = await self.db.get_shelf(shelf_id=shelf_id)
        if shelf_data:
            # Get box count for this shelf
            boxes = await self.db.list_boxes(shelf_id=shelf_data['id'])
            shelf_data['box_count'] = len(boxes)
            return Shelf.model_validate(shelf_data)

        return None

    async def list_shelves(self) -> List[Shelf]:
        """
        List all shelves.

        Returns:
            List of shelf models with box counts
        """
        await self.initialize()

        shelves_data = await self.db.list_shelves()
        shelves = []

        for shelf_data in shelves_data:
            # Box count is already included in the query
            shelves.append(Shelf.model_validate(shelf_data))

        return shelves

    async def get_current_shelf(self) -> Optional[Shelf]:
        """
        Get the current active shelf.

        Returns:
            Current shelf model or None if no current shelf set
        """
        await self.initialize()

        current_shelf_id = await self.db.get_current_shelf_id()
        if current_shelf_id:
            return await self.get_shelf_by_id(current_shelf_id)

        return None

    async def set_current_shelf(self, name: str) -> Shelf:
        """
        Set the current active shelf.

        Args:
            name: Name of the shelf to set as current

        Returns:
            Updated shelf model

        Raises:
            ShelfNotFoundError: If shelf not found
        """
        await self.initialize()

        shelf = await self.get_shelf_by_name(name)
        if not shelf:
            raise ShelfNotFoundError(f"Shelf '{name}' not found")

        success = await self.db.set_current_shelf(shelf.id)
        if not success:
            raise DatabaseError(f"Failed to set current shelf: {name}")

        return shelf

    async def rename_shelf(self, old_name: str, new_name: str) -> Shelf:
        """
        Rename a shelf.

        Args:
            old_name: Current name of the shelf
            new_name: New name for the shelf

        Returns:
            Updated shelf model

        Raises:
            ShelfNotFoundError: If shelf not found
            ShelfExistsError: If new name already exists
            ShelfValidationError: If new name is invalid
        """
        await self.initialize()

        # Validate new name
        Shelf(name=new_name)  # This will raise if invalid

        # Check if old shelf exists
        shelf = await self.get_shelf_by_name(old_name)
        if not shelf:
            raise ShelfNotFoundError(f"Shelf '{old_name}' not found")

        # Check if new name already exists
        existing = await self.get_shelf_by_name(new_name)
        if existing:
            raise ShelfExistsError(f"Shelf with name '{new_name}' already exists")

        # Update in database
        try:
            conn = self.db._connection
            await conn.execute(
                "UPDATE shelves SET name = ?, updated_at = ? WHERE id = ?",
                (new_name, datetime.now(timezone.utc).isoformat(), shelf.id)
            )
            await conn.commit()

            # Return updated shelf
            return await self.get_shelf_by_id(shelf.id)

        except Exception as e:
            raise DatabaseError(f"Failed to rename shelf: {e}")

    async def delete_shelf(self, name: str, force: bool = False) -> bool:
        """
        Delete a shelf.

        Implements protection rules:
        - Cannot delete default shelf
        - Cannot delete if only shelf exists (to be implemented)

        Args:
            name: Name of the shelf to delete
            force: Force deletion (currently not used for protected items)

        Returns:
            True if deleted successfully

        Raises:
            ShelfNotFoundError: If shelf not found
            DatabaseError: If shelf is protected or other error
        """
        await self.initialize()

        shelf = await self.get_shelf_by_name(name)
        if not shelf:
            raise ShelfNotFoundError(f"Shelf '{name}' not found")

        # Protection rule: cannot delete default shelf
        if shelf.is_default:
            raise DatabaseError("Cannot delete default shelf")

        # Delete from database
        success = await self.db.delete_shelf(shelf.id)
        if not success:
            raise DatabaseError(f"Failed to delete shelf: {name}")

        logger.info(f"Deleted shelf: {name}")
        return True

    async def ensure_current_shelf(self) -> Shelf:
        """
        Ensure there is a current shelf set.

        If no current shelf is set, sets the default shelf as current.
        If no default shelf exists, creates one.

        Returns:
            Current shelf model
        """
        await self.initialize()

        current = await self.get_current_shelf()
        if current:
            return current

        # Look for default shelf
        shelves = await self.list_shelves()
        default_shelf = None
        for shelf in shelves:
            if shelf.is_default:
                default_shelf = shelf
                break

        if default_shelf:
            await self.db.set_current_shelf(default_shelf.id)
            return default_shelf

        # If no default shelf exists, something is wrong
        # This should have been created during migration
        raise DatabaseError("No default shelf found in system")

    async def get_shelf_stats(self, name: str) -> dict:
        """
        Get statistics for a shelf.

        Args:
            name: Name of the shelf

        Returns:
            Dictionary with shelf statistics

        Raises:
            ShelfNotFoundError: If shelf not found
        """
        await self.initialize()

        shelf = await self.get_shelf_by_name(name)
        if not shelf:
            raise ShelfNotFoundError(f"Shelf '{name}' not found")

        # Get boxes in this shelf
        boxes = await self.db.list_boxes(shelf_id=shelf.id)

        # Count by type
        type_counts = {'drag': 0, 'rag': 0, 'bag': 0}
        for box in boxes:
            box_type = box.get('type', 'unknown')
            if box_type in type_counts:
                type_counts[box_type] += 1

        return {
            'name': shelf.name,
            'id': shelf.id,
            'is_default': shelf.is_default,
            'box_count': len(boxes),
            'box_types': type_counts,
            'created_at': shelf.created_at,
            'updated_at': shelf.updated_at
        }