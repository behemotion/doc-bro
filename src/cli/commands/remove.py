"""Remove command for DocBro CLI."""

import asyncio
from typing import Optional

import click
from rich.console import Console
from rich.prompt import Confirm

# Optional uvloop for better performance
try:
    import uvloop
    UVLOOP_AVAILABLE = True
except ImportError:
    UVLOOP_AVAILABLE = False


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


@click.command(name="remove")
@click.argument("name", required=False)
@click.option("--confirm", is_flag=True, help="Skip confirmation prompt")
@click.option("--all", is_flag=True, help="Remove all projects")
@click.pass_context
def remove(ctx: click.Context, name: Optional[str], confirm: bool, all: bool):
    """Remove a documentation project and all its data.
    
    Aliases: delete, erase
    
    Usage:
      docbro remove myproject        # Remove single project
      docbro delete myproject        # Alias
      docbro erase --all            # Remove all projects
    """
    async def _remove():
        app = get_app()
        await app.initialize()

        # Capture the name parameter in the nested function scope
        project_name = name

        try:
            # Handle --all flag
            if all:
                # Get all projects
                projects = await app.db_manager.list_projects()
                if not projects:
                    app.console.print("[yellow]No projects found to remove.[/yellow]")
                    return

                # Display projects to be removed
                app.console.print("\n[bold red]⚠️  WARNING: This action is IRREVERSIBLE![/bold red]\n")
                app.console.print(f"The following {len(projects)} project(s) will be permanently removed:")
                for project in projects:
                    status_str = project.status.value if hasattr(project.status, 'value') else str(project.status)
                    app.console.print(f"  - {project.name} ({status_str})")

                if not confirm:
                    app.console.print("\n[red]This will delete all projects and their data![/red]")
                    if not Confirm.ask("[bold red]Are you absolutely sure you want to remove ALL projects?[/bold red]", default=False):
                        app.console.print("[yellow]Operation cancelled.[/yellow]")
                        return

                    # Double confirmation for safety
                    if not Confirm.ask("[bold red]This is your last chance. Remove ALL projects?[/bold red]", default=False):
                        app.console.print("[yellow]Operation cancelled.[/yellow]")
                        return

                # Remove all projects
                removed_count = 0
                failed_count = 0
                for project in projects:
                    try:
                        cleanup_result = await app.db_manager.cleanup_project(project.id)
                        if cleanup_result["success"]:
                            app.console.print(f"[green]✓[/green] Removed project '{project.name}'")
                            removed_count += 1
                        else:
                            app.console.print(f"[red]✗[/red] Failed to remove project '{project.name}'")
                            failed_count += 1
                    except Exception as e:
                        app.console.print(f"[red]✗[/red] Error removing project '{project.name}': {e}")
                        failed_count += 1

                # Summary
                if failed_count == 0:
                    app.console.print(f"\n[green]✓ Successfully removed all {removed_count} projects[/green]")
                else:
                    app.console.print(f"\n[yellow]⚠️  Removed {removed_count} projects, {failed_count} failed[/yellow]")

            else:
                # Handle single project removal
                if not project_name:
                    # Interactive project selection
                    projects = await app.db_manager.list_projects()
                    if not projects:
                        app.console.print("[yellow]No projects found.[/yellow]")
                        return
                    
                    app.console.print("\n[cyan]Select a project to remove:[/cyan]")
                    for i, project in enumerate(projects, 1):
                        app.console.print(f"  {i}. {project.name}")
                    
                    app.console.print("\nEnter project number (or 0 to cancel): ", end="")
                    try:
                        choice = int(input())
                        if choice == 0:
                            app.console.print("[yellow]Operation cancelled.[/yellow]")
                            return
                        if choice < 1 or choice > len(projects):
                            raise ValueError("Invalid choice")
                        selected_project = projects[choice - 1]
                        project_name = selected_project.name
                    except (ValueError, EOFError):
                        app.console.print("[red]Invalid selection. Operation cancelled.[/red]")
                        return

                project = await app.db_manager.get_project_by_name(project_name)
                if not project:
                    raise click.ClickException(f"Project '{project_name}' not found")

                if not confirm:
                    app.console.print(f"\n[yellow]This will permanently delete project '{project_name}' and all its data.[/yellow]")
                    if not Confirm.ask(f"Are you sure you want to remove project '{project_name}'?", default=False):
                        app.console.print("[yellow]Operation cancelled.[/yellow]")
                        return

                # Clean up project data
                cleanup_result = await app.db_manager.cleanup_project(project.id)

                if cleanup_result["success"]:
                    app.console.print(f"[green]✓[/green] Project '{project_name}' removed successfully")
                    app.console.print("[dim]All associated data has been deleted.[/dim]")
                else:
                    error = cleanup_result.get("error", "Unknown error")
                    raise click.ClickException(f"Failed to remove project: {error}")

        except Exception as e:
            app.console.print(f"[red]✗ Failed to remove project: {e}[/red]")
            raise click.ClickException(str(e))
        finally:
            await app.cleanup()

    run_async(_remove())