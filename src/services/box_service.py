"""Service for managing boxes in the Shelf-Box Rhyme System."""

import json
import logging
from datetime import datetime
from typing import List, Optional, Dict, Any

from src.models.box import Box, BoxExistsError, BoxNotFoundError, BoxValidationError
from src.models.box_type import BoxType
from src.services.database import DatabaseManager, DatabaseError
from src.core.lib_logger import get_component_logger

logger = get_component_logger("box_service")


class BoxService:
    """
    Service for managing boxes (documentation units).

    Provides CRUD operations for boxes and implements protection rules
    such as preventing deletion of protected boxes and last box in shelf.
    """

    def __init__(self, database: Optional[DatabaseManager] = None):
        """Initialize box service."""
        self.db = database or DatabaseManager()

    async def initialize(self) -> None:
        """Initialize the box service."""
        if not self.db._initialized:
            await self.db.initialize()

    async def create_box(
        self,
        name: str,
        box_type: str | BoxType,
        shelf_name: Optional[str] = None,
        description: Optional[str] = None,
        **kwargs
    ) -> Box:
        """
        Create a new box.

        Args:
            name: Name of the box (globally unique)
            box_type: Type of box (drag/rag/bag)
            shelf_name: Optional shelf to add box to
            description: Optional description
            **kwargs: Additional box configuration (url, max_pages, etc.)

        Returns:
            Created box model

        Raises:
            BoxExistsError: If box with same name already exists
            BoxValidationError: If box data is invalid
        """
        await self.initialize()

        try:
            # Normalize box type
            if isinstance(box_type, str):
                box_type = BoxType.from_string(box_type)

            # Validate box data using model
            box_data = {
                'name': name,
                'type': box_type,
                **kwargs
            }
            box_model = Box(**box_data)

            # Create box in database
            box_id = await self.db.create_box(
                name=name,
                box_type=box_type.value,
                **kwargs
            )

            # Add to shelf if specified
            if shelf_name:
                # Get shelf ID
                shelf_data = await self.db.get_shelf(name=shelf_name)
                if shelf_data:
                    await self.db.add_box_to_shelf(shelf_data['id'], box_id)

            # Return created box
            return await self.get_box_by_id(box_id)

        except DatabaseError as e:
            if "already exists" in str(e):
                raise BoxExistsError(f"Box with name '{name}' already exists")
            raise

    async def get_box_by_name(self, name: str) -> Optional[Box]:
        """
        Get box by name.

        Args:
            name: Name of the box

        Returns:
            Box model or None if not found
        """
        await self.initialize()

        box_data = await self.db.get_box(name=name)
        if box_data:
            return Box.model_validate(box_data)

        return None

    async def get_box_by_id(self, box_id: str) -> Optional[Box]:
        """
        Get box by ID.

        Args:
            box_id: ID of the box

        Returns:
            Box model or None if not found
        """
        await self.initialize()

        box_data = await self.db.get_box(box_id=box_id)
        if box_data:
            return Box.model_validate(box_data)

        return None

    async def list_boxes(
        self,
        shelf_name: Optional[str] = None,
        box_type: Optional[str | BoxType] = None
    ) -> List[Box]:
        """
        List boxes with optional filtering.

        Args:
            shelf_name: Filter by shelf name
            box_type: Filter by box type

        Returns:
            List of box models
        """
        await self.initialize()

        shelf_id = None
        if shelf_name:
            shelf_data = await self.db.get_shelf(name=shelf_name)
            if shelf_data:
                shelf_id = shelf_data['id']
            else:
                return []  # Shelf doesn't exist, no boxes

        type_filter = None
        if box_type:
            if isinstance(box_type, str):
                box_type = BoxType.from_string(box_type)
            type_filter = box_type.value

        boxes_data = await self.db.list_boxes(shelf_id=shelf_id, box_type=type_filter)
        boxes = []

        for box_data in boxes_data:
            boxes.append(Box.model_validate(box_data))

        return boxes

    async def add_box_to_shelf(self, box_name: str, shelf_name: str) -> bool:
        """
        Add existing box to a shelf.

        Args:
            box_name: Name of the box
            shelf_name: Name of the shelf

        Returns:
            True if added successfully

        Raises:
            BoxNotFoundError: If box not found
            DatabaseError: If shelf not found or other error
        """
        await self.initialize()

        # Get box
        box = await self.get_box_by_name(box_name)
        if not box:
            raise BoxNotFoundError(f"Box '{box_name}' not found")

        # Get shelf
        shelf_data = await self.db.get_shelf(name=shelf_name)
        if not shelf_data:
            raise DatabaseError(f"Shelf '{shelf_name}' not found")

        # Add box to shelf
        success = await self.db.add_box_to_shelf(shelf_data['id'], box.id)
        if success:
            logger.info(f"Added box '{box_name}' to shelf '{shelf_name}'")

        return success

    async def remove_box_from_shelf(self, box_name: str, shelf_name: str) -> bool:
        """
        Remove box from a shelf.

        Implements protection rule: cannot remove last box from shelf.

        Args:
            box_name: Name of the box
            shelf_name: Name of the shelf

        Returns:
            True if removed successfully

        Raises:
            BoxNotFoundError: If box not found
            DatabaseError: If shelf not found, last box protection, or other error
        """
        await self.initialize()

        # Get box
        box = await self.get_box_by_name(box_name)
        if not box:
            raise BoxNotFoundError(f"Box '{box_name}' not found")

        # Get shelf
        shelf_data = await self.db.get_shelf(name=shelf_name)
        if not shelf_data:
            raise DatabaseError(f"Shelf '{shelf_name}' not found")

        # Remove box from shelf (database handles last box protection)
        try:
            success = await self.db.remove_box_from_shelf(shelf_data['id'], box.id)
            if success:
                logger.info(f"Removed box '{box_name}' from shelf '{shelf_name}'")

            return success

        except DatabaseError as e:
            if "last box" in str(e):
                raise DatabaseError("Cannot remove last box from shelf")
            raise

    async def rename_box(self, old_name: str, new_name: str) -> Box:
        """
        Rename a box.

        Args:
            old_name: Current name of the box
            new_name: New name for the box

        Returns:
            Updated box model

        Raises:
            BoxNotFoundError: If box not found
            BoxExistsError: If new name already exists
            BoxValidationError: If new name is invalid
        """
        await self.initialize()

        # Validate new name
        Box(name=new_name, type=BoxType.RAG)  # This will raise if invalid

        # Check if old box exists
        box = await self.get_box_by_name(old_name)
        if not box:
            raise BoxNotFoundError(f"Box '{old_name}' not found")

        # Check if new name already exists
        existing = await self.get_box_by_name(new_name)
        if existing:
            raise BoxExistsError(f"Box with name '{new_name}' already exists")

        # Update in database
        try:
            conn = self.db._connection
            await conn.execute(
                "UPDATE boxes SET name = ?, updated_at = ? WHERE id = ?",
                (new_name, datetime.utcnow().isoformat(), box.id)
            )
            await conn.commit()

            # Return updated box
            return await self.get_box_by_id(box.id)

        except Exception as e:
            raise DatabaseError(f"Failed to rename box: {e}")

    async def delete_box(self, name: str, force: bool = False) -> bool:
        """
        Delete a box.

        Implements protection rules:
        - Cannot delete protected boxes

        Args:
            name: Name of the box to delete
            force: Force deletion (currently not used for protected items)

        Returns:
            True if deleted successfully

        Raises:
            BoxNotFoundError: If box not found
            DatabaseError: If box is protected or other error
        """
        await self.initialize()

        box = await self.get_box_by_name(name)
        if not box:
            raise BoxNotFoundError(f"Box '{name}' not found")

        # Protection rule: cannot delete protected boxes
        if not box.is_deletable:
            raise DatabaseError("Cannot delete protected box")

        # Delete from database
        success = await self.db.delete_box(box.id)
        if not success:
            raise DatabaseError(f"Failed to delete box: {name}")

        logger.info(f"Deleted box: {name}")
        return True

    async def update_box_settings(
        self,
        name: str,
        settings: Dict[str, Any]
    ) -> Box:
        """
        Update box settings.

        Args:
            name: Name of the box
            settings: Dictionary of settings to update

        Returns:
            Updated box model

        Raises:
            BoxNotFoundError: If box not found
        """
        await self.initialize()

        box = await self.get_box_by_name(name)
        if not box:
            raise BoxNotFoundError(f"Box '{name}' not found")

        # Update settings
        if not box.settings:
            box.settings = {}
        box.settings.update(settings)

        # Update in database
        try:
            conn = self.db._connection
            await conn.execute(
                "UPDATE boxes SET settings = ?, updated_at = ? WHERE id = ?",
                (
                    json.dumps(box.settings) if box.settings else None,
                    datetime.utcnow().isoformat(),
                    box.id
                )
            )
            await conn.commit()

            # Return updated box
            return await self.get_box_by_id(box.id)

        except Exception as e:
            raise DatabaseError(f"Failed to update box settings: {e}")

    async def get_box_stats(self, name: str) -> Dict[str, Any]:
        """
        Get statistics for a box.

        Args:
            name: Name of the box

        Returns:
            Dictionary with box statistics

        Raises:
            BoxNotFoundError: If box not found
        """
        await self.initialize()

        box = await self.get_box_by_name(name)
        if not box:
            raise BoxNotFoundError(f"Box '{name}' not found")

        # Get shelves containing this box
        shelves_data = await self.db.list_shelves()
        containing_shelves = []

        for shelf_data in shelves_data:
            shelf_boxes = await self.db.list_boxes(shelf_id=shelf_data['id'])
            for shelf_box in shelf_boxes:
                if shelf_box['id'] == box.id:
                    containing_shelves.append(shelf_data['name'])
                    break

        return {
            'name': box.name,
            'id': box.id,
            'type': box.type.value,
            'is_deletable': box.is_deletable,
            'url': box.url,
            'settings': box.settings or {},
            'containing_shelves': containing_shelves,
            'shelf_count': len(containing_shelves),
            'created_at': box.created_at,
            'updated_at': box.updated_at
        }