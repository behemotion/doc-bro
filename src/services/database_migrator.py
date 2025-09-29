"""Database migration service for DocBro."""

import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
import json
import uuid

from src.core.config import DocBroConfig
from src.core.lib_logger import get_component_logger
from src.models.box_type import BoxType


class DatabaseMigrator:
    """Handles database schema migrations."""

    def __init__(self, config: Optional[DocBroConfig] = None):
        """Initialize database migrator."""
        self.config = config or DocBroConfig()
        self.db_path = self.config.database_path
        self.logger = get_component_logger("database_migrator")

    def get_current_version(self, conn: sqlite3.Connection) -> int:
        """Get current schema version."""
        try:
            cursor = conn.execute("SELECT version FROM schema_version ORDER BY version DESC LIMIT 1")
            row = cursor.fetchone()
            return row[0] if row else 0
        except sqlite3.Error:
            return 0

    def migrate_to_version_5(self, conn: sqlite3.Connection) -> None:
        """Migrate to version 5: Add shelf-box rhyme system tables."""
        self.logger.info("Migrating database to version 5: Shelf-Box Rhyme System")

        # Create shelves table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shelves (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                is_default BOOLEAN DEFAULT FALSE,
                is_deletable BOOLEAN DEFAULT TRUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Create boxes table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS boxes (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                type TEXT NOT NULL CHECK (type IN ('drag', 'rag', 'bag')),
                is_deletable BOOLEAN DEFAULT TRUE,
                url TEXT,
                max_pages INTEGER,
                rate_limit REAL,
                crawl_depth INTEGER,
                settings TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
        """)

        # Create shelf_boxes junction table
        conn.execute("""
            CREATE TABLE IF NOT EXISTS shelf_boxes (
                shelf_id TEXT NOT NULL,
                box_id TEXT NOT NULL,
                position INTEGER,
                added_at TEXT NOT NULL,
                PRIMARY KEY (shelf_id, box_id),
                FOREIGN KEY (shelf_id) REFERENCES shelves(id) ON DELETE CASCADE,
                FOREIGN KEY (box_id) REFERENCES boxes(id) ON DELETE CASCADE
            )
        """)

        # Create indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shelves_name ON shelves(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shelves_is_default ON shelves(is_default)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_boxes_name ON boxes(name)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_boxes_type ON boxes(type)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shelf_boxes_shelf_id ON shelf_boxes(shelf_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_shelf_boxes_box_id ON shelf_boxes(box_id)")

        # Create global_settings table if it doesn't exist and add current_shelf
        conn.execute("""
            CREATE TABLE IF NOT EXISTS global_settings (
                id INTEGER PRIMARY KEY DEFAULT 1,
                current_shelf TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Add current_shelf column if it doesn't exist
        try:
            conn.execute("ALTER TABLE global_settings ADD COLUMN current_shelf TEXT")
        except sqlite3.OperationalError:
            # Column might already exist
            pass

        # Create default data
        self._create_default_shelf_data(conn)

        # Update schema version
        conn.execute("INSERT OR REPLACE INTO schema_version (version) VALUES (5)")
        conn.commit()

        self.logger.info("Migration to version 5 completed successfully")

    def _create_default_shelf_data(self, conn: sqlite3.Connection) -> None:
        """Create default shelf and box."""
        now = datetime.utcnow().isoformat()

        # Create default "common shelf"
        shelf_id = str(uuid.uuid4())
        conn.execute("""
            INSERT OR IGNORE INTO shelves (id, name, is_default, is_deletable, created_at, updated_at)
            VALUES (?, ?, TRUE, FALSE, ?, ?)
        """, (shelf_id, "common shelf", now, now))

        # Create default "new year" box
        box_id = str(uuid.uuid4())
        conn.execute("""
            INSERT OR IGNORE INTO boxes (id, name, type, is_deletable, created_at, updated_at)
            VALUES (?, ?, 'bag', FALSE, ?, ?)
        """, (box_id, "new year", now, now))

        # Add box to shelf
        conn.execute("""
            INSERT OR IGNORE INTO shelf_boxes (shelf_id, box_id, position, added_at)
            VALUES (?, ?, 1, ?)
        """, (shelf_id, box_id, now))

        # Set as current shelf in global settings
        try:
            conn.execute("""
                UPDATE global_settings SET current_shelf = ?
            """, (shelf_id,))
        except sqlite3.OperationalError:
            # Global settings might not exist yet
            pass

    def run_migrations(self) -> None:
        """Run all pending migrations."""
        conn = sqlite3.connect(self.db_path)
        try:
            current_version = self.get_current_version(conn)
            target_version = 5

            if current_version < target_version:
                self.logger.info(f"Migrating database from version {current_version} to {target_version}")

                # Run migrations in sequence
                if current_version < 5:
                    self.migrate_to_version_5(conn)

                self.logger.info(f"Database migrated to version {target_version}")
            else:
                self.logger.debug(f"Database already at version {current_version}")

        finally:
            conn.close()