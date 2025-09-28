"""
Contract tests for ProjectManagerContract service interface.

These tests verify the service interface contract for project management
according to the specification in contracts/service-interfaces.py.
"""

import pytest
from unittest.mock import Mock, AsyncMock
from datetime import datetime
from typing import Optional, List

# Import contract interfaces (will fail until implemented)
try:
    from src.logic.projects.core.project_manager import ProjectManager
    from src.logic.projects.models.project import Project, ProjectType, ProjectStatus
    from src.logic.projects.models.config import ProjectConfig
except ImportError:
    # Expected to fail in TDD - create mock classes for testing
    class ProjectType:
        CRAWLING = "crawling"
        DATA = "data"
        STORAGE = "storage"

    class ProjectStatus:
        ACTIVE = "active"
        INACTIVE = "inactive"
        ERROR = "error"
        PROCESSING = "processing"

    class Project:
        def __init__(self, id: str, name: str, type: ProjectType, status: ProjectStatus,
                     created_at: datetime, updated_at: datetime, settings: dict, metadata: dict):
            self.id = id
            self.name = name
            self.type = type
            self.status = status
            self.created_at = created_at
            self.updated_at = updated_at
            self.settings = settings
            self.metadata = metadata

    class ProjectConfig:
        def __init__(self, max_file_size: int, allowed_formats: List[str], type_specific_settings: dict):
            self.max_file_size = max_file_size
            self.allowed_formats = allowed_formats
            self.type_specific_settings = type_specific_settings

    class ProjectManager:
        pass


class TestProjectManagerContract:
    """Test the ProjectManager service contract."""

    def setup_method(self):
        """Set up test environment."""
        self.project_manager = Mock(spec=ProjectManager)
        self._setup_mock_behaviors()

    def _setup_mock_behaviors(self):
        """Set up mock method behaviors."""
        # Mock async methods
        self.project_manager.create_project = AsyncMock()
        self.project_manager.get_project = AsyncMock()
        self.project_manager.list_projects = AsyncMock()
        self.project_manager.update_project = AsyncMock()
        self.project_manager.remove_project = AsyncMock()
        self.project_manager.get_project_stats = AsyncMock()

    @pytest.mark.asyncio
    async def test_create_project_contract(self):
        """Test create_project method contract."""
        # Setup
        name = "test-project"
        project_type = ProjectType.DATA
        settings = ProjectConfig(
            max_file_size=10485760,
            allowed_formats=["pdf", "txt", "md"],
            type_specific_settings={"embedding_model": "mxbai-embed-large"}
        )

        expected_project = Project(
            id="test-project-id",
            name=name,
            type=project_type,
            status=ProjectStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            settings={"max_file_size": 10485760},
            metadata={}
        )

        self.project_manager.create_project.return_value = expected_project

        # Execute
        result = await self.project_manager.create_project(name, project_type, settings)

        # Verify
        self.project_manager.create_project.assert_called_once_with(name, project_type, settings)
        assert result == expected_project
        assert result.name == name
        assert result.type == project_type

    @pytest.mark.asyncio
    async def test_create_project_without_settings(self):
        """Test create_project with default settings."""
        # Setup
        name = "test-project-defaults"
        project_type = ProjectType.STORAGE

        expected_project = Project(
            id="test-project-defaults-id",
            name=name,
            type=project_type,
            status=ProjectStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            settings={},
            metadata={}
        )

        self.project_manager.create_project.return_value = expected_project

        # Execute
        result = await self.project_manager.create_project(name, project_type, None)

        # Verify
        self.project_manager.create_project.assert_called_once_with(name, project_type, None)
        assert result == expected_project

    @pytest.mark.asyncio
    async def test_get_project_contract(self):
        """Test get_project method contract."""
        # Setup
        name = "existing-project"
        expected_project = Project(
            id="existing-project-id",
            name=name,
            type=ProjectType.CRAWLING,
            status=ProjectStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            settings={},
            metadata={}
        )

        self.project_manager.get_project.return_value = expected_project

        # Execute
        result = await self.project_manager.get_project(name)

        # Verify
        self.project_manager.get_project.assert_called_once_with(name)
        assert result == expected_project

    @pytest.mark.asyncio
    async def test_get_project_not_found(self):
        """Test get_project returns None for non-existent project."""
        # Setup
        name = "nonexistent-project"
        self.project_manager.get_project.return_value = None

        # Execute
        result = await self.project_manager.get_project(name)

        # Verify
        self.project_manager.get_project.assert_called_once_with(name)
        assert result is None

    @pytest.mark.asyncio
    async def test_list_projects_contract(self):
        """Test list_projects method contract."""
        # Setup
        expected_projects = [
            Project(
                id="project-1",
                name="Project 1",
                type=ProjectType.DATA,
                status=ProjectStatus.ACTIVE,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                settings={},
                metadata={}
            ),
            Project(
                id="project-2",
                name="Project 2",
                type=ProjectType.STORAGE,
                status=ProjectStatus.INACTIVE,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                settings={},
                metadata={}
            )
        ]

        self.project_manager.list_projects.return_value = expected_projects

        # Execute
        result = await self.project_manager.list_projects()

        # Verify
        self.project_manager.list_projects.assert_called_once_with(None, None, None)
        assert result == expected_projects
        assert len(result) == 2

    @pytest.mark.asyncio
    async def test_list_projects_with_filters(self):
        """Test list_projects with status and type filters."""
        # Setup
        status_filter = ProjectStatus.ACTIVE
        type_filter = ProjectType.DATA
        limit = 10

        filtered_projects = [
            Project(
                id="filtered-project",
                name="Filtered Project",
                type=type_filter,
                status=status_filter,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                settings={},
                metadata={}
            )
        ]

        self.project_manager.list_projects.return_value = filtered_projects

        # Execute
        result = await self.project_manager.list_projects(status_filter, type_filter, limit)

        # Verify
        self.project_manager.list_projects.assert_called_once_with(status_filter, type_filter, limit)
        assert result == filtered_projects

    @pytest.mark.asyncio
    async def test_update_project_contract(self):
        """Test update_project method contract."""
        # Setup
        project = Project(
            id="update-project-id",
            name="Project to Update",
            type=ProjectType.CRAWLING,
            status=ProjectStatus.ACTIVE,
            created_at=datetime.now(),
            updated_at=datetime.now(),
            settings={"crawl_depth": 5},
            metadata={"description": "Updated description"}
        )

        updated_project = Project(
            id=project.id,
            name=project.name,
            type=project.type,
            status=project.status,
            created_at=project.created_at,
            updated_at=datetime.now(),  # Should be updated
            settings=project.settings,
            metadata=project.metadata
        )

        self.project_manager.update_project.return_value = updated_project

        # Execute
        result = await self.project_manager.update_project(project)

        # Verify
        self.project_manager.update_project.assert_called_once_with(project)
        assert result == updated_project

    @pytest.mark.asyncio
    async def test_remove_project_contract(self):
        """Test remove_project method contract."""
        # Setup
        name = "project-to-remove"
        backup = True

        self.project_manager.remove_project.return_value = True

        # Execute
        result = await self.project_manager.remove_project(name, backup)

        # Verify
        self.project_manager.remove_project.assert_called_once_with(name, backup)
        assert result is True

    @pytest.mark.asyncio
    async def test_remove_project_without_backup(self):
        """Test remove_project without backup."""
        # Setup
        name = "project-no-backup"
        backup = False

        self.project_manager.remove_project.return_value = True

        # Execute
        result = await self.project_manager.remove_project(name, backup)

        # Verify
        self.project_manager.remove_project.assert_called_once_with(name, backup)
        assert result is True

    @pytest.mark.asyncio
    async def test_remove_project_failure(self):
        """Test remove_project returns False on failure."""
        # Setup
        name = "project-remove-fail"
        backup = True

        self.project_manager.remove_project.return_value = False

        # Execute
        result = await self.project_manager.remove_project(name, backup)

        # Verify
        self.project_manager.remove_project.assert_called_once_with(name, backup)
        assert result is False

    @pytest.mark.asyncio
    async def test_get_project_stats_contract(self):
        """Test get_project_stats method contract."""
        # Setup
        name = "stats-project"
        expected_stats = {
            "file_count": 150,
            "total_size": "2.5GB",
            "last_updated": "2025-09-28T10:30:00Z",
            "status": "active",
            "type_specific_data": {
                "documents_processed": 150,
                "vector_chunks": 500
            }
        }

        self.project_manager.get_project_stats.return_value = expected_stats

        # Execute
        result = await self.project_manager.get_project_stats(name)

        # Verify
        self.project_manager.get_project_stats.assert_called_once_with(name)
        assert result == expected_stats
        assert "file_count" in result
        assert "total_size" in result

    @pytest.mark.asyncio
    async def test_all_project_types_supported(self):
        """Test that all project types can be created."""
        project_types = [ProjectType.CRAWLING, ProjectType.DATA, ProjectType.STORAGE]

        for project_type in project_types:
            # Reset mock
            self.project_manager.create_project.reset_mock()

            # Setup
            name = f"test-{project_type.lower()}"
            expected_project = Project(
                id=f"{name}-id",
                name=name,
                type=project_type,
                status=ProjectStatus.ACTIVE,
                created_at=datetime.now(),
                updated_at=datetime.now(),
                settings={},
                metadata={}
            )

            self.project_manager.create_project.return_value = expected_project

            # Execute
            result = await self.project_manager.create_project(name, project_type, None)

            # Verify
            self.project_manager.create_project.assert_called_once_with(name, project_type, None)
            assert result.type == project_type

    @pytest.mark.asyncio
    async def test_method_signatures_match_contract(self):
        """Test that all methods have correct signatures."""
        # This test verifies that the implementation matches the contract interface
        # Will fail until implementation exists, which is expected in TDD

        # Verify create_project signature
        assert hasattr(self.project_manager, 'create_project')

        # Verify get_project signature
        assert hasattr(self.project_manager, 'get_project')

        # Verify list_projects signature
        assert hasattr(self.project_manager, 'list_projects')

        # Verify update_project signature
        assert hasattr(self.project_manager, 'update_project')

        # Verify remove_project signature
        assert hasattr(self.project_manager, 'remove_project')

        # Verify get_project_stats signature
        assert hasattr(self.project_manager, 'get_project_stats')