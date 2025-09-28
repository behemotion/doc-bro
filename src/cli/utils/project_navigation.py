"""Project-specific CLI navigation utilities."""

import logging

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from src.cli.utils.navigation import ArrowNavigator, NavigationChoice
from src.logic.projects.models.project import Project, ProjectStatus, ProjectType

logger = logging.getLogger(__name__)


class ProjectNavigationHelper:
    """Helper class for project-specific navigation operations."""

    def __init__(self, console: Console | None = None):
        self.console = console or Console()
        self.navigator = ArrowNavigator(console=self.console)

    async def select_project(
        self,
        projects: list[Project],
        title: str = "Select Project",
        filter_type: ProjectType | None = None,
        filter_status: ProjectStatus | None = None
    ) -> Project | None:
        """Interactive project selection with filtering."""
        try:
            # Apply filters
            filtered_projects = projects
            if filter_type:
                filtered_projects = [p for p in filtered_projects if p.type == filter_type]
            if filter_status:
                filtered_projects = [p for p in filtered_projects if p.status == filter_status]

            if not filtered_projects:
                self.console.print("[yellow]No projects match the current filters[/yellow]")
                return None

            # Create choices
            choices = []
            for project in filtered_projects:
                status_indicator = self._get_status_indicator(project.status)
                description = f"Type: {project.type.value} • Status: {project.status.value} • Created: {project.created_at.strftime('%Y-%m-%d')}"

                choice = NavigationChoice(
                    value=project.name,
                    label=f"{project.name} {status_indicator}",
                    description=description
                )
                choices.append(choice)

            # Show selection menu
            selected_name = await self.navigator.navigate_menu(title, choices)
            if not selected_name:
                return None

            # Return the selected project
            return next((p for p in filtered_projects if p.name == selected_name), None)

        except Exception as e:
            logger.error(f"Error in project selection: {e}")
            return None

    async def select_project_type(
        self,
        title: str = "Select Project Type",
        include_descriptions: bool = True
    ) -> ProjectType | None:
        """Interactive project type selection."""
        try:
            type_descriptions = {
                ProjectType.DATA: "Upload documents for vector search and AI assistance",
                ProjectType.STORAGE: "File storage with inventory management and search",
                ProjectType.CRAWLING: "Web documentation crawling and indexing"
            }

            choices = []
            for project_type in ProjectType:
                description = type_descriptions.get(project_type, "") if include_descriptions else None
                choice = NavigationChoice(
                    value=project_type.value,
                    label=project_type.value.title(),
                    description=description
                )
                choices.append(choice)

            selected = await self.navigator.navigate_menu(title, choices)
            return ProjectType(selected) if selected else None

        except Exception as e:
            logger.error(f"Error in project type selection: {e}")
            return None

    async def show_project_overview(self, projects: list[Project]) -> None:
        """Display comprehensive project overview."""
        try:
            if not projects:
                self.console.print("[yellow]No projects found[/yellow]")
                return

            # Create overview table
            table = Table(title="Project Overview")
            table.add_column("Name", style="cyan", min_width=15)
            table.add_column("Type", style="green", min_width=10)
            table.add_column("Status", style="yellow", min_width=10)
            table.add_column("Created", style="blue", min_width=12)
            table.add_column("Files", justify="right", min_width=8)

            # Group projects by type for better organization
            projects_by_type = {}
            for project in projects:
                if project.type not in projects_by_type:
                    projects_by_type[project.type] = []
                projects_by_type[project.type].append(project)

            # Add projects to table, grouped by type
            for project_type in ProjectType:
                if project_type in projects_by_type:
                    type_projects = projects_by_type[project_type]
                    # Sort by status (active first) then by name
                    type_projects.sort(key=lambda p: (p.status.value != 'active', p.name))

                    for i, project in enumerate(type_projects):
                        status_icon = self._get_status_indicator(project.status)

                        # Add visual separator between project types
                        if i == 0 and len([p for p in projects if p.type != project_type]) > 0:
                            table.add_row("", "", "", "", "", style="dim")

                        table.add_row(
                            project.name,
                            project.type.value.title(),
                            f"{status_icon} {project.status.value.title()}",
                            project.created_at.strftime("%Y-%m-%d"),
                            "N/A"  # Would be populated from project stats
                        )

            self.console.print(table)

            # Show summary statistics
            total_projects = len(projects)
            active_projects = len([p for p in projects if p.status == ProjectStatus.ACTIVE])
            by_type = {ptype: len([p for p in projects if p.type == ptype]) for ptype in ProjectType}

            summary_text = f"Total: {total_projects} projects ({active_projects} active)\n"
            summary_text += "By type: " + ", ".join([f"{ptype.value}: {count}" for ptype, count in by_type.items() if count > 0])

            self.console.print(Panel.fit(summary_text, title="Summary", border_style="dim"))

        except Exception as e:
            logger.error(f"Error showing project overview: {e}")
            self.console.print(f"[red]Error displaying project overview: {str(e)}[/red]")

    async def confirm_project_action(
        self,
        action: str,
        project_name: str,
        details: str | None = None,
        default: bool = False
    ) -> bool:
        """Get confirmation for potentially destructive project actions."""
        try:
            message = f"{action} project '{project_name}'"
            if details:
                message += f" ({details})"
            message += "?"

            return await self.navigator.confirm_choice(message, default=default)

        except Exception as e:
            logger.error(f"Error in confirmation dialog: {e}")
            return False

    async def select_upload_source_type(self) -> str | None:
        """Interactive upload source type selection."""
        try:
            source_types = [
                NavigationChoice(
                    "local",
                    "Local Files",
                    "Upload files from local filesystem"
                ),
                NavigationChoice(
                    "http",
                    "HTTP/HTTPS",
                    "Download files from web URLs"
                ),
                NavigationChoice(
                    "ftp",
                    "FTP",
                    "Upload from FTP server"
                ),
                NavigationChoice(
                    "sftp",
                    "SFTP/SSH",
                    "Upload from SFTP server (secure)"
                ),
                NavigationChoice(
                    "smb",
                    "SMB/CIFS",
                    "Upload from Windows network share"
                )
            ]

            return await self.navigator.navigate_menu(
                "Select upload source type:",
                source_types
            )

        except Exception as e:
            logger.error(f"Error in source type selection: {e}")
            return None

    async def show_project_actions_menu(self, project: Project) -> str | None:
        """Show available actions for a specific project."""
        try:
            # Base actions available for all projects
            actions = [
                NavigationChoice(
                    "show",
                    "Show Details",
                    "View detailed project information and statistics"
                ),
                NavigationChoice(
                    "settings",
                    "Update Settings",
                    "Modify project configuration and preferences"
                )
            ]

            # Add type-specific actions
            if project.type in [ProjectType.DATA, ProjectType.STORAGE]:
                actions.insert(1, NavigationChoice(
                    "upload",
                    "Upload Files",
                    "Upload files to this project"
                ))

            if project.type == ProjectType.CRAWLING:
                actions.insert(1, NavigationChoice(
                    "crawl",
                    "Start Crawling",
                    "Begin or resume web crawling"
                ))

            # Search action for data and crawling projects
            if project.type in [ProjectType.DATA, ProjectType.CRAWLING]:
                actions.append(NavigationChoice(
                    "search",
                    "Search Content",
                    "Search through project content"
                ))

            # Destructive actions at the end
            actions.extend([
                NavigationChoice(
                    "backup",
                    "Create Backup",
                    "Create a backup of project data"
                ),
                NavigationChoice(
                    "remove",
                    "Remove Project",
                    "Delete this project (with confirmation)"
                )
            ])

            return await self.navigator.navigate_menu(
                f"Actions for '{project.name}' ({project.type.value}):",
                actions
            )

        except Exception as e:
            logger.error(f"Error showing project actions: {e}")
            return None

    def _get_status_indicator(self, status: ProjectStatus) -> str:
        """Get visual indicator for project status."""
        indicators = {
            ProjectStatus.ACTIVE: "🟢",
            ProjectStatus.INACTIVE: "⚪",
            ProjectStatus.ERROR: "🔴",
            ProjectStatus.PROCESSING: "🟡"
        }
        return indicators.get(status, "❓")

    async def show_upload_progress_summary(
        self,
        operation_id: str,
        files_processed: int,
        files_total: int,
        bytes_processed: int,
        bytes_total: int,
        errors: list[str],
        warnings: list[str]
    ) -> None:
        """Display upload operation summary."""
        try:
            # Create summary table
            table = Table(title=f"Upload Summary - {operation_id}")
            table.add_column("Metric", style="cyan")
            table.add_column("Value", style="green")

            # Add metrics
            success_rate = (files_processed / files_total * 100) if files_total > 0 else 0
            table.add_row("Files Processed", f"{files_processed}/{files_total}")
            table.add_row("Success Rate", f"{success_rate:.1f}%")
            table.add_row("Data Transferred", self._format_bytes(bytes_processed))

            if bytes_total > 0:
                data_rate = (bytes_processed / bytes_total * 100)
                table.add_row("Data Completion", f"{data_rate:.1f}%")

            self.console.print(table)

            # Show errors and warnings if any
            if errors:
                self.console.print(f"\n[red]Errors ({len(errors)}):[/red]")
                for error in errors[:3]:  # Show first 3 errors
                    self.console.print(f"  • {error}")
                if len(errors) > 3:
                    self.console.print(f"  ... and {len(errors) - 3} more errors")

            if warnings:
                self.console.print(f"\n[yellow]Warnings ({len(warnings)}):[/yellow]")
                for warning in warnings[:3]:  # Show first 3 warnings
                    self.console.print(f"  • {warning}")
                if len(warnings) > 3:
                    self.console.print(f"  ... and {len(warnings) - 3} more warnings")

        except Exception as e:
            logger.error(f"Error showing upload summary: {e}")

    def _format_bytes(self, bytes_count: int) -> str:
        """Format bytes for human-readable display."""
        for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
            if bytes_count < 1024.0:
                return f"{bytes_count:.1f} {unit}"
            bytes_count /= 1024.0
        return f"{bytes_count:.1f} PB"
