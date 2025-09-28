"""Project management service."""

import logging

from src.models.project_status import ProjectStatus

logger = logging.getLogger(__name__)


class ProjectManager:
    """Manages documentation projects."""

    def __init__(self):
        """Initialize project manager."""
        self.projects = {}

    async def create_project(
        self,
        name: str,
        url: str,
        depth: int = 2,
        model: str = "mxbai-embed-large"
    ) -> ProjectStatus:
        """Create a new project.

        Args:
            name: Project name
            url: Documentation URL
            depth: Crawl depth
            model: Embedding model

        Returns:
            Created project status
        """
        project = ProjectStatus(
            project_name=name,
            url=url,
            crawl_depth=depth,
            model=model
        )
        self.projects[name] = project
        logger.info(f"Created project: {name}")
        return project

    async def get_project(self, name: str) -> ProjectStatus | None:
        """Get a project by name.

        Args:
            name: Project name

        Returns:
            Project status or None
        """
        return self.projects.get(name)

    async def list_projects(self) -> list[ProjectStatus]:
        """List all projects.

        Returns:
            List of project statuses
        """
        return list(self.projects.values())

    async def update_project(self, project: ProjectStatus) -> None:
        """Update a project.

        Args:
            project: Project to update
        """
        self.projects[project.project_name] = project
        logger.info(f"Updated project: {project.project_name}")

    async def delete_project(self, name: str) -> bool:
        """Delete a project.

        Args:
            name: Project name

        Returns:
            True if deleted
        """
        if name in self.projects:
            del self.projects[name]
            logger.info(f"Deleted project: {name}")
            return True
        return False
