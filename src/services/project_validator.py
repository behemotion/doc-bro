"""Project validation service for compatibility checking and schema validation."""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

import aiosqlite

from src.core.config import DocBroConfig
from src.core.lib_logger import get_component_logger
from src.models.compatibility_status import CompatibilityStatus
from src.models.schema_version import SchemaVersion
from src.models.unified_project import UnifiedProject
from src.logic.projects.models.project import ProjectType, ProjectStatus


class ValidationError(Exception):
    """Project validation error."""
    pass


class CompatibilityResult:
    """Result of a project compatibility check."""

    def __init__(
        self,
        is_compatible: bool,
        current_version: int,
        project_version: int,
        status: CompatibilityStatus,
        missing_fields: Optional[List[str]] = None,
        extra_fields: Optional[List[str]] = None,
        issues: Optional[List[str]] = None,
        can_be_migrated: bool = False,
        migration_required: bool = False
    ):
        self.is_compatible = is_compatible
        self.current_version = current_version
        self.project_version = project_version
        self.status = status
        self.missing_fields = missing_fields or []
        self.extra_fields = extra_fields or []
        self.issues = issues or []
        self.can_be_migrated = can_be_migrated
        self.migration_required = migration_required

    @property
    def needs_recreation(self) -> bool:
        """Whether project needs to be recreated."""
        return not self.is_compatible and not self.can_be_migrated

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for API responses."""
        return {
            "is_compatible": self.is_compatible,
            "current_version": self.current_version,
            "project_version": self.project_version,
            "status": self.status.value,
            "missing_fields": self.missing_fields,
            "extra_fields": self.extra_fields,
            "issues": self.issues,
            "can_be_migrated": self.can_be_migrated,
            "migration_required": self.migration_required,
            "needs_recreation": self.needs_recreation
        }


class ProjectValidator:
    """Validates project schema compatibility and provides detailed analysis."""

    def __init__(self, config: DocBroConfig | None = None):
        """Initialize project validator."""
        self.config = config or DocBroConfig()
        self.db_path = self.config.database_path
        self.logger = get_component_logger("project_validator")

        # Required fields for unified schema version 3
        self.required_fields_v3 = {
            "id", "name", "schema_version", "type", "status", "compatibility_status",
            "created_at", "updated_at"
        }

        # Optional fields for unified schema version 3
        self.optional_fields_v3 = {
            "last_crawl_at", "source_url", "settings_json", "statistics_json", "metadata_json"
        }

        # All valid fields for version 3
        self.valid_fields_v3 = self.required_fields_v3 | self.optional_fields_v3

        # Type-specific settings requirements
        self.type_required_settings = {
            ProjectType.CRAWLING: ["crawl_depth", "rate_limit"],
            ProjectType.DATA: ["chunk_size", "embedding_model"],
            ProjectType.STORAGE: ["enable_compression"]
        }

    async def check_project_compatibility(self, project_id: str) -> CompatibilityResult:
        """Check compatibility of a specific project."""
        try:
            async with aiosqlite.connect(str(self.db_path)) as conn:
                # Get project data
                cursor = await conn.execute(
                    "SELECT * FROM projects WHERE id = ?",
                    (project_id,)
                )
                row = await cursor.fetchone()

                if not row:
                    raise ValidationError(f"Project {project_id} not found")

                # Get column names
                cursor = await conn.execute("PRAGMA table_info(projects)")
                columns = await cursor.fetchall()
                column_names = [col[1] for col in columns]

                # Create project data dict
                project_data = dict(zip(column_names, row))

                return await self._analyze_project_compatibility(project_data, column_names)

        except Exception as e:
            self.logger.error(f"Failed to check project compatibility: {e}")
            raise ValidationError(f"Failed to check project compatibility: {e}")

    async def check_all_projects_compatibility(self) -> List[Dict[str, Any]]:
        """Check compatibility of all projects in the database."""
        try:
            async with aiosqlite.connect(str(self.db_path)) as conn:
                # Get all projects
                cursor = await conn.execute("SELECT * FROM projects")
                rows = await cursor.fetchall()

                # Get column names
                cursor = await conn.execute("PRAGMA table_info(projects)")
                columns = await cursor.fetchall()
                column_names = [col[1] for col in columns]

                results = []
                for row in rows:
                    project_data = dict(zip(column_names, row))
                    compatibility = await self._analyze_project_compatibility(project_data, column_names)

                    results.append({
                        "project_id": project_data["id"],
                        "project_name": project_data["name"],
                        "compatibility": compatibility.to_dict()
                    })

                return results

        except Exception as e:
            self.logger.error(f"Failed to check all projects compatibility: {e}")
            raise ValidationError(f"Failed to check all projects compatibility: {e}")

    async def validate_unified_project(self, project_data: Dict[str, Any]) -> List[str]:
        """Validate a unified project data structure."""
        issues = []

        # Check required fields
        missing_fields = self.required_fields_v3 - set(project_data.keys())
        if missing_fields:
            issues.append(f"Missing required fields: {', '.join(missing_fields)}")

        # Check field types and values
        if "schema_version" in project_data:
            if not isinstance(project_data["schema_version"], int) or project_data["schema_version"] < 1:
                issues.append("schema_version must be a positive integer")

        if "type" in project_data:
            try:
                project_type = ProjectType(project_data["type"])
            except ValueError:
                issues.append(f"Invalid project type: {project_data['type']}")
            else:
                # Validate type-specific settings
                settings = {}
                if "settings_json" in project_data and project_data["settings_json"]:
                    try:
                        settings = json.loads(project_data["settings_json"])
                    except json.JSONDecodeError:
                        issues.append("Invalid JSON in settings_json field")

                # Check required settings for project type
                if project_type in self.type_required_settings:
                    required_settings = self.type_required_settings[project_type]
                    missing_settings = set(required_settings) - set(settings.keys())
                    if missing_settings:
                        issues.append(f"Missing required settings for {project_type.value}: {', '.join(missing_settings)}")

        if "status" in project_data:
            try:
                ProjectStatus(project_data["status"])
            except ValueError:
                issues.append(f"Invalid project status: {project_data['status']}")

        if "compatibility_status" in project_data:
            try:
                CompatibilityStatus(project_data["compatibility_status"])
            except ValueError:
                issues.append(f"Invalid compatibility status: {project_data['compatibility_status']}")

        # Validate JSON fields
        json_fields = ["settings_json", "statistics_json", "metadata_json"]
        for field in json_fields:
            if field in project_data and project_data[field]:
                try:
                    json.loads(project_data[field])
                except json.JSONDecodeError:
                    issues.append(f"Invalid JSON in {field} field")

        # Validate timestamps
        timestamp_fields = ["created_at", "updated_at", "last_crawl_at"]
        for field in timestamp_fields:
            if field in project_data and project_data[field]:
                try:
                    datetime.fromisoformat(project_data[field])
                except ValueError:
                    issues.append(f"Invalid timestamp format in {field}")

        # Check timestamp order
        if all(field in project_data for field in ["created_at", "updated_at"]):
            try:
                created = datetime.fromisoformat(project_data["created_at"])
                updated = datetime.fromisoformat(project_data["updated_at"])
                if created > updated:
                    issues.append("created_at cannot be after updated_at")
            except ValueError:
                pass  # Already reported above

        return issues

    async def flag_incompatible_projects(self) -> Dict[str, Any]:
        """Flag all incompatible projects in the database."""
        try:
            flagged_count = 0
            incompatible_projects = []

            async with aiosqlite.connect(str(self.db_path)) as conn:
                # Get all projects
                cursor = await conn.execute("SELECT * FROM projects")
                rows = await cursor.fetchall()

                # Get column names
                cursor = await conn.execute("PRAGMA table_info(projects)")
                columns = await cursor.fetchall()
                column_names = [col[1] for col in columns]

                # Check each project
                for row in rows:
                    project_data = dict(zip(column_names, row))
                    compatibility = await self._analyze_project_compatibility(project_data, column_names)

                    if not compatibility.is_compatible:
                        # Update compatibility status
                        await conn.execute(
                            "UPDATE projects SET compatibility_status = ? WHERE id = ?",
                            (CompatibilityStatus.INCOMPATIBLE.value, project_data["id"])
                        )
                        flagged_count += 1
                        incompatible_projects.append({
                            "id": project_data["id"],
                            "name": project_data["name"],
                            "compatibility": compatibility.to_dict()
                        })

                await conn.commit()

            self.logger.info(f"Flagged {flagged_count} incompatible projects")
            return {
                "success": True,
                "flagged_count": flagged_count,
                "incompatible_projects": incompatible_projects
            }

        except Exception as e:
            self.logger.error(f"Failed to flag incompatible projects: {e}")
            return {
                "success": False,
                "error": str(e),
                "flagged_count": 0
            }

    async def generate_compatibility_report(self) -> Dict[str, Any]:
        """Generate a comprehensive compatibility report for all projects."""
        try:
            all_results = await self.check_all_projects_compatibility()

            # Analyze results
            total_projects = len(all_results)
            compatible_count = sum(1 for r in all_results if r["compatibility"]["is_compatible"])
            incompatible_count = total_projects - compatible_count

            # Group by schema version
            version_breakdown = {}
            issue_summary = {}

            for result in all_results:
                comp = result["compatibility"]
                version = comp["project_version"]

                if version not in version_breakdown:
                    version_breakdown[version] = {"count": 0, "compatible": 0}

                version_breakdown[version]["count"] += 1
                if comp["is_compatible"]:
                    version_breakdown[version]["compatible"] += 1

                # Collect issues
                for issue in comp["issues"]:
                    if issue not in issue_summary:
                        issue_summary[issue] = 0
                    issue_summary[issue] += 1

            # Projects needing action
            needs_recreation = [r for r in all_results if r["compatibility"]["needs_recreation"]]
            can_be_migrated = [r for r in all_results if r["compatibility"]["can_be_migrated"]]

            return {
                "summary": {
                    "total_projects": total_projects,
                    "compatible_projects": compatible_count,
                    "incompatible_projects": incompatible_count,
                    "compatibility_rate": compatible_count / total_projects if total_projects > 0 else 0
                },
                "version_breakdown": version_breakdown,
                "action_required": {
                    "needs_recreation": len(needs_recreation),
                    "can_be_migrated": len(can_be_migrated),
                    "recreation_projects": [r["project_name"] for r in needs_recreation],
                    "migration_projects": [r["project_name"] for r in can_be_migrated]
                },
                "common_issues": sorted(issue_summary.items(), key=lambda x: x[1], reverse=True),
                "current_schema_version": SchemaVersion.get_current_version(),
                "generated_at": datetime.utcnow().isoformat()
            }

        except Exception as e:
            self.logger.error(f"Failed to generate compatibility report: {e}")
            raise ValidationError(f"Failed to generate compatibility report: {e}")

    async def _analyze_project_compatibility(
        self,
        project_data: Dict[str, Any],
        available_columns: List[str]
    ) -> CompatibilityResult:
        """Analyze project compatibility based on schema and data."""
        current_version = SchemaVersion.get_current_version()
        project_version = project_data.get("schema_version", 1)  # Default to version 1 if missing

        issues = []
        missing_fields = []
        extra_fields = []

        # Check schema version
        if project_version < current_version:
            issues.append(f"Project schema version {project_version} is outdated (current: {current_version})")

        # Check for required fields
        available_fields = set(available_columns)
        missing_fields = list(self.required_fields_v3 - available_fields)

        if missing_fields:
            issues.append(f"Missing required fields: {', '.join(missing_fields)}")

        # Check for unexpected fields (extra fields)
        extra_fields = list(available_fields - self.valid_fields_v3)
        if extra_fields:
            issues.append(f"Unexpected fields found: {', '.join(extra_fields)}")

        # Validate data integrity
        data_issues = await self.validate_unified_project(project_data)
        issues.extend(data_issues)

        # Determine compatibility
        is_compatible = (
            project_version == current_version and
            len(missing_fields) == 0 and
            len(data_issues) == 0
        )

        # Determine if migration is possible
        can_be_migrated = (
            project_version >= 2 and  # Can migrate from version 2+
            len(missing_fields) <= 2 and  # Minor missing fields
            len(data_issues) == 0  # No data corruption
        )

        migration_required = project_version < current_version

        # Determine status
        if is_compatible:
            status = CompatibilityStatus.COMPATIBLE
        elif migration_required:
            status = CompatibilityStatus.INCOMPATIBLE
        else:
            status = CompatibilityStatus.INCOMPATIBLE

        return CompatibilityResult(
            is_compatible=is_compatible,
            current_version=current_version,
            project_version=project_version,
            status=status,
            missing_fields=missing_fields,
            extra_fields=extra_fields,
            issues=issues,
            can_be_migrated=can_be_migrated,
            migration_required=migration_required
        )

    async def cleanup_validation_cache(self) -> None:
        """Clean up any validation cache or temporary data."""
        # For now, this is a placeholder for future caching mechanisms
        self.logger.info("Validation cache cleanup completed")

    async def validate_project_settings(
        self,
        project_type: ProjectType,
        settings: Dict[str, Any]
    ) -> List[str]:
        """Validate project settings for a specific project type."""
        issues = []

        # Check required settings
        if project_type in self.type_required_settings:
            required_settings = self.type_required_settings[project_type]
            missing_settings = set(required_settings) - set(settings.keys())
            if missing_settings:
                issues.append(f"Missing required settings: {', '.join(missing_settings)}")

        # Type-specific validation
        if project_type == ProjectType.CRAWLING:
            if "crawl_depth" in settings:
                depth = settings["crawl_depth"]
                if not isinstance(depth, int) or depth < 1 or depth > 10:
                    issues.append("crawl_depth must be an integer between 1 and 10")

            if "rate_limit" in settings:
                rate = settings["rate_limit"]
                if not isinstance(rate, (int, float)) or rate <= 0:
                    issues.append("rate_limit must be a positive number")

        elif project_type == ProjectType.DATA:
            if "chunk_size" in settings:
                size = settings["chunk_size"]
                if not isinstance(size, int) or size < 100 or size > 5000:
                    issues.append("chunk_size must be an integer between 100 and 5000")

            if "embedding_model" in settings:
                model = settings["embedding_model"]
                if not isinstance(model, str) or len(model.strip()) == 0:
                    issues.append("embedding_model must be a non-empty string")

        elif project_type == ProjectType.STORAGE:
            if "enable_compression" in settings:
                compression = settings["enable_compression"]
                if not isinstance(compression, bool):
                    issues.append("enable_compression must be a boolean")

        return issues