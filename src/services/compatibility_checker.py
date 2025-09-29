"""Compatibility checker service for schema validation."""

import logging
from typing import Any, Optional

from pydantic import BaseModel, Field

from ..models.compatibility_status import CompatibilityStatus
from ..models.schema_version import SchemaVersion
from ..models.unified_project import UnifiedProject


logger = logging.getLogger(__name__)


class CompatibilityResult(BaseModel):
    """Result of compatibility check."""

    is_compatible: bool = Field(..., description="Whether project is compatible")
    current_version: int = Field(..., description="Current schema version")
    project_version: int = Field(..., description="Project schema version")
    status: CompatibilityStatus = Field(..., description="Compatibility status")
    missing_fields: list[str] = Field(default_factory=list, description="Fields missing from project")
    extra_fields: list[str] = Field(default_factory=list, description="Extra fields in project")
    issues: list[str] = Field(default_factory=list, description="Compatibility issues found")
    can_be_migrated: bool = Field(default=False, description="Whether automatic migration is possible")
    migration_required: bool = Field(default=False, description="Whether migration is required")

    @property
    def needs_recreation(self) -> bool:
        """Whether project needs to be recreated."""
        return not self.is_compatible and not self.can_be_migrated

    def add_issue(self, issue: str) -> None:
        """Add a compatibility issue."""
        self.issues.append(issue)

    def add_missing_field(self, field: str) -> None:
        """Add a missing field."""
        self.missing_fields.append(field)

    def add_extra_field(self, field: str) -> None:
        """Add an extra field."""
        self.extra_fields.append(field)

    def to_summary(self) -> dict[str, Any]:
        """Get a summary of the compatibility result."""
        return {
            "is_compatible": self.is_compatible,
            "status": self.status.value,
            "version_info": f"v{self.project_version} → v{self.current_version}",
            "issues_count": len(self.issues),
            "missing_fields_count": len(self.missing_fields),
            "extra_fields_count": len(self.extra_fields),
            "needs_recreation": self.needs_recreation,
            "can_be_migrated": self.can_be_migrated,
            "migration_required": self.migration_required
        }


class CompatibilityChecker:
    """Service for detecting and validating project compatibility."""

    def __init__(self):
        """Initialize compatibility checker."""
        self.current_version = SchemaVersion.get_current_version()
        self.logger = logging.getLogger(__name__)

    async def check_project_compatibility(self, project: UnifiedProject) -> CompatibilityResult:
        """
        Check compatibility of a project with current schema version.

        Args:
            project: Project to check

        Returns:
            CompatibilityResult with detailed analysis
        """
        result = CompatibilityResult(
            is_compatible=False,
            current_version=self.current_version,
            project_version=project.schema_version,
            status=CompatibilityStatus.INCOMPATIBLE
        )

        try:
            # Check schema version compatibility
            await self._check_schema_version(project, result)

            # Check field compatibility
            await self._check_field_compatibility(project, result)

            # Check data integrity
            await self._check_data_integrity(project, result)

            # Check type-specific requirements
            await self._check_type_specific_requirements(project, result)

            # Determine final compatibility status
            self._determine_final_status(result)

            self.logger.debug(f"Compatibility check for {project.name}: {result.status.value}")

        except Exception as e:
            result.add_issue(f"Error during compatibility check: {str(e)}")
            result.status = CompatibilityStatus.INCOMPATIBLE
            self.logger.error(f"Compatibility check failed for {project.name}: {e}")

        return result

    async def check_database_compatibility(self, project_data: dict[str, Any]) -> CompatibilityResult:
        """
        Check compatibility of raw project data from database.

        Args:
            project_data: Raw project data dictionary

        Returns:
            CompatibilityResult with detailed analysis
        """
        schema_version = project_data.get('schema_version', 1)  # Default to version 1 if missing

        result = CompatibilityResult(
            is_compatible=False,
            current_version=self.current_version,
            project_version=schema_version,
            status=CompatibilityStatus.INCOMPATIBLE
        )

        try:
            # Check if we can parse the data into a UnifiedProject
            if schema_version == self.current_version:
                # Try to create UnifiedProject to validate structure
                try:
                    project = UnifiedProject.from_dict(project_data)
                    return await self.check_project_compatibility(project)
                except Exception as e:
                    result.add_issue(f"Failed to parse project data: {str(e)}")
                    result.status = CompatibilityStatus.INCOMPATIBLE
            else:
                # Check specific version compatibility
                await self._check_version_specific_compatibility(project_data, result)

        except Exception as e:
            result.add_issue(f"Error during database compatibility check: {str(e)}")
            result.status = CompatibilityStatus.INCOMPATIBLE
            self.logger.error(f"Database compatibility check failed: {e}")

        return result

    async def _check_schema_version(self, project: UnifiedProject, result: CompatibilityResult) -> None:
        """Check schema version compatibility."""
        if project.schema_version == self.current_version:
            # Same version - should be compatible
            result.is_compatible = True
            result.status = CompatibilityStatus.COMPATIBLE
        elif project.schema_version < self.current_version:
            # Older version - incompatible
            result.status = CompatibilityStatus.INCOMPATIBLE
            result.migration_required = True
            result.add_issue(f"Project uses older schema version {project.schema_version}, current is {self.current_version}")
        else:
            # Future version - incompatible
            result.status = CompatibilityStatus.INCOMPATIBLE
            result.add_issue(f"Project uses future schema version {project.schema_version}, current is {self.current_version}")

    async def _check_field_compatibility(self, project: UnifiedProject, result: CompatibilityResult) -> None:
        """Check field presence and compatibility."""
        # Required fields for current schema version
        required_fields = {
            'id', 'name', 'schema_version', 'compatibility_status',
            'status', 'created_at', 'updated_at', 'settings',
            'statistics', 'metadata'
        }

        # Get project fields
        project_dict = project.to_dict()
        project_fields = set(project_dict.keys())

        # Check for missing required fields
        missing = required_fields - project_fields
        for field in missing:
            result.add_missing_field(field)
            result.add_issue(f"Missing required field: {field}")

        # Check for extra fields (not necessarily a problem)
        expected_fields = required_fields.union({
            'type', 'last_crawl_at', 'source_url',
            'is_compatible', 'allows_modification', 'needs_recreation', 'is_outdated'
        })
        extra = project_fields - expected_fields
        for field in extra:
            result.add_extra_field(field)

    async def _check_data_integrity(self, project: UnifiedProject, result: CompatibilityResult) -> None:
        """Check data integrity and consistency."""
        # Check timestamp order
        if project.updated_at < project.created_at:
            result.add_issue("Updated timestamp is before created timestamp")

        if project.last_crawl_at and project.last_crawl_at < project.created_at:
            result.add_issue("Last crawl timestamp is before created timestamp")

        # Check statistics consistency
        stats = project.statistics
        if 'total_pages' in stats and 'successful_pages' in stats and 'failed_pages' in stats:
            total = stats.get('total_pages', 0)
            successful = stats.get('successful_pages', 0)
            failed = stats.get('failed_pages', 0)

            if successful + failed > total:
                result.add_issue("Sum of successful and failed pages exceeds total pages")

        # Check settings validity
        if project.type:
            try:
                # This will raise an exception if settings are invalid
                project._validate_type_specific_settings(project.settings, project.type)
            except ValueError as e:
                result.add_issue(f"Invalid settings: {str(e)}")

    async def _check_type_specific_requirements(self, project: UnifiedProject, result: CompatibilityResult) -> None:
        """Check type-specific requirements."""
        if not project.type:
            result.add_issue("Project type is not specified")
            return

        # Check type-specific field requirements
        type_requirements = {
            'crawling': {
                'required_settings': ['crawl_depth'],
                'optional_fields': ['source_url', 'last_crawl_at'],
                'required_statistics': []
            },
            'data': {
                'required_settings': ['chunk_size', 'embedding_model'],
                'optional_fields': [],
                'required_statistics': []
            },
            'storage': {
                'required_settings': ['enable_compression'],
                'optional_fields': [],
                'required_statistics': []
            }
        }

        requirements = type_requirements.get(project.type.value, {})

        # Check required settings
        for setting in requirements.get('required_settings', []):
            if setting not in project.settings:
                result.add_issue(f"Missing required setting for {project.type.value} project: {setting}")

    async def _check_version_specific_compatibility(self, project_data: dict[str, Any], result: CompatibilityResult) -> None:
        """Check compatibility for specific schema versions."""
        schema_version = result.project_version

        if schema_version == 1:
            # Original crawler schema
            await self._check_v1_compatibility(project_data, result)
        elif schema_version == 2:
            # Project logic schema
            await self._check_v2_compatibility(project_data, result)
        else:
            result.add_issue(f"Unknown schema version: {schema_version}")

    async def _check_v1_compatibility(self, project_data: dict[str, Any], result: CompatibilityResult) -> None:
        """Check compatibility for version 1 (crawler schema)."""
        # Version 1 required fields
        v1_required = {'id', 'name', 'status', 'created_at', 'updated_at'}

        missing = v1_required - set(project_data.keys())
        for field in missing:
            result.add_missing_field(field)
            result.add_issue(f"Missing required v1 field: {field}")

        # Check if it has crawler-specific fields
        crawler_fields = {'source_url', 'crawl_depth', 'total_pages', 'embedding_model'}
        has_crawler_fields = any(field in project_data for field in crawler_fields)

        if has_crawler_fields:
            # This looks like a crawler project that can be converted
            result.migration_required = True
            result.add_issue("Version 1 crawler project requires recreation to unified schema")
        else:
            result.add_issue("Version 1 project format not recognized")

    async def _check_v2_compatibility(self, project_data: dict[str, Any], result: CompatibilityResult) -> None:
        """Check compatibility for version 2 (logic schema)."""
        # Version 2 required fields
        v2_required = {'id', 'name', 'type', 'status', 'created_at', 'updated_at', 'settings'}

        missing = v2_required - set(project_data.keys())
        for field in missing:
            result.add_missing_field(field)
            result.add_issue(f"Missing required v2 field: {field}")

        # Check if it has logic-specific structure
        if 'type' in project_data and 'settings' in project_data:
            # This looks like a logic project that can be converted
            result.migration_required = True
            result.add_issue("Version 2 logic project requires recreation to unified schema")
        else:
            result.add_issue("Version 2 project format not recognized")

    def _determine_final_status(self, result: CompatibilityResult) -> None:
        """Determine final compatibility status based on all checks."""
        if result.project_version == self.current_version and not result.issues:
            result.is_compatible = True
            result.status = CompatibilityStatus.COMPATIBLE
        elif result.migration_required and not result.missing_fields:
            result.status = CompatibilityStatus.INCOMPATIBLE
            result.can_be_migrated = SchemaVersion.can_migrate_from(result.project_version)
        else:
            result.is_compatible = False
            result.status = CompatibilityStatus.INCOMPATIBLE

    async def check_multiple_projects(self, projects: list[UnifiedProject]) -> dict[str, CompatibilityResult]:
        """
        Check compatibility for multiple projects.

        Args:
            projects: List of projects to check

        Returns:
            Dictionary mapping project IDs to compatibility results
        """
        results = {}

        for project in projects:
            try:
                result = await self.check_project_compatibility(project)
                results[project.id] = result
            except Exception as e:
                # Create error result
                error_result = CompatibilityResult(
                    is_compatible=False,
                    current_version=self.current_version,
                    project_version=project.schema_version,
                    status=CompatibilityStatus.INCOMPATIBLE
                )
                error_result.add_issue(f"Error checking project: {str(e)}")
                results[project.id] = error_result

                self.logger.error(f"Failed to check compatibility for project {project.id}: {e}")

        return results

    def get_compatibility_summary(self, results: dict[str, CompatibilityResult]) -> dict[str, Any]:
        """
        Get a summary of compatibility results.

        Args:
            results: Dictionary of compatibility results

        Returns:
            Summary statistics
        """
        total = len(results)
        compatible = sum(1 for r in results.values() if r.is_compatible)
        incompatible = sum(1 for r in results.values() if not r.is_compatible)
        needs_recreation = sum(1 for r in results.values() if r.needs_recreation)
        can_migrate = sum(1 for r in results.values() if r.can_be_migrated)

        return {
            "total_projects": total,
            "compatible": compatible,
            "incompatible": incompatible,
            "needs_recreation": needs_recreation,
            "can_migrate": can_migrate,
            "compatibility_rate": round(compatible / total * 100, 1) if total > 0 else 0,
            "version_distribution": self._get_version_distribution(results)
        }

    def _get_version_distribution(self, results: dict[str, CompatibilityResult]) -> dict[int, int]:
        """Get distribution of schema versions."""
        distribution = {}
        for result in results.values():
            version = result.project_version
            distribution[version] = distribution.get(version, 0) + 1
        return distribution

    def get_recreation_instructions(self, result: CompatibilityResult, project_name: str) -> list[str]:
        """
        Get step-by-step recreation instructions for incompatible project.

        Args:
            result: Compatibility result
            project_name: Name of the project

        Returns:
            List of instruction strings
        """
        if result.is_compatible:
            return ["Project is already compatible - no action needed."]

        instructions = [
            f"Project '{project_name}' is incompatible with current schema version {self.current_version}.",
            "",
            "To upgrade this project:",
            "",
            "1. Export current project settings (recommended):",
            f"   docbro project --export {project_name} > {project_name}-backup.json",
            "",
            "2. Recreate the project with unified schema:",
            f"   docbro project --recreate {project_name} --confirm",
            "",
            "3. Verify the recreation was successful:",
            f"   docbro project --show {project_name} --detailed",
            "",
            "Note: This will preserve your settings and metadata but will reset statistics",
            "and require re-crawling any documentation if this is a crawling project."
        ]

        if result.issues:
            instructions.extend([
                "",
                "Compatibility issues found:",
            ])
            for issue in result.issues:
                instructions.append(f"  • {issue}")

        return instructions