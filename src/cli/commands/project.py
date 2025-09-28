"""Project command for DocBro CLI."""

import asyncio
import json

import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

# Optional uvloop for better performance
try:
    import uvloop
    UVLOOP_AVAILABLE = True
except ImportError:
    UVLOOP_AVAILABLE = False

import logging

from src.cli.utils.navigation import ArrowNavigator, NavigationChoice
from src.logic.projects.models.project import ProjectStatus, ProjectType

logger = logging.getLogger(__name__)


def run_async(coro):
    """Run async coroutine in sync context."""
    if UVLOOP_AVAILABLE:
        try:
            uvloop.install()
        except Exception:
            pass

    return asyncio.run(coro)


def get_app():
    """Get or create global app instance."""
    from src.cli.main import get_app as main_get_app
    return main_get_app()


# CLI Error Messages from contracts
CLI_ERROR_MESSAGES = {
    "project_exists": "Project '{name}' already exists. Use --force to overwrite.",
    "project_not_found": "Project '{name}' not found.",
    "invalid_project_type": "Invalid project type '{type}'. Must be one of: {valid_types}",
    "invalid_source_type": "Invalid source type '{type}'. Must be one of: {valid_types}",
    "authentication_failed": "Authentication failed for {source}. Please check credentials.",
    "network_timeout": "Network timeout while connecting to {source}. Retrying ({attempt}/3)...",
    "file_too_large": "File '{filename}' ({size}) exceeds maximum size limit ({limit}).",
    "invalid_format": "File '{filename}' has unsupported format '{format}' for {project_type} projects.",
    "permission_denied": "Permission denied accessing '{path}'. Check file permissions.",
    "disk_space_low": "Insufficient disk space. Need {required}, have {available}."
}


@click.group(name="project", invoke_without_command=True)
@click.pass_context
def project(ctx: click.Context):
    """Manage documentation projects.

    Run without arguments to launch interactive menu:
    docbro project

    Or use subcommands directly:
    docbro project create --name my-docs --type data
    docbro project list --status active
    docbro project remove --name old-project --confirm
    """
    if ctx.invoked_subcommand is None:
        # Launch interactive menu
        run_async(interactive_project_menu())


@project.command(name="create")
@click.option("--name", "-n", required=True, help="Project name")
@click.option("--type", "-t", "project_type",
              type=click.Choice(['crawling', 'data', 'storage'], case_sensitive=False),
              required=True, help="Project type")
@click.option("--description", "-d", help="Optional project description")
@click.option("--settings", "-s", help="JSON settings override")
@click.option("--force", "-f", is_flag=True, help="Overwrite existing project")
def create_project(name: str, project_type: str, description: str | None,
                   settings: str | None, force: bool):
    """Create a new project with specified type and settings."""
    run_async(_create_project_impl(name, project_type, description, settings, force))


@project.command(name="list")
@click.option("--status", "-st",
              type=click.Choice(['active', 'inactive', 'error', 'processing'], case_sensitive=False),
              help="Filter by status")
@click.option("--type", "-t", "project_type",
              type=click.Choice(['crawling', 'data', 'storage'], case_sensitive=False),
              help="Filter by project type")
@click.option("--limit", "-l", type=int, help="Limit number of results")
@click.option("--verbose", "-v", is_flag=True, help="Show detailed information")
def list_projects(status: str | None, project_type: str | None,
                  limit: int | None, verbose: bool):
    """List projects with optional filtering."""
    run_async(_list_projects_impl(status, project_type, limit, verbose))


@project.command(name="remove")
@click.option("--name", "-n", required=True, help="Project name")
@click.option("--confirm", "-c", is_flag=True, help="Skip confirmation prompt")
@click.option("--backup", "-b", is_flag=True, default=True, help="Create backup before removal")
@click.option("--force", "-f", is_flag=True, help="Force removal even if errors")
def remove_project(name: str, confirm: bool, backup: bool, force: bool):
    """Remove a project and handle type-specific cleanup."""
    run_async(_remove_project_impl(name, confirm, backup, force))


@project.command(name="show")
@click.option("--name", "-n", required=True, help="Project name")
@click.option("--detailed", "-dt", is_flag=True, help="Show detailed information")
def show_project(name: str, detailed: bool):
    """Show project information and status."""
    run_async(_show_project_impl(name, detailed))


@project.command(name="update")
@click.option("--name", "-n", required=True, help="Project name")
@click.option("--settings", "-s", help="JSON settings update")
@click.option("--description", "-d", help="Update project description")
def update_project(name: str, settings: str | None, description: str | None):
    """Update project settings and metadata."""
    run_async(_update_project_impl(name, settings, description))


# Implementation functions

async def interactive_project_menu():
    """Show interactive project management menu with arrow navigation."""
    console = Console()
    navigator = ArrowNavigator()

    try:
        app = get_app()
        project_manager = app.project_manager

        # Get existing projects
        projects = await project_manager.list_projects()

        while True:
            console.clear()
            console.print(Panel.fit(
                "[bold blue]DocBro Project Management[/bold blue]\n"
                "Manage your documentation projects",
                border_style="blue"
            ))

            # Main menu choices
            main_choices = [
                NavigationChoice("create", "Create New Project", "Create a new documentation project"),
                NavigationChoice("list", "List Projects", f"View all projects ({len(projects)} total)"),
            ]

            if projects:
                main_choices.extend([
                    NavigationChoice("manage", "Manage Existing Project", "View, update, or remove projects"),
                    NavigationChoice("stats", "Project Statistics", "View project statistics and usage")
                ])

            main_choices.append(NavigationChoice("exit", "Exit", "Return to main CLI"))

            choice = await navigator.navigate_menu(
                "Select an action:",
                main_choices
            )

            if choice == "exit":
                break
            elif choice == "create":
                await _interactive_create_project()
                # Refresh project list
                projects = await project_manager.list_projects()
            elif choice == "list":
                await _interactive_list_projects()
            elif choice == "manage" and projects:
                await _interactive_manage_projects(projects)
                # Refresh project list
                projects = await project_manager.list_projects()
            elif choice == "stats" and projects:
                await _interactive_project_stats(projects)

    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
    except Exception as e:
        logger.error(f"Error in interactive project menu: {e}")
        console.print(f"[red]Error: {str(e)}[/red]")


async def _interactive_create_project():
    """Interactive project creation."""
    console = Console()
    navigator = ArrowNavigator()

    try:
        # Get project name
        name = console.input("[cyan]Project name:[/cyan] ").strip()
        if not name:
            console.print("[red]Project name is required[/red]")
            return

        # Select project type
        type_choices = [
            NavigationChoice("data", "Data Project", "Upload documents for vector search"),
            NavigationChoice("storage", "Storage Project", "File storage with inventory management"),
            NavigationChoice("crawling", "Crawling Project", "Web documentation crawling")
        ]

        project_type = await navigator.navigate_menu(
            "Select project type:",
            type_choices
        )

        if not project_type:
            return

        # Optional description
        description = console.input("[cyan]Description (optional):[/cyan] ").strip() or None

        # Create project
        await _create_project_impl(name, project_type, description, None, False)

    except Exception as e:
        logger.error(f"Error in interactive project creation: {e}")
        console.print(f"[red]Error creating project: {str(e)}[/red]")


async def _interactive_list_projects():
    """Interactive project listing."""
    console = Console()

    try:
        app = get_app()
        project_manager = app.project_manager

        projects = await project_manager.list_projects()

        if not projects:
            console.print("[yellow]No projects found[/yellow]")
            console.input("\nPress Enter to continue...")
            return

        # Create projects table
        table = Table(title="Documentation Projects")
        table.add_column("Name", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Status", style="yellow")
        table.add_column("Created", style="blue")
        table.add_column("Files", justify="right")

        for project in projects:
            # Get project stats
            try:
                stats = await project_manager.get_project_stats(project.name)
                file_count = str(stats.get("file_count", "N/A"))
            except Exception:
                file_count = "N/A"

            table.add_row(
                project.name,
                project.type.value.title(),
                project.status.value.title(),
                project.created_at.strftime("%Y-%m-%d"),
                file_count
            )

        console.print(table)
        console.input("\nPress Enter to continue...")

    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        console.print(f"[red]Error listing projects: {str(e)}[/red]")


async def _interactive_manage_projects(projects):
    """Interactive project management."""
    console = Console()
    navigator = ArrowNavigator()

    try:
        # Select project to manage
        project_choices = [
            NavigationChoice(
                p.name,
                f"{p.name} ({p.type.value})",
                f"Status: {p.status.value} • Created: {p.created_at.strftime('%Y-%m-%d')}"
            )
            for p in projects
        ]

        selected_project_name = await navigator.navigate_menu(
            "Select project to manage:",
            project_choices
        )

        if not selected_project_name:
            return

        # Find selected project
        selected_project = next((p for p in projects if p.name == selected_project_name), None)
        if not selected_project:
            console.print("[red]Project not found[/red]")
            return

        # Project management menu
        mgmt_choices = [
            NavigationChoice("show", "Show Details", "View detailed project information"),
            NavigationChoice("upload", "Upload Files", "Upload files to this project"),
            NavigationChoice("settings", "Update Settings", "Modify project settings"),
            NavigationChoice("remove", "Remove Project", "Delete this project")
        ]

        action = await navigator.navigate_menu(
            f"Manage project '{selected_project.name}':",
            mgmt_choices
        )

        if action == "show":
            await _show_project_impl(selected_project.name, True)
            console.input("\nPress Enter to continue...")
        elif action == "upload":
            # Launch upload command interactively
            from src.cli.commands.upload import interactive_upload_menu
            await interactive_upload_menu(selected_project.name)
        elif action == "settings":
            await _interactive_update_settings(selected_project.name)
        elif action == "remove":
            # Confirm removal
            confirm = await navigator.confirm_choice(
                f"Are you sure you want to remove project '{selected_project.name}'?",
                default=False
            )
            if confirm:
                await _remove_project_impl(selected_project.name, True, True, False)

    except Exception as e:
        logger.error(f"Error managing projects: {e}")
        console.print(f"[red]Error managing projects: {str(e)}[/red]")


async def _interactive_project_stats(projects):
    """Show interactive project statistics."""
    console = Console()

    try:
        app = get_app()
        project_manager = app.project_manager

        # Create stats table
        table = Table(title="Project Statistics")
        table.add_column("Project", style="cyan")
        table.add_column("Type", style="green")
        table.add_column("Files", justify="right")
        table.add_column("Size", justify="right")
        table.add_column("Status", style="yellow")

        total_files = 0
        total_size = 0

        for project in projects:
            try:
                stats = await project_manager.get_project_stats(project.name)
                file_count = stats.get("file_count", 0)
                project_size = stats.get("total_size", 0)

                total_files += file_count
                total_size += project_size

                size_str = _format_bytes(project_size) if project_size > 0 else "N/A"

                table.add_row(
                    project.name,
                    project.type.value.title(),
                    str(file_count),
                    size_str,
                    project.status.value.title()
                )
            except Exception:
                table.add_row(
                    project.name,
                    project.type.value.title(),
                    "N/A",
                    "N/A",
                    project.status.value.title()
                )

        console.print(table)

        # Show totals
        console.print(f"\n[bold]Total: {total_files} files, {_format_bytes(total_size)}[/bold]")
        console.input("\nPress Enter to continue...")

    except Exception as e:
        logger.error(f"Error showing project stats: {e}")
        console.print(f"[red]Error showing statistics: {str(e)}[/red]")


async def _interactive_update_settings(project_name: str):
    """Interactive settings update."""
    console = Console()

    try:
        console.print(f"[cyan]Updating settings for project: {project_name}[/cyan]")
        console.print("Enter settings as JSON (press Enter for no changes):")

        settings_input = console.input("Settings: ").strip()

        if settings_input:
            await _update_project_impl(project_name, settings_input, None)
        else:
            console.print("[yellow]No changes made[/yellow]")

    except Exception as e:
        logger.error(f"Error updating settings: {e}")
        console.print(f"[red]Error updating settings: {str(e)}[/red]")


# Command implementation functions

async def _create_project_impl(name: str, project_type: str, description: str | None,
                               settings: str | None, force: bool):
    """Implementation of project creation."""
    console = Console()

    try:
        app = get_app()
        project_manager = app.project_manager

        # Validate project type
        try:
            proj_type = ProjectType(project_type.lower())
        except ValueError:
            valid_types = [t.value for t in ProjectType]
            error_msg = CLI_ERROR_MESSAGES["invalid_project_type"].format(
                type=project_type, valid_types=", ".join(valid_types)
            )
            console.print(f"[red]Error: {error_msg}[/red]")
            return

        # Parse settings if provided
        parsed_settings = None
        if settings:
            try:
                parsed_settings = json.loads(settings)
            except json.JSONDecodeError as e:
                console.print(f"[red]Error: Invalid JSON in settings: {str(e)}[/red]")
                return

        # Check if project exists
        existing_project = await project_manager.get_project(name)
        if existing_project and not force:
            error_msg = CLI_ERROR_MESSAGES["project_exists"].format(name=name)
            console.print(f"[red]Error: {error_msg}[/red]")
            return

        # Create project
        with console.status(f"Creating project '{name}'..."):
            project = await project_manager.create_project(
                name=name,
                project_type=proj_type,
                settings=parsed_settings
            )

        console.print(f"[green]✓[/green] Project '{name}' created successfully!")
        console.print(f"  Type: {project.type.value}")
        console.print(f"  Status: {project.status.value}")
        console.print(f"  Created: {project.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

        if description:
            # Update project with description (if supported by project manager)
            # This would be handled by the project manager implementation
            pass

    except Exception as e:
        logger.error(f"Error creating project: {e}")
        console.print(f"[red]Error creating project: {str(e)}[/red]")


async def _list_projects_impl(status: str | None, project_type: str | None,
                              limit: int | None, verbose: bool):
    """Implementation of project listing."""
    console = Console()

    try:
        app = get_app()
        project_manager = app.project_manager

        # Convert string parameters to enums
        status_filter = None
        if status:
            try:
                status_filter = ProjectStatus(status.lower())
            except ValueError:
                console.print(f"[red]Error: Invalid status '{status}'[/red]")
                return

        type_filter = None
        if project_type:
            try:
                type_filter = ProjectType(project_type.lower())
            except ValueError:
                console.print(f"[red]Error: Invalid project type '{project_type}'[/red]")
                return

        # Get projects
        projects = await project_manager.list_projects(
            status=status_filter,
            project_type=type_filter,
            limit=limit
        )

        if not projects:
            console.print("[yellow]No projects found[/yellow]")
            return

        if verbose:
            # Detailed view
            for project in projects:
                console.print(f"\n[bold cyan]{project.name}[/bold cyan]")
                console.print(f"  Type: {project.type.value}")
                console.print(f"  Status: {project.status.value}")
                console.print(f"  Created: {project.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                console.print(f"  Updated: {project.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")

                # Get additional stats
                try:
                    stats = await project_manager.get_project_stats(project.name)
                    if stats:
                        console.print(f"  Files: {stats.get('file_count', 'N/A')}")
                        if 'total_size' in stats:
                            console.print(f"  Size: {_format_bytes(stats['total_size'])}")
                except Exception:
                    pass
        else:
            # Table view
            table = Table()
            table.add_column("Name", style="cyan")
            table.add_column("Type", style="green")
            table.add_column("Status", style="yellow")
            table.add_column("Created", style="blue")

            for project in projects:
                table.add_row(
                    project.name,
                    project.type.value.title(),
                    project.status.value.title(),
                    project.created_at.strftime("%Y-%m-%d")
                )

            console.print(table)

    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        console.print(f"[red]Error listing projects: {str(e)}[/red]")


async def _remove_project_impl(name: str, confirm: bool, backup: bool, force: bool):
    """Implementation of project removal."""
    console = Console()

    try:
        app = get_app()
        project_manager = app.project_manager

        # Check if project exists
        project = await project_manager.get_project(name)
        if not project:
            error_msg = CLI_ERROR_MESSAGES["project_not_found"].format(name=name)
            console.print(f"[red]Error: {error_msg}[/red]")
            return

        # Confirmation prompt if not already confirmed
        if not confirm:
            response = console.input(f"Are you sure you want to remove project '{name}'? [y/N]: ")
            if response.lower() not in ['y', 'yes']:
                console.print("[yellow]Operation cancelled[/yellow]")
                return

        # Remove project
        with console.status(f"Removing project '{name}'..."):
            success = await project_manager.remove_project(name, backup=backup)

        if success:
            console.print(f"[green]✓[/green] Project '{name}' removed successfully!")
            if backup:
                console.print("  Backup created before removal")
        else:
            console.print(f"[red]✗[/red] Failed to remove project '{name}'")

    except Exception as e:
        logger.error(f"Error removing project: {e}")
        if force:
            console.print(f"[yellow]Warning: Error during removal (force mode): {str(e)}[/yellow]")
        else:
            console.print(f"[red]Error removing project: {str(e)}[/red]")


async def _show_project_impl(name: str, detailed: bool):
    """Implementation of project show."""
    console = Console()

    try:
        app = get_app()
        project_manager = app.project_manager

        # Get project
        project = await project_manager.get_project(name)
        if not project:
            error_msg = CLI_ERROR_MESSAGES["project_not_found"].format(name=name)
            console.print(f"[red]Error: {error_msg}[/red]")
            return

        # Basic information
        console.print(f"\n[bold cyan]Project: {project.name}[/bold cyan]")
        console.print(f"Type: {project.type.value}")
        console.print(f"Status: {project.status.value}")
        console.print(f"Created: {project.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        console.print(f"Updated: {project.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")

        if detailed:
            # Get detailed statistics
            try:
                stats = await project_manager.get_project_stats(name)
                if stats:
                    console.print("\n[bold]Statistics:[/bold]")
                    for key, value in stats.items():
                        if key == 'total_size' and isinstance(value, int):
                            console.print(f"  {key.replace('_', ' ').title()}: {_format_bytes(value)}")
                        else:
                            console.print(f"  {key.replace('_', ' ').title()}: {value}")
            except Exception as e:
                console.print(f"[yellow]Warning: Could not fetch detailed stats: {str(e)}[/yellow]")

            # Show settings if available
            if project.settings:
                console.print("\n[bold]Settings:[/bold]")
                for key, value in project.settings.items():
                    console.print(f"  {key}: {value}")

    except Exception as e:
        logger.error(f"Error showing project: {e}")
        console.print(f"[red]Error showing project: {str(e)}[/red]")


async def _update_project_impl(name: str, settings: str | None, description: str | None):
    """Implementation of project update."""
    console = Console()

    try:
        app = get_app()
        project_manager = app.project_manager

        # Get project
        project = await project_manager.get_project(name)
        if not project:
            error_msg = CLI_ERROR_MESSAGES["project_not_found"].format(name=name)
            console.print(f"[red]Error: {error_msg}[/red]")
            return

        # Parse settings if provided
        if settings:
            try:
                parsed_settings = json.loads(settings)
                # Update project settings
                project.settings.update(parsed_settings)
            except json.JSONDecodeError as e:
                console.print(f"[red]Error: Invalid JSON in settings: {str(e)}[/red]")
                return

        # Update description if provided
        if description:
            if not project.metadata:
                project.metadata = {}
            project.metadata['description'] = description

        # Save changes
        with console.status(f"Updating project '{name}'..."):
            updated_project = await project_manager.update_project(project)

        console.print(f"[green]✓[/green] Project '{name}' updated successfully!")

    except Exception as e:
        logger.error(f"Error updating project: {e}")
        console.print(f"[red]Error updating project: {str(e)}[/red]")


def _format_bytes(bytes_count: int) -> str:
    """Format bytes for human-readable display."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} PB"
