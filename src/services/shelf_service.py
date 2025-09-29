"""Service for managing shelfs (collections of baskets)."""

import logging
from datetime import datetime
from typing import List, Optional
from uuid import uuid4

from src.models.shelf import Shelf, ShelfExistsError, ShelfNotFoundError, ShelfValidationError
from src.services.database import DatabaseManager

logger = logging.getLogger(__name__)


class ShelfService:
    """Service for managing shelfs."""

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
        set_current: bool = False,
        force: bool = False
    ) -> Shelf:
        """Create a new shelf.

        Args:
            name: Name of the shelf
            description: Optional description
            set_current: Whether to set as current shelf
            force: Force creation even if shelf exists

        Returns:
            Created shelf

        Raises:
            ShelfExistsError: If shelf already exists and force is False
            ShelfValidationError: If shelf validation fails
        """
        await self.initialize()

        # Check if shelf exists
        existing = await self.get_shelf_by_name(name)
        if existing and not force:
            raise ShelfExistsError(f"Shelf '{name}' already exists")

        if existing and force:
            # Remove existing shelf
            await self.remove_shelf(existing.id, force=True)

        # Create shelf model
        shelf = Shelf(
            id=f"shelf-{uuid4().hex[:12]}",
            name=name,
            is_current=set_current
        )

        if description:
            shelf.add_metadata("description", description)

        # If setting as current, unset other shelfs
        if set_current:
            await self._unset_all_current()

        # Insert into database
        async with self.db._conn.execute(
            """
            INSERT INTO shelfs (id, name, created_at, updated_at, is_current, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                shelf.id,
                shelf.name,
                shelf.created_at.isoformat(),
                shelf.updated_at.isoformat(),
                shelf.is_current,
                self.db._json_dumps(shelf.metadata)
            )
        ) as cursor:
            await self.db._conn.commit()

        logger.info(f"Created shelf: {shelf.name} (id={shelf.id})")
        return shelf

    async def get_shelf(self, shelf_id: str) -> Optional[Shelf]:
        """Get shelf by ID.

        Args:
            shelf_id: Shelf ID

        Returns:
            Shelf if found, None otherwise
        """
        await self.initialize()

        async with self.db._conn.execute(
            """
            SELECT id, name, created_at, updated_at, is_current, metadata_json
            FROM shelfs
            WHERE id = ?
            """,
            (shelf_id,)
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            return None

        # Get basket count
        async with self.db._conn.execute(
            "SELECT COUNT(*) FROM baskets WHERE shelf_id = ?",
            (shelf_id,)
        ) as cursor:
            count_row = await cursor.fetchone()
            basket_count = count_row[0] if count_row else 0

        return self._row_to_shelf(row, basket_count)

    async def get_shelf_by_name(self, name: str) -> Optional[Shelf]:
        """Get shelf by name.

        Args:
            name: Shelf name

        Returns:
            Shelf if found, None otherwise
        """
        await self.initialize()

        async with self.db._conn.execute(
            """
            SELECT id, name, created_at, updated_at, is_current, metadata_json
            FROM shelfs
            WHERE name = ?
            """,
            (name,)
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            return None

        shelf_id = row[0]

        # Get basket count
        async with self.db._conn.execute(
            "SELECT COUNT(*) FROM baskets WHERE shelf_id = ?",
            (shelf_id,)
        ) as cursor:
            count_row = await cursor.fetchone()
            basket_count = count_row[0] if count_row else 0

        return self._row_to_shelf(row, basket_count)

    async def list_shelfs(
        self,
        verbose: bool = False,
        current_only: bool = False,
        limit: Optional[int] = None
    ) -> List[Shelf]:
        """List all shelfs.

        Args:
            verbose: Include detailed information
            current_only: Only return current shelf
            limit: Maximum number of shelfs to return

        Returns:
            List of shelfs
        """
        await self.initialize()

        query = "SELECT id, name, created_at, updated_at, is_current, metadata_json FROM shelfs"
        params = []

        if current_only:
            query += " WHERE is_current = 1"

        query += " ORDER BY created_at DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        async with self.db._conn.execute(query, params) as cursor:
            rows = await cursor.fetchall()

        shelfs = []
        for row in rows:
            shelf_id = row[0]

            # Get basket count for each shelf
            async with self.db._conn.execute(
                "SELECT COUNT(*) FROM baskets WHERE shelf_id = ?",
                (shelf_id,)
            ) as count_cursor:
                count_row = await count_cursor.fetchone()
                basket_count = count_row[0] if count_row else 0

            shelf = self._row_to_shelf(row, basket_count)

            if verbose:
                # Load baskets for verbose mode
                async with self.db._conn.execute(
                    "SELECT id, name, type, status FROM baskets WHERE shelf_id = ?",
                    (shelf_id,)
                ) as basket_cursor:
                    basket_rows = await basket_cursor.fetchall()
                    shelf.baskets = [
                        {"id": b[0], "name": b[1], "type": b[2], "status": b[3]}
                        for b in basket_rows
                    ]

            shelfs.append(shelf)

        return shelfs

    async def get_current_shelf(self) -> Optional[Shelf]:
        """Get the current active shelf.

        Returns:
            Current shelf if set, None otherwise
        """
        await self.initialize()

        async with self.db._conn.execute(
            """
            SELECT id, name, created_at, updated_at, is_current, metadata_json
            FROM shelfs
            WHERE is_current = 1
            LIMIT 1
            """
        ) as cursor:
            row = await cursor.fetchone()

        if not row:
            return None

        shelf_id = row[0]

        # Get basket count
        async with self.db._conn.execute(
            "SELECT COUNT(*) FROM baskets WHERE shelf_id = ?",
            (shelf_id,)
        ) as cursor:
            count_row = await cursor.fetchone()
            basket_count = count_row[0] if count_row else 0

        return self._row_to_shelf(row, basket_count)

    async def set_current_shelf(self, shelf_id: str) -> Shelf:
        """Set a shelf as current.

        Args:
            shelf_id: Shelf ID to set as current

        Returns:
            Updated shelf

        Raises:
            ShelfNotFoundError: If shelf not found
        """
        await self.initialize()

        shelf = await self.get_shelf(shelf_id)
        if not shelf:
            raise ShelfNotFoundError(f"Shelf with ID '{shelf_id}' not found")

        # Unset all current shelfs
        await self._unset_all_current()

        # Set this shelf as current
        async with self.db._conn.execute(
            "UPDATE shelfs SET is_current = 1, updated_at = ? WHERE id = ?",
            (datetime.utcnow().isoformat(), shelf_id)
        ):
            await self.db._conn.commit()

        shelf.set_current()
        logger.info(f"Set current shelf: {shelf.name} (id={shelf.id})")
        return shelf

    async def update_shelf(
        self,
        shelf_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        metadata: Optional[dict] = None
    ) -> Shelf:
        """Update a shelf.

        Args:
            shelf_id: Shelf ID
            name: New name
            description: New description
            metadata: Additional metadata to merge

        Returns:
            Updated shelf

        Raises:
            ShelfNotFoundError: If shelf not found
        """
        await self.initialize()

        shelf = await self.get_shelf(shelf_id)
        if not shelf:
            raise ShelfNotFoundError(f"Shelf with ID '{shelf_id}' not found")

        updates = []
        params = []

        if name:
            # Validate new name
            test_shelf = Shelf(name=name)  # This will validate
            updates.append("name = ?")
            params.append(name)
            shelf.name = name

        if description is not None:
            shelf.add_metadata("description", description)

        if metadata:
            for key, value in metadata.items():
                shelf.add_metadata(key, value)

        if updates or description is not None or metadata:
            updates.append("metadata_json = ?")
            params.append(self.db._json_dumps(shelf.metadata))
            updates.append("updated_at = ?")
            params.append(datetime.utcnow().isoformat())
            params.append(shelf_id)

            query = f"UPDATE shelfs SET {', '.join(updates)} WHERE id = ?"
            async with self.db._conn.execute(query, params):
                await self.db._conn.commit()

            logger.info(f"Updated shelf: {shelf.name} (id={shelf.id})")

        return shelf

    async def remove_shelf(
        self,
        shelf_id: str,
        force: bool = False,
        backup: bool = True
    ) -> bool:
        """Remove a shelf.

        Args:
            shelf_id: Shelf ID
            force: Force removal even if shelf has baskets
            backup: Create backup before removal

        Returns:
            True if removed

        Raises:
            ShelfNotFoundError: If shelf not found
            ValueError: If shelf has baskets and force is False
        """
        await self.initialize()

        shelf = await self.get_shelf(shelf_id)
        if not shelf:
            raise ShelfNotFoundError(f"Shelf with ID '{shelf_id}' not found")

        # Check for baskets
        if shelf.basket_count > 0 and not force:
            raise ValueError(
                f"Shelf '{shelf.name}' has {shelf.basket_count} baskets. "
                "Use force=True to remove anyway."
            )

        if backup:
            # TODO: Implement backup functionality
            logger.info(f"Creating backup of shelf: {shelf.name}")

        # Delete shelf (cascade will delete baskets)
        async with self.db._conn.execute(
            "DELETE FROM shelfs WHERE id = ?",
            (shelf_id,)
        ):
            await self.db._conn.commit()

        logger.info(f"Removed shelf: {shelf.name} (id={shelf.id})")
        return True

    async def _unset_all_current(self) -> None:
        """Unset current flag on all shelfs."""
        async with self.db._conn.execute(
            "UPDATE shelfs SET is_current = 0, updated_at = ? WHERE is_current = 1",
            (datetime.utcnow().isoformat(),)
        ):
            await self.db._conn.commit()

    def _row_to_shelf(self, row: tuple, basket_count: int = 0) -> Shelf:
        """Convert database row to Shelf model."""
        return Shelf(
            id=row[0],
            name=row[1],
            created_at=datetime.fromisoformat(row[2]),
            updated_at=datetime.fromisoformat(row[3]),
            is_current=bool(row[4]),
            metadata=self.db._json_loads(row[5]) if row[5] else {},
            basket_count=basket_count
        )

    async def close(self) -> None:
        """Close database connection."""
        await self.db.close()