"""Migration tracking service for project schema migrations."""

import json
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Optional

import aiosqlite

from ..models.migration_record import ProjectMigrationRecord, MigrationOperation
from ..models.schema_version import SchemaVersion


logger = logging.getLogger(__name__)


class MigrationTrackingService:
    """Service for tracking and managing project migration operations."""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize migration tracking service.

        Args:
            db_path: Optional database path, defaults to standard location
        """
        self.logger = logging.getLogger(__name__)

        # Database path
        if db_path is None:
            from pathlib import Path
            import os
            data_dir = os.environ.get('DOCBRO_DATA_DIR',
                                      str(Path.home() / '.local' / 'share' / 'docbro'))
            self.db_path = Path(data_dir) / 'project_registry.db'
        else:
            self.db_path = db_path

        # Database connection
        self._connection: Optional[aiosqlite.Connection] = None

    async def initialize(self) -> None:
        """Initialize database connection."""
        try:
            # Ensure database directory exists
            self.db_path.parent.mkdir(parents=True, exist_ok=True)

            # Open database connection
            self._connection = await aiosqlite.connect(str(self.db_path))

            # Enable foreign keys
            await self._connection.execute("PRAGMA foreign_keys = ON")

            # Ensure migration table exists
            await self._ensure_migration_table()

            self.logger.info(f"Initialized migration tracking service with database: {self.db_path}")

        except Exception as e:
            self.logger.error(f"Failed to initialize migration tracking service: {e}")
            raise

    async def close(self) -> None:
        """Close database connection."""
        if self._connection:
            await self._connection.close()
            self._connection = None

    async def _ensure_migration_table(self) -> None:
        """Ensure migration tracking table exists."""
        await self._connection.execute("""
            CREATE TABLE IF NOT EXISTS project_migrations (
                id TEXT PRIMARY KEY,
                project_id TEXT NOT NULL,
                project_name TEXT NOT NULL,
                operation TEXT NOT NULL,
                from_schema_version INTEGER NOT NULL,
                to_schema_version INTEGER NOT NULL,
                started_at TEXT NOT NULL,
                completed_at TEXT,
                success BOOLEAN DEFAULT FALSE,
                error_message TEXT,
                preserved_settings_json TEXT DEFAULT '{}',
                preserved_metadata_json TEXT DEFAULT '{}',
                data_size_bytes INTEGER DEFAULT 0,
                user_initiated BOOLEAN DEFAULT TRUE,
                initiated_by_command TEXT DEFAULT 'unknown'
            )
        """)

        # Create indexes
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_migrations_project_id ON project_migrations(project_id)",
            "CREATE INDEX IF NOT EXISTS idx_migrations_operation ON project_migrations(operation)",
            "CREATE INDEX IF NOT EXISTS idx_migrations_started_at ON project_migrations(started_at)",
            "CREATE INDEX IF NOT EXISTS idx_migrations_success ON project_migrations(success)"
        ]

        for index_sql in indexes:
            await self._connection.execute(index_sql)

        await self._connection.commit()

    async def record_migration(self, record: ProjectMigrationRecord) -> None:
        """
        Store a migration record in the database.

        Args:
            record: Migration record to store
        """
        try:
            await self._connection.execute("""
                INSERT OR REPLACE INTO project_migrations (
                    id, project_id, project_name, operation,
                    from_schema_version, to_schema_version,
                    started_at, completed_at, success, error_message,
                    preserved_settings_json, preserved_metadata_json,
                    data_size_bytes, user_initiated, initiated_by_command
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                record.id,
                record.project_id,
                record.project_name,
                record.operation.value,
                record.from_schema_version,
                record.to_schema_version,
                record.started_at.isoformat(),
                record.completed_at.isoformat() if record.completed_at else None,
                record.success,
                record.error_message,
                json.dumps(record.preserved_settings),
                json.dumps(record.preserved_metadata),
                record.data_size_bytes,
                record.user_initiated,
                record.initiated_by_command
            ))
            await self._connection.commit()

            self.logger.info(f"Recorded migration {record.operation.value} for project {record.project_name}")

        except Exception as e:
            self.logger.error(f"Failed to record migration for project {record.project_name}: {e}")
            raise

    async def get_migration_by_id(self, migration_id: str) -> Optional[ProjectMigrationRecord]:
        """
        Get migration record by ID.

        Args:
            migration_id: Migration ID

        Returns:
            ProjectMigrationRecord if found, None otherwise
        """
        cursor = await self._connection.execute(
            "SELECT * FROM project_migrations WHERE id = ?",
            (migration_id,)
        )
        row = await cursor.fetchone()
        await cursor.close()

        if row:
            return self._row_to_migration_record(row)
        return None

    async def get_project_migrations(
        self,
        project_id: str,
        limit: Optional[int] = None,
        operation_filter: Optional[MigrationOperation] = None
    ) -> list[ProjectMigrationRecord]:
        """
        Get migration history for a specific project.

        Args:
            project_id: Project ID
            limit: Maximum number of records to return
            operation_filter: Filter by operation type

        Returns:
            List of migration records ordered by started_at DESC
        """
        query = "SELECT * FROM project_migrations WHERE project_id = ?"
        params = [project_id]

        if operation_filter:
            query += " AND operation = ?"
            params.append(operation_filter.value)

        query += " ORDER BY started_at DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cursor = await self._connection.execute(query, params)
        rows = await cursor.fetchall()
        await cursor.close()

        return [self._row_to_migration_record(row) for row in rows]

    async def get_all_migrations(
        self,
        limit: Optional[int] = None,
        operation_filter: Optional[MigrationOperation] = None,
        success_filter: Optional[bool] = None,
        since: Optional[datetime] = None
    ) -> list[ProjectMigrationRecord]:
        """
        Get all migration records with optional filtering.

        Args:
            limit: Maximum number of records to return
            operation_filter: Filter by operation type
            success_filter: Filter by success status
            since: Only return migrations since this datetime

        Returns:
            List of migration records ordered by started_at DESC
        """
        query = "SELECT * FROM project_migrations WHERE 1=1"
        params = []

        if operation_filter:
            query += " AND operation = ?"
            params.append(operation_filter.value)

        if success_filter is not None:
            query += " AND success = ?"
            params.append(success_filter)

        if since:
            query += " AND started_at >= ?"
            params.append(since.isoformat())

        query += " ORDER BY started_at DESC"

        if limit:
            query += " LIMIT ?"
            params.append(limit)

        cursor = await self._connection.execute(query, params)
        rows = await cursor.fetchall()
        await cursor.close()

        return [self._row_to_migration_record(row) for row in rows]

    async def get_migration_statistics(self, days: int = 30) -> dict[str, Any]:
        """
        Get migration statistics for the specified time period.

        Args:
            days: Number of days to look back

        Returns:
            Dictionary with migration statistics
        """
        since = datetime.utcnow() - timedelta(days=days)

        cursor = await self._connection.execute("""
            SELECT
                COUNT(*) as total_migrations,
                COUNT(CASE WHEN success = 1 THEN 1 END) as successful_migrations,
                COUNT(CASE WHEN success = 0 THEN 1 END) as failed_migrations,
                COUNT(CASE WHEN operation = 'recreation' THEN 1 END) as recreations,
                COUNT(CASE WHEN operation = 'upgrade' THEN 1 END) as upgrades,
                COUNT(CASE WHEN operation = 'validation' THEN 1 END) as validations,
                AVG(CASE WHEN completed_at IS NOT NULL THEN
                    CAST((julianday(completed_at) - julianday(started_at)) * 86400 AS INTEGER)
                END) as avg_duration_seconds,
                COUNT(DISTINCT project_id) as unique_projects
            FROM project_migrations
            WHERE started_at >= ?
        """, (since.isoformat(),))

        row = await cursor.fetchone()
        await cursor.close()

        return {
            "period_days": days,
            "total_migrations": row[0],
            "successful_migrations": row[1],
            "failed_migrations": row[2],
            "recreation_count": row[3],
            "upgrade_count": row[4],
            "validation_count": row[5],
            "success_rate": round(row[1] / row[0] * 100, 1) if row[0] > 0 else 0,
            "average_duration_seconds": int(row[6]) if row[6] else 0,
            "unique_projects_affected": row[7]
        }

    async def get_failed_migrations(self, days: int = 7) -> list[ProjectMigrationRecord]:
        """
        Get recent failed migrations for debugging.

        Args:
            days: Number of days to look back

        Returns:
            List of failed migration records
        """
        since = datetime.utcnow() - timedelta(days=days)

        cursor = await self._connection.execute("""
            SELECT * FROM project_migrations
            WHERE success = 0 AND started_at >= ?
            ORDER BY started_at DESC
        """, (since.isoformat(),))

        rows = await cursor.fetchall()
        await cursor.close()

        return [self._row_to_migration_record(row) for row in rows]

    async def get_migration_trends(self, days: int = 30) -> dict[str, Any]:
        """
        Get migration trends over time.

        Args:
            days: Number of days to analyze

        Returns:
            Dictionary with trend analysis
        """
        since = datetime.utcnow() - timedelta(days=days)

        # Get daily migration counts
        cursor = await self._connection.execute("""
            SELECT
                DATE(started_at) as migration_date,
                COUNT(*) as count,
                COUNT(CASE WHEN success = 1 THEN 1 END) as successful,
                COUNT(CASE WHEN operation = 'recreation' THEN 1 END) as recreations
            FROM project_migrations
            WHERE started_at >= ?
            GROUP BY DATE(started_at)
            ORDER BY migration_date
        """, (since.isoformat(),))

        daily_data = await cursor.fetchall()
        await cursor.close()

        # Get schema version migration patterns
        cursor = await self._connection.execute("""
            SELECT
                from_schema_version,
                to_schema_version,
                COUNT(*) as count
            FROM project_migrations
            WHERE started_at >= ? AND operation = 'recreation'
            GROUP BY from_schema_version, to_schema_version
            ORDER BY count DESC
        """, (since.isoformat(),))

        version_patterns = await cursor.fetchall()
        await cursor.close()

        return {
            "period_days": days,
            "daily_migrations": [
                {
                    "date": row[0],
                    "total": row[1],
                    "successful": row[2],
                    "recreations": row[3]
                }
                for row in daily_data
            ],
            "schema_version_patterns": [
                {
                    "from_version": row[0],
                    "to_version": row[1],
                    "count": row[2]
                }
                for row in version_patterns
            ]
        }

    async def cleanup_old_migrations(self, keep_days: int = 90) -> int:
        """
        Clean up old migration records to prevent database bloat.

        Args:
            keep_days: Number of days of migration history to keep

        Returns:
            Number of records deleted
        """
        cutoff = datetime.utcnow() - timedelta(days=keep_days)

        cursor = await self._connection.execute(
            "DELETE FROM project_migrations WHERE started_at < ?",
            (cutoff.isoformat(),)
        )

        deleted_count = cursor.rowcount
        await self._connection.commit()
        await cursor.close()

        if deleted_count > 0:
            self.logger.info(f"Cleaned up {deleted_count} old migration records older than {keep_days} days")

        return deleted_count

    async def export_migration_history(
        self,
        output_path: Path,
        project_id: Optional[str] = None,
        since: Optional[datetime] = None
    ) -> None:
        """
        Export migration history to JSON file.

        Args:
            output_path: Path to export file
            project_id: Optional project ID filter
            since: Optional datetime filter

        Raises:
            Exception: If export fails
        """
        query = "SELECT * FROM project_migrations WHERE 1=1"
        params = []

        if project_id:
            query += " AND project_id = ?"
            params.append(project_id)

        if since:
            query += " AND started_at >= ?"
            params.append(since.isoformat())

        query += " ORDER BY started_at DESC"

        cursor = await self._connection.execute(query, params)
        rows = await cursor.fetchall()
        await cursor.close()

        # Convert to export format
        migrations = []
        for row in rows:
            record = self._row_to_migration_record(row)
            migrations.append(record.to_summary())

        export_data = {
            "export_timestamp": datetime.utcnow().isoformat(),
            "total_migrations": len(migrations),
            "filters": {
                "project_id": project_id,
                "since": since.isoformat() if since else None
            },
            "migrations": migrations
        }

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)

            self.logger.info(f"Exported {len(migrations)} migration records to {output_path}")

        except Exception as e:
            self.logger.error(f"Failed to export migration history: {e}")
            raise

    async def analyze_migration_patterns(self) -> dict[str, Any]:
        """
        Analyze migration patterns to identify common issues.

        Returns:
            Dictionary with pattern analysis
        """
        # Get error patterns
        cursor = await self._connection.execute("""
            SELECT
                error_message,
                COUNT(*) as frequency,
                operation
            FROM project_migrations
            WHERE success = 0 AND error_message IS NOT NULL
            GROUP BY error_message, operation
            ORDER BY frequency DESC
            LIMIT 10
        """)

        error_patterns = await cursor.fetchall()
        await cursor.close()

        # Get project recreation frequency
        cursor = await self._connection.execute("""
            SELECT
                project_name,
                COUNT(*) as recreation_count,
                MAX(started_at) as last_recreation
            FROM project_migrations
            WHERE operation = 'recreation'
            GROUP BY project_name
            HAVING recreation_count > 1
            ORDER BY recreation_count DESC
            LIMIT 10
        """)

        frequent_recreations = await cursor.fetchall()
        await cursor.close()

        # Get average recreation time by schema version
        cursor = await self._connection.execute("""
            SELECT
                from_schema_version,
                to_schema_version,
                COUNT(*) as count,
                AVG(CASE WHEN completed_at IS NOT NULL THEN
                    CAST((julianday(completed_at) - julianday(started_at)) * 86400 AS INTEGER)
                END) as avg_duration_seconds
            FROM project_migrations
            WHERE operation = 'recreation' AND success = 1
            GROUP BY from_schema_version, to_schema_version
            ORDER BY count DESC
        """)

        duration_patterns = await cursor.fetchall()
        await cursor.close()

        return {
            "common_errors": [
                {
                    "error": row[0],
                    "frequency": row[1],
                    "operation": row[2]
                }
                for row in error_patterns
            ],
            "frequent_recreations": [
                {
                    "project_name": row[0],
                    "recreation_count": row[1],
                    "last_recreation": row[2]
                }
                for row in frequent_recreations
            ],
            "duration_by_version": [
                {
                    "from_version": row[0],
                    "to_version": row[1],
                    "count": row[2],
                    "avg_duration_seconds": int(row[3]) if row[3] else 0
                }
                for row in duration_patterns
            ]
        }

    def _row_to_migration_record(self, row) -> ProjectMigrationRecord:
        """Convert database row to ProjectMigrationRecord."""
        # Parse JSON fields
        preserved_settings = json.loads(row[10]) if row[10] else {}
        preserved_metadata = json.loads(row[11]) if row[11] else {}

        # Parse datetime fields
        started_at = datetime.fromisoformat(row[6])
        completed_at = datetime.fromisoformat(row[7]) if row[7] else None

        return ProjectMigrationRecord(
            id=row[0],
            project_id=row[1],
            project_name=row[2],
            operation=MigrationOperation(row[3]),
            from_schema_version=row[4],
            to_schema_version=row[5],
            started_at=started_at,
            completed_at=completed_at,
            success=bool(row[8]),
            error_message=row[9],
            preserved_settings=preserved_settings,
            preserved_metadata=preserved_metadata,
            data_size_bytes=row[12],
            user_initiated=bool(row[13]),
            initiated_by_command=row[14]
        )

    async def __aenter__(self):
        """Async context manager entry."""
        await self.initialize()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.close()