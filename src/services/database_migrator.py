"""Database migration service for schema evolution and project compatibility."""

import json
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import aiosqlite

from src.core.config import DocBroConfig
from src.core.lib_logger import get_component_logger
from src.models.compatibility_status import CompatibilityStatus
from src.models.migration_record import MigrationOperation, ProjectMigrationRecord
from src.models.schema_version import SchemaVersion


class MigrationError(Exception):
    """Database migration operation error."""
    pass


class DatabaseMigrator:
    """Handles database schema migrations and project compatibility updates."""

    def __init__(self, config: DocBroConfig | None = None):
        """Initialize database migrator."""
        self.config = config or DocBroConfig()
        self.db_path = self.config.database_path
        self.logger = get_component_logger("database_migrator")

        # Migration scripts for each version
        self.migration_scripts = {
            1: self._migration_v1_to_v2,
            2: self._migration_v2_to_v3,
            3: self._migration_v3_to_v4,
        }

    async def check_schema_version(self) -> int:
        """Check current database schema version."""
        try:
            async with aiosqlite.connect(str(self.db_path)) as conn:
                cursor = await conn.execute(
                    "SELECT version FROM schema_version ORDER BY version DESC LIMIT 1"
                )
                row = await cursor.fetchone()
                return row[0] if row else 0
        except Exception as e:
            self.logger.warning(f"Could not determine schema version: {e}")
            return 0

    async def migrate_to_latest(self) -> Dict[str, Any]:
        """Migrate database to latest schema version."""
        current_version = await self.check_schema_version()
        target_version = SchemaVersion.get_current_version()

        if current_version >= target_version:
            return {
                "success": True,
                "current_version": current_version,
                "target_version": target_version,
                "migrations_applied": 0,
                "message": "Database is already at latest version"
            }

        self.logger.info(f"Starting migration from version {current_version} to {target_version}")

        migrations_applied = 0
        try:
            # Apply migrations sequentially
            for version in range(current_version + 1, target_version + 1):
                if version in self.migration_scripts:
                    await self.migration_scripts[version]()
                    migrations_applied += 1
                    self.logger.info(f"Applied migration to version {version}")
                else:
                    self.logger.warning(f"No migration script found for version {version}")

            # Update schema version
            await self._update_schema_version(target_version)

            return {
                "success": True,
                "current_version": target_version,
                "target_version": target_version,
                "migrations_applied": migrations_applied,
                "message": f"Successfully migrated from version {current_version} to {target_version}"
            }

        except Exception as e:
            self.logger.error(f"Migration failed: {e}")
            return {
                "success": False,
                "current_version": await self.check_schema_version(),
                "target_version": target_version,
                "migrations_applied": migrations_applied,
                "error": str(e)
            }

    async def detect_incompatible_projects(self) -> List[Dict[str, Any]]:
        """Detect projects that are incompatible with current schema."""
        incompatible_projects = []

        try:
            async with aiosqlite.connect(str(self.db_path)) as conn:
                # Check if projects table exists and has schema_version column
                cursor = await conn.execute(
                    "PRAGMA table_info(projects)"
                )
                columns = await cursor.fetchall()
                column_names = [col[1] for col in columns]

                # If no schema_version column, all projects are incompatible
                if 'schema_version' not in column_names:
                    cursor = await conn.execute(
                        "SELECT id, name, created_at FROM projects"
                    )
                    projects = await cursor.fetchall()

                    for project_id, name, created_at in projects:
                        incompatible_projects.append({
                            "id": project_id,
                            "name": name,
                            "current_schema_version": 1,  # Assume version 1
                            "required_schema_version": SchemaVersion.get_current_version(),
                            "compatibility_status": CompatibilityStatus.INCOMPATIBLE.value,
                            "created_at": created_at,
                            "issues": ["Missing schema_version field", "Old project schema"]
                        })
                else:
                    # Check projects with old schema versions
                    current_version = SchemaVersion.get_current_version()
                    cursor = await conn.execute(
                        "SELECT id, name, schema_version, created_at FROM projects WHERE schema_version < ?",
                        (current_version,)
                    )
                    projects = await cursor.fetchall()

                    for project_id, name, schema_version, created_at in projects:
                        incompatible_projects.append({
                            "id": project_id,
                            "name": name,
                            "current_schema_version": schema_version,
                            "required_schema_version": current_version,
                            "compatibility_status": CompatibilityStatus.INCOMPATIBLE.value,
                            "created_at": created_at,
                            "issues": [f"Schema version {schema_version} is outdated"]
                        })

        except Exception as e:
            self.logger.error(f"Failed to detect incompatible projects: {e}")
            raise MigrationError(f"Failed to detect incompatible projects: {e}")

        self.logger.info(f"Found {len(incompatible_projects)} incompatible projects")
        return incompatible_projects

    async def flag_incompatible_projects(self) -> Dict[str, Any]:
        """Flag all incompatible projects in the database."""
        try:
            incompatible_projects = await self.detect_incompatible_projects()

            if not incompatible_projects:
                return {
                    "success": True,
                    "flagged_count": 0,
                    "message": "No incompatible projects found"
                }

            flagged_count = 0
            async with aiosqlite.connect(str(self.db_path)) as conn:
                # Ensure compatibility_status column exists
                await self._ensure_compatibility_column(conn)

                # Flag each incompatible project
                for project in incompatible_projects:
                    await conn.execute(
                        "UPDATE projects SET compatibility_status = ? WHERE id = ?",
                        (CompatibilityStatus.INCOMPATIBLE.value, project["id"])
                    )
                    flagged_count += 1

                await conn.commit()

            self.logger.info(f"Flagged {flagged_count} incompatible projects")
            return {
                "success": True,
                "flagged_count": flagged_count,
                "projects": incompatible_projects
            }

        except Exception as e:
            self.logger.error(f"Failed to flag incompatible projects: {e}")
            return {
                "success": False,
                "error": str(e),
                "flagged_count": 0
            }

    async def create_migration_record(
        self,
        project_id: str,
        project_name: str,
        operation: MigrationOperation,
        from_version: int,
        to_version: int,
        preserved_settings: Optional[Dict[str, Any]] = None,
        preserved_metadata: Optional[Dict[str, Any]] = None,
        initiated_by_command: str = "migration"
    ) -> ProjectMigrationRecord:
        """Create a new migration record."""
        record = ProjectMigrationRecord(
            project_id=project_id,
            project_name=project_name,
            operation=operation,
            from_schema_version=from_version,
            to_schema_version=to_version,
            preserved_settings=preserved_settings or {},
            preserved_metadata=preserved_metadata or {},
            initiated_by_command=initiated_by_command
        )

        try:
            async with aiosqlite.connect(str(self.db_path)) as conn:
                await conn.execute("""
                    INSERT INTO project_migrations (
                        id, project_id, project_name, operation, from_schema_version,
                        to_schema_version, started_at, preserved_settings_json,
                        preserved_metadata_json, user_initiated, initiated_by_command
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    record.id, record.project_id, record.project_name,
                    record.operation.value, record.from_schema_version,
                    record.to_schema_version, record.started_at.isoformat(),
                    json.dumps(record.preserved_settings),
                    json.dumps(record.preserved_metadata),
                    record.user_initiated, record.initiated_by_command
                ))
                await conn.commit()

            self.logger.info(f"Created migration record for project {project_name}")
            return record

        except Exception as e:
            self.logger.error(f"Failed to create migration record: {e}")
            raise MigrationError(f"Failed to create migration record: {e}")

    async def complete_migration_record(
        self,
        record_id: str,
        success: bool = True,
        error_message: Optional[str] = None,
        data_size_bytes: int = 0
    ) -> None:
        """Mark a migration record as completed."""
        try:
            async with aiosqlite.connect(str(self.db_path)) as conn:
                await conn.execute("""
                    UPDATE project_migrations
                    SET completed_at = ?, success = ?, error_message = ?, data_size_bytes = ?
                    WHERE id = ?
                """, (
                    datetime.utcnow().isoformat(), success, error_message,
                    data_size_bytes, record_id
                ))
                await conn.commit()

            self.logger.info(f"Completed migration record {record_id}, success: {success}")

        except Exception as e:
            self.logger.error(f"Failed to complete migration record: {e}")
            raise MigrationError(f"Failed to complete migration record: {e}")

    async def get_migration_history(
        self,
        project_id: Optional[str] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """Get migration history for a project or all projects."""
        try:
            async with aiosqlite.connect(str(self.db_path)) as conn:
                if project_id:
                    cursor = await conn.execute("""
                        SELECT id, project_id, project_name, operation, from_schema_version,
                               to_schema_version, started_at, completed_at, success,
                               error_message, data_size_bytes, initiated_by_command
                        FROM project_migrations
                        WHERE project_id = ?
                        ORDER BY started_at DESC LIMIT ?
                    """, (project_id, limit))
                else:
                    cursor = await conn.execute("""
                        SELECT id, project_id, project_name, operation, from_schema_version,
                               to_schema_version, started_at, completed_at, success,
                               error_message, data_size_bytes, initiated_by_command
                        FROM project_migrations
                        ORDER BY started_at DESC LIMIT ?
                    """, (limit,))

                rows = await cursor.fetchall()
                return [
                    {
                        "id": row[0],
                        "project_id": row[1],
                        "project_name": row[2],
                        "operation": row[3],
                        "from_schema_version": row[4],
                        "to_schema_version": row[5],
                        "started_at": row[6],
                        "completed_at": row[7],
                        "success": bool(row[8]) if row[8] is not None else None,
                        "error_message": row[9],
                        "data_size_bytes": row[10],
                        "initiated_by_command": row[11]
                    }
                    for row in rows
                ]

        except Exception as e:
            self.logger.error(f"Failed to get migration history: {e}")
            return []

    # Private migration methods

    async def _migration_v1_to_v2(self) -> None:
        """Migrate from version 1 to version 2."""
        self.logger.info("Applying migration from version 1 to version 2")

        async with aiosqlite.connect(str(self.db_path)) as conn:
            # Add compatibility_status column if it doesn't exist
            await self._ensure_compatibility_column(conn)

            # Update all existing projects to have compatibility status
            await conn.execute("""
                UPDATE projects
                SET compatibility_status = ?
                WHERE compatibility_status IS NULL
            """, (CompatibilityStatus.COMPATIBLE.value,))

            await conn.commit()

    async def _migration_v2_to_v3(self) -> None:
        """Migrate from version 2 to version 3 (unified schema)."""
        self.logger.info("Applying migration from version 2 to version 3")

        async with aiosqlite.connect(str(self.db_path)) as conn:
            # Check if we need to restructure the projects table
            cursor = await conn.execute("PRAGMA table_info(projects)")
            columns = await cursor.fetchall()
            column_names = [col[1] for col in columns]

            # If schema_version column doesn't exist, we need to restructure
            if 'schema_version' not in column_names:
                await self._restructure_projects_table(conn)

            # Ensure all required columns exist
            await self._ensure_unified_schema_columns(conn)

            # Update schema version for all projects
            await conn.execute("""
                UPDATE projects
                SET schema_version = 3
                WHERE schema_version IS NULL OR schema_version < 3
            """)

            await conn.commit()

    async def _ensure_compatibility_column(self, conn: aiosqlite.Connection) -> None:
        """Ensure compatibility_status column exists."""
        try:
            await conn.execute("""
                ALTER TABLE projects
                ADD COLUMN compatibility_status TEXT DEFAULT 'compatible'
            """)
            self.logger.info("Added compatibility_status column")
        except sqlite3.OperationalError as e:
            if "duplicate column name" not in str(e).lower():
                raise

    async def _ensure_unified_schema_columns(self, conn: aiosqlite.Connection) -> None:
        """Ensure all unified schema columns exist."""
        required_columns = [
            ("schema_version", "INTEGER NOT NULL DEFAULT 3"),
            ("compatibility_status", "TEXT NOT NULL DEFAULT 'compatible'"),
            ("settings_json", "TEXT NOT NULL DEFAULT '{}'"),
            ("statistics_json", "TEXT NOT NULL DEFAULT '{}'"),
            ("metadata_json", "TEXT NOT NULL DEFAULT '{}'"),
        ]

        for column_name, column_def in required_columns:
            try:
                await conn.execute(f"ALTER TABLE projects ADD COLUMN {column_name} {column_def}")
                self.logger.info(f"Added {column_name} column")
            except sqlite3.OperationalError as e:
                if "duplicate column name" not in str(e).lower():
                    raise

    async def _restructure_projects_table(self, conn: aiosqlite.Connection) -> None:
        """Restructure projects table to unified schema."""
        self.logger.info("Restructuring projects table to unified schema")

        # Create new table with unified schema
        await conn.execute("""
            CREATE TABLE projects_unified (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                schema_version INTEGER NOT NULL DEFAULT 3,
                type TEXT NOT NULL DEFAULT 'crawling',
                status TEXT NOT NULL DEFAULT 'active',
                compatibility_status TEXT NOT NULL DEFAULT 'incompatible',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_crawl_at TEXT,
                source_url TEXT,
                settings_json TEXT NOT NULL DEFAULT '{}',
                statistics_json TEXT NOT NULL DEFAULT '{}',
                metadata_json TEXT NOT NULL DEFAULT '{}'
            )
        """)

        # Migrate data from old table if it exists
        try:
            cursor = await conn.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects'")
            if await cursor.fetchone():
                # Get old table structure
                cursor = await conn.execute("PRAGMA table_info(projects)")
                old_columns = await cursor.fetchall()
                old_column_names = [col[1] for col in old_columns]

                # Build migration query based on available columns
                if 'crawl_depth' in old_column_names:
                    # Old crawler schema - convert to unified
                    await conn.execute("""
                        INSERT INTO projects_unified (
                            id, name, type, status, created_at, updated_at,
                            last_crawl_at, source_url, settings_json, statistics_json, metadata_json
                        )
                        SELECT
                            id, name, 'crawling', status, created_at, updated_at,
                            last_crawl_at, source_url,
                            json_object(
                                'crawl_depth', crawl_depth,
                                'embedding_model', embedding_model,
                                'chunk_size', chunk_size,
                                'chunk_overlap', chunk_overlap
                            ),
                            json_object(
                                'total_pages', total_pages,
                                'successful_pages', successful_pages,
                                'failed_pages', failed_pages,
                                'total_size_bytes', total_size_bytes
                            ),
                            COALESCE(metadata, '{}')
                        FROM projects
                    """)
                else:
                    # Simple project schema - convert to unified
                    await conn.execute("""
                        INSERT INTO projects_unified (
                            id, name, type, status, created_at, updated_at,
                            settings_json, metadata_json
                        )
                        SELECT
                            id, name,
                            COALESCE(type, 'data'),
                            COALESCE(status, 'active'),
                            created_at, updated_at,
                            COALESCE(settings, '{}'),
                            COALESCE(metadata, '{}')
                        FROM projects
                    """)

                # Drop old table
                await conn.execute("DROP TABLE projects")
        except Exception as e:
            self.logger.warning(f"Could not migrate old projects data: {e}")

        # Rename new table
        await conn.execute("ALTER TABLE projects_unified RENAME TO projects")

        # Create indexes
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_name ON projects(name)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_type ON projects(type)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_status ON projects(status)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_compatibility ON projects(compatibility_status)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_projects_schema_version ON projects(schema_version)")

    async def _update_schema_version(self, version: int) -> None:
        """Update the schema version in the database."""
        async with aiosqlite.connect(str(self.db_path)) as conn:
            await conn.execute(
                "INSERT OR REPLACE INTO schema_version (version) VALUES (?)",
                (version,)
            )
            await conn.commit()
            self.logger.info(f"Updated schema version to {version}")

    async def _migration_v3_to_v4(self) -> None:
        """Migrate from version 3 to version 4 (shelf/basket system)."""
        self.logger.info("Applying migration from version 3 to version 4 (shelf/basket system)")

        async with aiosqlite.connect(str(self.db_path)) as conn:
            # Create backup before migration
            await self._create_migration_backup(conn, "v3_to_v4")

            # Create shelf and basket tables
            await self._create_shelf_basket_tables(conn)

            # Create default shelf for existing projects
            default_shelf_id = await self._create_default_shelf(conn)

            # Migrate existing projects to baskets
            await self._migrate_projects_to_baskets(conn, default_shelf_id)

            # Validate migration
            await self._validate_shelf_basket_migration(conn)

            # Create indexes
            await self._create_shelf_basket_indexes(conn)

            await conn.commit()
            self.logger.info("Successfully completed v3 to v4 migration")

    async def _create_migration_backup(self, conn: aiosqlite.Connection, migration_name: str) -> None:
        """Create backup before major migration."""
        backup_timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{migration_name}_backup_{backup_timestamp}.db"
        backup_path = self.config.data_dir / "backups" / backup_name

        # Ensure backup directory exists
        backup_path.parent.mkdir(parents=True, exist_ok=True)

        # Create backup using SQLite backup API
        backup_conn = sqlite3.connect(str(backup_path))
        conn._conn.backup(backup_conn)
        backup_conn.close()

        self.logger.info(f"Created migration backup at {backup_path}")

    async def _create_shelf_basket_tables(self, conn: aiosqlite.Connection) -> None:
        """Create shelf and basket tables."""
        # Create shelfs table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS shelfs (
                id TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                is_current BOOLEAN DEFAULT FALSE,
                metadata_json TEXT DEFAULT '{}'
            )
        """)

        # Create baskets table
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS baskets (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                shelf_id TEXT NOT NULL,
                type TEXT NOT NULL DEFAULT 'data',
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                last_operation_at TEXT,

                -- Preserve all existing project fields
                status TEXT NOT NULL DEFAULT 'created',
                source_url TEXT,
                crawl_depth INTEGER DEFAULT 2,
                embedding_model TEXT DEFAULT 'mxbai-embed-large',
                chunk_size INTEGER DEFAULT 1000,
                chunk_overlap INTEGER DEFAULT 100,

                -- Statistics
                total_pages INTEGER DEFAULT 0,
                total_size_bytes INTEGER DEFAULT 0,
                successful_pages INTEGER DEFAULT 0,
                failed_pages INTEGER DEFAULT 0,

                -- Configuration
                settings_json TEXT NOT NULL DEFAULT '{}',
                metadata_json TEXT NOT NULL DEFAULT '{}',

                -- Schema compatibility
                schema_version INTEGER DEFAULT 4,
                compatibility_status TEXT DEFAULT 'compatible',

                FOREIGN KEY (shelf_id) REFERENCES shelfs (id) ON DELETE CASCADE,
                UNIQUE(shelf_id, name)
            )
        """)

        self.logger.info("Created shelf and basket tables")

    async def _create_default_shelf(self, conn: aiosqlite.Connection) -> str:
        """Create default shelf for migrated projects."""
        import uuid

        shelf_id = str(uuid.uuid4())
        current_time = datetime.utcnow().isoformat()

        await conn.execute("""
            INSERT INTO shelfs (id, name, created_at, updated_at, is_current, metadata_json)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            shelf_id,
            "default",
            current_time,
            current_time,
            True,
            json.dumps({
                "description": "Default shelf for migrated projects",
                "migration_source": "v3_projects",
                "auto_created": True
            })
        ))

        self.logger.info(f"Created default shelf with ID: {shelf_id}")
        return shelf_id

    async def _migrate_projects_to_baskets(self, conn: aiosqlite.Connection, default_shelf_id: str) -> None:
        """Migrate existing projects to baskets in default shelf."""
        # Get all existing projects
        cursor = await conn.execute("SELECT * FROM projects")
        projects = await cursor.fetchall()

        if not projects:
            self.logger.info("No projects found to migrate")
            return

        # Get column names
        cursor = await conn.execute("PRAGMA table_info(projects)")
        columns = await cursor.fetchall()
        column_names = [col[1] for col in columns]

        migrated_count = 0
        for project_row in projects:
            # Convert row to dictionary
            project = dict(zip(column_names, project_row))

            # Determine basket type based on project characteristics
            basket_type = "data"  # default
            if project.get("source_url"):
                basket_type = "crawling"

            # Extract statistics from settings_json if available
            settings = {}
            statistics = {}
            metadata = {}

            try:
                if project.get("settings_json"):
                    settings = json.loads(project["settings_json"])
                if project.get("statistics_json"):
                    statistics = json.loads(project["statistics_json"])
                if project.get("metadata_json"):
                    metadata = json.loads(project["metadata_json"])
            except json.JSONDecodeError as e:
                self.logger.warning(f"Failed to parse JSON for project {project['name']}: {e}")

            # Create basket entry
            await conn.execute("""
                INSERT INTO baskets (
                    id, name, shelf_id, type, status, source_url,
                    created_at, updated_at, last_operation_at,
                    crawl_depth, embedding_model, chunk_size, chunk_overlap,
                    total_pages, total_size_bytes, successful_pages, failed_pages,
                    settings_json, metadata_json, schema_version, compatibility_status
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project["id"],
                project["name"],
                default_shelf_id,
                basket_type,
                project.get("status", "created"),
                project.get("source_url"),
                project["created_at"],
                project["updated_at"],
                project.get("last_crawl_at"),
                settings.get("crawl_depth", 2),
                settings.get("embedding_model", "mxbai-embed-large"),
                settings.get("chunk_size", 1000),
                settings.get("chunk_overlap", 100),
                statistics.get("total_pages", 0),
                statistics.get("total_size_bytes", 0),
                statistics.get("successful_pages", 0),
                statistics.get("failed_pages", 0),
                project.get("settings_json", "{}"),
                project.get("metadata_json", "{}"),
                4,  # New schema version
                "migrated"
            ))

            migrated_count += 1

        self.logger.info(f"Migrated {migrated_count} projects to baskets")

    async def _validate_shelf_basket_migration(self, conn: aiosqlite.Connection) -> None:
        """Validate the shelf/basket migration."""
        # Check shelf count
        cursor = await conn.execute("SELECT COUNT(*) FROM shelfs")
        shelf_count = (await cursor.fetchone())[0]

        # Check basket count
        cursor = await conn.execute("SELECT COUNT(*) FROM baskets")
        basket_count = (await cursor.fetchone())[0]

        # Check original project count
        cursor = await conn.execute("SELECT COUNT(*) FROM projects")
        project_count = (await cursor.fetchone())[0]

        if basket_count != project_count:
            raise MigrationError(
                f"Migration validation failed: {project_count} projects but {basket_count} baskets"
            )

        if shelf_count == 0:
            raise MigrationError("Migration validation failed: no shelfs created")

        self.logger.info(f"Migration validation passed: {shelf_count} shelfs, {basket_count} baskets")

    async def _create_shelf_basket_indexes(self, conn: aiosqlite.Connection) -> None:
        """Create indexes for shelf and basket tables."""
        # Shelf indexes
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_shelfs_name ON shelfs (name)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_shelfs_is_current ON shelfs (is_current)")

        # Basket indexes
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_baskets_shelf_id ON baskets (shelf_id)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_baskets_name ON baskets (name)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_baskets_type ON baskets (type)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_baskets_status ON baskets (status)")
        await conn.execute("CREATE INDEX IF NOT EXISTS idx_baskets_schema_version ON baskets (schema_version)")

        self.logger.info("Created shelf and basket indexes")

    async def cleanup_migration_records(self, days_old: int = 30) -> int:
        """Clean up old migration records."""
        cutoff_date = datetime.utcnow().replace(
            day=datetime.utcnow().day - days_old
        ).isoformat()

        try:
            async with aiosqlite.connect(str(self.db_path)) as conn:
                cursor = await conn.execute("""
                    DELETE FROM project_migrations
                    WHERE started_at < ? AND success = 1
                """, (cutoff_date,))
                deleted_count = cursor.rowcount
                await conn.commit()

            self.logger.info(f"Cleaned up {deleted_count} old migration records")
            return deleted_count

        except Exception as e:
            self.logger.error(f"Failed to cleanup migration records: {e}")
            return 0