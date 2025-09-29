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
from src.services.unified_project_service import UnifiedProjectService, ProjectNotFoundError, IncompatibleProjectError
from src.services.compatibility_checker import CompatibilityChecker, CompatibilityResult
from src.services.project_export_service import ProjectExportService
from src.models.unified_project import UnifiedProject, UnifiedProjectStatus
from src.models.compatibility_status import CompatibilityStatus
from src.logic.projects.models.project import ProjectType
from pathlib import Path

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


async def get_unified_project_service():
    """Get or create UnifiedProjectService instance."""
    service = UnifiedProjectService()
    await service.initialize()
    return service


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


@click.command(name="project")
@click.option("--create", "-c", is_flag=True, help="Create a new project")
@click.option("--list", "-l", "-ls", is_flag=True, help="List projects")
@click.option("--remove", "-r", "-rm", is_flag=True, help="Remove a project")
@click.option("--show", "-s", is_flag=True, help="Show project details")
@click.option("--update", "-u", is_flag=True, help="Update project settings")
@click.option("--recreate", is_flag=True, help="Recreate incompatible project")
@click.option("--export", "-e", is_flag=True, help="Export project for backup")
@click.option("--check-compatibility", is_flag=True, help="Check project compatibility")
@click.argument("name", required=False)
@click.option("--type", "-t", "project_type",
              type=click.Choice(['crawling', 'data', 'storage'], case_sensitive=False),
              help="Project type (for create)")
@click.option("--description", "-d", help="Project description")
@click.option("--settings", help="JSON settings")
@click.option("--force", "-f", is_flag=True, help="Force operation")
@click.option("--status", "-st",
              type=click.Choice(['active', 'inactive', 'error', 'processing', 'created', 'crawling', 'indexing', 'ready', 'failed', 'archived'], case_sensitive=False),
              help="Filter by status (for list)")
@click.option("--compatibility", "-comp",
              type=click.Choice(['compatible', 'incompatible', 'migrating'], case_sensitive=False),
              help="Filter by compatibility status (for list)")
@click.option("--limit", type=int, help="Limit results (for list)")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@click.option("--confirm", is_flag=True, help="Skip confirmation (for remove)")
@click.option("--backup", "-b", is_flag=True, default=True, help="Create backup (for remove)")
@click.option("--detailed", "-dt", is_flag=True, help="Detailed view (for show)")
@click.pass_context
def project(ctx: click.Context, create: bool, list: bool, remove: bool, show: bool, update: bool,
           recreate: bool, export: bool, check_compatibility: bool,
           name: str | None, project_type: str | None, description: str | None, settings: str | None,
           force: bool, status: str | None, compatibility: str | None, limit: int | None, verbose: bool, confirm: bool,
           backup: bool, detailed: bool):
    """Manage documentation projects.

    \b
    USAGE:
      docbro project                    # Interactive menu
      docbro project <name>             # Show project details (same as --show)
      docbro project <flags> [options]  # Execute specific action

    \b
    FLAGS (mutually exclusive):
      --create, -c      Create a new project
      --list, -l, -ls   List projects
      --remove, -r, -rm Remove a project
      --show, -s        Show project details
      --update, -u      Update project settings

    \b
    EXAMPLES:
      docbro project                                    # Interactive menu
      docbro project myproject                          # Show project details (implicit)
      docbro project --create myproject --type data    # Create project
      docbro project --list --status active            # List active projects
      docbro project --remove myproject --confirm      # Remove project
      docbro project --show myproject --detailed       # Show project details (explicit)
      docbro project --update myproject --settings '{...}'  # Update settings

    \b
    PROJECT TYPES:
      crawling    Web documentation crawler projects
      data        Document upload and vector search projects
      storage     File storage with inventory management
    """
    # Count active flags
    active_flags = sum([create, list, remove, show, update, recreate, export, check_compatibility])

    if active_flags == 0:
        if name:
            # Name provided without flags - default to show
            run_async(_show_project_impl(name, detailed))
        else:
            # No flags and no name - launch interactive menu
            run_async(interactive_project_menu())
        return
    elif active_flags > 1:
        click.echo("Error: Only one action flag can be specified at a time.", err=True)
        ctx.exit(1)

    # Execute the appropriate action
    if create:
        if not name:
            click.echo("Error: Project name is required for --create", err=True)
            ctx.exit(1)
        if not project_type:
            click.echo("Error: --type is required for --create", err=True)
            ctx.exit(1)
        run_async(_create_project_impl(name, project_type, description, settings, force))
    elif list:
        run_async(_list_projects_impl(status, project_type, compatibility, limit, verbose))
    elif remove:
        if not name:
            click.echo("Error: Project name is required for --remove", err=True)
            ctx.exit(1)
        run_async(_remove_project_impl(name, confirm, backup, force))
    elif show:
        if not name:
            click.echo("Error: Project name is required for --show", err=True)
            ctx.exit(1)
        run_async(_show_project_impl(name, detailed))
    elif update:
        if not name:
            click.echo("Error: Project name is required for --update", err=True)
            ctx.exit(1)
        run_async(_update_project_impl(name, settings, description))
    elif recreate:
        if not name:
            click.echo("Error: Project name is required for --recreate", err=True)
            ctx.exit(1)
        run_async(_recreate_project_impl(name, confirm, force))
    elif export:
        if not name:
            click.echo("Error: Project name is required for --export", err=True)
            ctx.exit(1)
        run_async(_export_project_impl(name))
    elif check_compatibility:
        if not name:
            click.echo("Error: Project name is required for --check-compatibility", err=True)
            ctx.exit(1)
        run_async(_check_compatibility_impl(name))



# Implementation functions

async def interactive_project_menu():
    """Show interactive project management menu with arrow navigation."""
    console = Console()
    navigator = ArrowNavigator()

    try:
        unified_service = await get_unified_project_service()

        # Get existing projects
        projects = await unified_service.list_projects()

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
                projects = await unified_service.list_projects()
            elif choice == "list":
                await _interactive_list_projects()
            elif choice == "manage" and projects:
                await _interactive_manage_projects(projects)
                # Refresh project list
                projects = await unified_service.list_projects()
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
        unified_service = await get_unified_project_service()

        projects = await unified_service.list_projects()

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
                stats = await unified_service.get_project_stats(project.name)
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
        unified_service = await get_unified_project_service()

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
                stats = await unified_service.get_project_stats(project.name)
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
        unified_service = await get_unified_project_service()

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
                settings_dict = json.loads(settings)
                # Import ProjectConfig to properly convert settings
                from src.logic.projects.models.config import ProjectConfig
                parsed_settings = ProjectConfig.from_dict(settings_dict)
            except json.JSONDecodeError as e:
                console.print(f"[red]Error: Invalid JSON in settings: {str(e)}[/red]")
                return
            except Exception as e:
                console.print(f"[red]Error: Invalid settings configuration: {str(e)}[/red]")
                return

        # Check if project exists
        existing_project = await unified_service.get_project(name)
        if existing_project and not force:
            error_msg = CLI_ERROR_MESSAGES["project_exists"].format(name=name)
            console.print(f"[red]Error: {error_msg}[/red]")
            return

        # Create project
        with console.status(f"Creating project '{name}'..."):
            project = await unified_service.create_project(
                name=name,
                project_type=proj_type,
                settings=parsed_settings
            )

        console.print(f"[green]✓[/green] Project '{name}' created successfully!")

        # Debug logging to understand what we received
        logger.debug(f"Project type: {type(project)}, Is dict: {isinstance(project, dict)}")
        if hasattr(project, '__dict__'):
            logger.debug(f"Project attributes: {project.__dict__}")

        # Check if project is a dict or object and handle accordingly
        if isinstance(project, dict):
            console.print(f"  Type: {project.get('type', 'unknown')}")
            console.print(f"  Status: {project.get('status', 'unknown')}")
            created_at = project.get('created_at')
            if created_at:
                if isinstance(created_at, str):
                    console.print(f"  Created: {created_at}")
                else:
                    console.print(f"  Created: {created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            # Assume it's a Project object
            # Safely access attributes
            project_type = getattr(project, 'type', 'unknown')
            if hasattr(project_type, 'value'):
                console.print(f"  Type: {project_type.value}")
            else:
                console.print(f"  Type: {project_type}")

            project_status = getattr(project, 'status', 'unknown')
            if hasattr(project_status, 'value'):
                console.print(f"  Status: {project_status.value}")
            else:
                console.print(f"  Status: {project_status}")

            created_at = getattr(project, 'created_at', None)
            if created_at:
                if hasattr(created_at, 'strftime'):
                    console.print(f"  Created: {created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    console.print(f"  Created: {created_at}")

        if description:
            # Update project with description (if supported by project manager)
            # This would be handled by the project manager implementation
            pass

    except Exception as e:
        import traceback
        logger.error(f"Error creating project: {e}", exc_info=True)
        console.print(f"[red]Error creating project: {str(e)}[/red]")
        console.print(f"[dim]Full error: {traceback.format_exc()}[/dim]")


async def _list_projects_impl(status: str | None, project_type: str | None, compatibility: str | None,
                              limit: int | None, verbose: bool):
    """Implementation of project listing."""
    console = Console()

    try:
        unified_service = await get_unified_project_service()

        # Convert string parameters to enums
        status_filter = None
        if status:
            try:
                status_filter = UnifiedProjectStatus(status.lower())
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

        compatibility_filter = None
        if compatibility:
            try:
                compatibility_filter = CompatibilityStatus(compatibility.lower())
            except ValueError:
                console.print(f"[red]Error: Invalid compatibility status '{compatibility}'[/red]")
                return

        # Get projects
        projects = await unified_service.list_projects(
            status_filter=status_filter,
            type_filter=type_filter,
            compatibility_filter=compatibility_filter,
            limit=limit
        )

        if not projects:
            console.print("[yellow]No projects found[/yellow]")
            return

        if verbose:
            # Detailed view
            for project in projects:
                console.print(f"\n[bold cyan]{project.name}[/bold cyan]")

                # Handle both enum and string types for type
                project_type = project.type
                if hasattr(project_type, 'value'):
                    console.print(f"  Type: {project_type.value}")
                else:
                    console.print(f"  Type: {project_type}")

                # Handle both enum and string types for status
                project_status = project.status
                if hasattr(project_status, 'value'):
                    console.print(f"  Status: {project_status.value}")
                else:
                    console.print(f"  Status: {project_status}")

                # Handle date formatting safely
                if hasattr(project.created_at, 'strftime'):
                    console.print(f"  Created: {project.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    console.print(f"  Created: {project.created_at}")

                if hasattr(project.updated_at, 'strftime'):
                    console.print(f"  Updated: {project.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")
                else:
                    console.print(f"  Updated: {project.updated_at}")

                # Get additional stats
                try:
                    stats = await unified_service.get_project_stats(project.name)
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
            table.add_column("Compatibility", style="magenta")
            table.add_column("Created", style="blue")

            for project in projects:
                # Handle both enum and string types
                project_type = project.type
                if hasattr(project_type, 'value'):
                    type_str = project_type.value.title()
                else:
                    type_str = str(project_type).title()

                project_status = project.status
                if hasattr(project_status, 'value'):
                    status_str = project_status.value.title()
                else:
                    status_str = str(project_status).title()

                compatibility_status = project.compatibility_status
                if hasattr(compatibility_status, 'value'):
                    compatibility_str = compatibility_status.value.title()
                else:
                    compatibility_str = str(compatibility_status).title()

                created_str = project.created_at.strftime("%Y-%m-%d") if hasattr(project.created_at, 'strftime') else str(project.created_at)

                table.add_row(
                    project.name,
                    type_str,
                    status_str,
                    compatibility_str,
                    created_str
                )

            console.print(table)

    except Exception as e:
        logger.error(f"Error listing projects: {e}")
        console.print(f"[red]Error listing projects: {str(e)}[/red]")


async def _remove_project_impl(name: str, confirm: bool, backup: bool, force: bool):
    """Implementation of project removal."""
    console = Console()

    try:
        unified_service = await get_unified_project_service()

        # Check if project exists
        project = await unified_service.get_project(name)
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
            success = await unified_service.remove_project(name, backup=backup)

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
        unified_service = await get_unified_project_service()

        # Get project
        project = await unified_service.get_project(name)
        if not project:
            error_msg = CLI_ERROR_MESSAGES["project_not_found"].format(name=name)
            console.print(f"[red]Error: {error_msg}[/red]")
            return

        # Basic information
        console.print(f"\n[bold cyan]Project: {project.name}[/bold cyan]")
        # Handle both enum and string types
        type_value = project.type.value if hasattr(project.type, 'value') else str(project.type)
        status_value = project.status.value if hasattr(project.status, 'value') else str(project.status)
        console.print(f"Type: {type_value}")
        console.print(f"Status: {status_value}")
        console.print(f"Created: {project.created_at.strftime('%Y-%m-%d %H:%M:%S')}")
        console.print(f"Updated: {project.updated_at.strftime('%Y-%m-%d %H:%M:%S')}")

        if detailed:
            # Get detailed statistics
            try:
                stats = await unified_service.get_project_stats(name)
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
        unified_service = await get_unified_project_service()

        # Get project
        project = await unified_service.get_project(name)
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
            updated_project = await unified_service.update_project(project)

        console.print(f"[green]✓[/green] Project '{name}' updated successfully!")

    except Exception as e:
        logger.error(f"Error updating project: {e}")
        console.print(f"[red]Error updating project: {str(e)}[/red]")


async def _recreate_project_impl(name: str, confirm: bool, force: bool):
    """Implementation of project recreation."""
    console = Console()

    try:
        unified_service = await get_unified_project_service()

        # Get project by name first to get its ID
        project = await unified_service.get_project_by_name(name)
        if not project:
            error_msg = CLI_ERROR_MESSAGES["project_not_found"].format(name=name)
            console.print(f"[red]Error: {error_msg}[/red]")
            return

        # Check compatibility
        compatibility_result = await unified_service.check_project_compatibility(project.id)
        if compatibility_result.is_compatible and not force:
            console.print(f"[yellow]Project '{name}' is already compatible with current schema[/yellow]")
            console.print("Use --force to recreate anyway")
            return

        # Confirmation prompt if not already confirmed
        if not confirm:
            console.print(f"[yellow]Warning: Recreation will reset all statistics and crawled data for '{name}'[/yellow]")
            console.print("Settings and metadata will be preserved.")
            response = console.input(f"Are you sure you want to recreate project '{name}'? [y/N]: ")
            if response.lower() not in ['y', 'yes']:
                console.print("[yellow]Operation cancelled[/yellow]")
                return

        # Recreate project
        with console.status(f"Recreating project '{name}'..."):
            new_project, migration_record = await unified_service.recreate_project(
                project.id,
                preserve_data=False,
                initiated_by_command="docbro project --recreate"
            )

        console.print(f"[green]✓[/green] Project '{name}' recreated successfully!")
        console.print(f"  Schema version: v{project.schema_version} → v{new_project.schema_version}")
        console.print(f"  Migration ID: {migration_record.id}")
        console.print(f"  Settings preserved: {len(new_project.settings)} items")
        console.print(f"  Metadata preserved: {len(new_project.metadata)} items")

    except IncompatibleProjectError as e:
        console.print(f"[red]Error: {str(e)}[/red]")
    except ProjectNotFoundError as e:
        console.print(f"[red]Error: {str(e)}[/red]")
    except Exception as e:
        logger.error(f"Error recreating project: {e}")
        console.print(f"[red]Error recreating project: {str(e)}[/red]")


async def _export_project_impl(name: str):
    """Implementation of project export."""
    console = Console()

    try:
        unified_service = await get_unified_project_service()
        export_service = ProjectExportService()

        # Get project
        project = await unified_service.get_project_by_name(name)
        if not project:
            error_msg = CLI_ERROR_MESSAGES["project_not_found"].format(name=name)
            console.print(f"[red]Error: {error_msg}[/red]")
            return

        # Export project
        with console.status(f"Exporting project '{name}'..."):
            export_path = await export_service.export_to_file(
                project=project,
                export_type="full",
                include_statistics=True,
                pretty_json=True
            )

        console.print(f"[green]✓[/green] Project '{name}' exported successfully!")
        console.print(f"  Export file: {export_path}")
        console.print(f"  Schema version: v{project.schema_version}")
        console.print(f"  Settings: {len(project.settings)} items")
        console.print(f"  Metadata: {len(project.metadata)} items")

        # Show file size
        file_size = export_path.stat().st_size
        console.print(f"  File size: {_format_bytes(file_size)}")

    except ProjectNotFoundError as e:
        console.print(f"[red]Error: {str(e)}[/red]")
    except Exception as e:
        logger.error(f"Error exporting project: {e}")
        console.print(f"[red]Error exporting project: {str(e)}[/red]")


async def _check_compatibility_impl(name: str):
    """Implementation of compatibility check."""
    console = Console()

    try:
        unified_service = await get_unified_project_service()
        compatibility_checker = CompatibilityChecker()

        # Get project
        project = await unified_service.get_project_by_name(name)
        if not project:
            error_msg = CLI_ERROR_MESSAGES["project_not_found"].format(name=name)
            console.print(f"[red]Error: {error_msg}[/red]")
            return

        # Check compatibility
        with console.status(f"Checking compatibility for project '{name}'..."):
            compatibility_result = await compatibility_checker.check_project_compatibility(project)

        # Display results
        console.print(f"\n[bold cyan]Compatibility Check: {project.name}[/bold cyan]")

        # Status
        if compatibility_result.is_compatible:
            console.print(f"Status: [green]Compatible[/green]")
        else:
            console.print(f"Status: [red]Incompatible[/red]")

        # Version info
        console.print(f"Project Schema Version: v{compatibility_result.project_version}")
        console.print(f"Current Schema Version: v{compatibility_result.current_version}")

        # Issues
        if compatibility_result.issues:
            console.print(f"\n[bold]Issues Found ({len(compatibility_result.issues)}):[/bold]")
            for issue in compatibility_result.issues:
                console.print(f"  • {issue}")

        # Missing fields
        if compatibility_result.missing_fields:
            console.print(f"\n[bold]Missing Fields ({len(compatibility_result.missing_fields)}):[/bold]")
            for field in compatibility_result.missing_fields:
                console.print(f"  • {field}")

        # Extra fields
        if compatibility_result.extra_fields:
            console.print(f"\n[bold]Extra Fields ({len(compatibility_result.extra_fields)}):[/bold]")
            for field in compatibility_result.extra_fields:
                console.print(f"  • {field}")

        # Recommendations
        if compatibility_result.needs_recreation:
            console.print(f"\n[bold yellow]Recommendation:[/bold yellow]")
            console.print("This project requires recreation to be compatible with the current schema.")

            # Get recreation instructions
            instructions = compatibility_checker.get_recreation_instructions(compatibility_result, project.name)
            console.print("\n[bold]Recreation Instructions:[/bold]")
            for instruction in instructions:
                console.print(instruction)

        elif compatibility_result.migration_required:
            console.print(f"\n[bold yellow]Recommendation:[/bold yellow]")
            console.print("This project can be automatically migrated to the current schema.")
        else:
            console.print(f"\n[bold green]✓[/bold green] No action required - project is fully compatible!")

    except ProjectNotFoundError as e:
        console.print(f"[red]Error: {str(e)}[/red]")
    except Exception as e:
        logger.error(f"Error checking compatibility: {e}")
        console.print(f"[red]Error checking compatibility: {str(e)}[/red]")


def _format_bytes(bytes_count: int) -> str:
    """Format bytes for human-readable display."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} PB"
