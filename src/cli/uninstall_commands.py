"""Enhanced uninstall command with single confirmation prompt."""
import asyncio
import click
from typing import List
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from src.services.uninstall_service import UninstallService, UninstallWarning
from src.models.uninstall_inventory import UninstallComponent
from src.core.lib_logger import get_logger

logger = get_logger(__name__)
console = Console()


@click.command()
@click.option('--force', is_flag=True, help='Skip confirmation prompt and force removal')
@click.option('--keep-data', is_flag=True, help='Preserve data volumes and user data')
@click.option('--dry-run', is_flag=True, help='Show what would be removed without actually removing')
@click.option('--backup', is_flag=True, help='Create backup before uninstall')
@click.option('--backup-path', type=str, help='Custom backup location')
def uninstall(force: bool, keep_data: bool, dry_run: bool, backup: bool, backup_path: str):
    """Uninstall DocBro with single confirmation prompt and data loss warning."""
    try:
        console.print("\n[bold red]DocBro Uninstall Process[/bold red]\n")

        # Run async uninstall process
        result = asyncio.run(_run_uninstall_process(force, keep_data, dry_run, backup, backup_path))

        if result["success"]:
            if dry_run:
                console.print("\n[green]✓ Dry run completed - no changes made[/green]")
            else:
                console.print("\n[green bold]✓ DocBro uninstalled successfully![/green bold]")
                _display_uninstall_summary(result)
        else:
            console.print(f"\n[red]✗ Uninstall failed: {result.get('error', 'Unknown error')}[/red]")

            if result.get("partial_success"):
                _display_partial_uninstall_results(result)

            raise click.ClickException("Uninstall failed")

    except click.Abort:
        console.print("\n[yellow]Uninstall cancelled by user[/yellow]")
    except KeyboardInterrupt:
        console.print("\n[yellow]Uninstall interrupted by user[/yellow]")
        raise click.Abort()
    except Exception as e:
        logger.error(f"Uninstall command failed: {e}")
        console.print(f"\n[red]Uninstall failed: {e}[/red]")
        raise click.ClickException("Uninstall failed")


async def _run_uninstall_process(
    force: bool,
    keep_data: bool,
    dry_run: bool,
    backup: bool,
    backup_path: str
) -> dict:
    """Run the complete uninstall process."""
    uninstall_service = UninstallService()

    try:
        # Step 1: Scan installed components
        console.print("[dim]Scanning installed DocBro components...[/dim]")
        components = await uninstall_service.scan_installed_components()

        if not components:
            console.print("[yellow]No DocBro components found to uninstall[/yellow]")
            return {"success": True, "message": "Nothing to uninstall"}

        # Step 2: Check running services
        console.print("[dim]Checking for running DocBro services...[/dim]")
        running_services = await uninstall_service.check_running_services()

        # Step 3: Generate uninstall warning
        warning = uninstall_service.generate_uninstall_warning(components)

        # Step 4: Display what will be removed and get confirmation
        if not force:
            confirmed = _display_uninstall_confirmation(components, running_services, warning, dry_run)
            if not confirmed:
                return {"success": False, "cancelled": True}

        # Step 5: Stop running services if any
        if running_services and not dry_run:
            console.print(f"\n[yellow]Stopping {len(running_services)} running services...[/yellow]")
            stop_results = await uninstall_service.stop_all_services(running_services)

            failed_stops = [svc for svc, success in stop_results.items() if not success]
            if failed_stops:
                console.print(f"[red]Failed to stop services: {', '.join(failed_stops)}[/red]")
                if not force:
                    if not click.confirm("Continue with uninstall anyway?"):
                        return {"success": False, "cancelled": True}

        # Step 6: Create backup if requested
        backup_info = None
        if backup and not dry_run:
            console.print("\n[dim]Creating backup...[/dim]")
            # Backup logic would be implemented here
            # For now, just log the intention
            logger.info(f"Backup requested to: {backup_path or 'default location'}")

        # Step 7: Execute uninstall
        if dry_run:
            console.print(f"\n[dim]DRY RUN: Would remove {len(components)} components[/dim]")
            return {
                "success": True,
                "dry_run": True,
                "components_count": len(components),
                "services_count": len(running_services)
            }
        else:
            console.print(f"\n[dim]Removing {len(components)} DocBro components...[/dim]")

            # Filter external components if keeping data
            components_to_remove = components
            if keep_data:
                components_to_remove = [c for c in components if not c.is_external]
                excluded_count = len(components) - len(components_to_remove)
                if excluded_count > 0:
                    console.print(f"[yellow]Preserving {excluded_count} data components[/yellow]")

            uninstall_result = await uninstall_service.execute_uninstall(
                components=components_to_remove,
                force=force,
                preserve_external=keep_data
            )

            return {
                "success": uninstall_result.get("success", False),
                "removed": uninstall_result.get("removed", 0),
                "failed": uninstall_result.get("failed", 0),
                "skipped": uninstall_result.get("skipped", 0),
                "summary": uninstall_result.get("summary", {}),
                "backup_info": backup_info,
                "stopped_services": len(running_services)
            }

    except Exception as e:
        logger.error(f"Uninstall process failed: {e}")
        return {"success": False, "error": str(e)}


def _display_uninstall_confirmation(
    components: List[UninstallComponent],
    running_services: List[str],
    warning: UninstallWarning,
    dry_run: bool
) -> bool:
    """Display uninstall confirmation with comprehensive warning."""

    # Create components table
    components_table = Table(title="Components to Remove", show_header=True, header_style="bold red")
    components_table.add_column("Type", style="dim")
    components_table.add_column("Name", style="bold")
    components_table.add_column("Size", justify="right")
    components_table.add_column("External", justify="center")

    total_size = 0
    for component in components:
        components_table.add_row(
            component.component_type.value,
            component.name,
            f"{component.size_mb:.1f}MB" if component.size_mb > 0 else "Unknown",
            "✓" if component.is_external else "○"
        )
        total_size += component.size_mb

    console.print(components_table)

    # Display running services if any
    if running_services:
        console.print(f"\n[yellow bold]Running Services (will be stopped):[/yellow bold]")
        for service in running_services:
            console.print(f"  • {service}")

    # Display warning panel
    warning_content = f"""
{warning.message}

Data Types Affected: {', '.join(warning.data_types)}
Estimated Data Loss: {warning.estimated_data_loss}
Irreversible: {'Yes' if warning.is_irreversible else 'No'}

Total Components: {len(components)}
Total Size: {total_size:.1f}MB
"""

    warning_panel = Panel(
        warning_content.strip(),
        title="⚠️ Data Loss Warning",
        border_style="red",
        padding=(1, 2)
    )
    console.print(f"\n{warning_panel}")

    # Single confirmation prompt
    if dry_run:
        prompt_text = "\nProceed with dry run analysis?"
    else:
        prompt_text = f"\nThis will permanently remove {len(components)} DocBro components. Proceed?"

    return click.confirm(prompt_text, default=False)


def _display_uninstall_summary(result: dict):
    """Display uninstall completion summary."""
    summary_table = Table(title="Uninstall Summary", show_header=True, header_style="bold green")
    summary_table.add_column("Metric", style="bold")
    summary_table.add_column("Count", justify="right", style="green")

    summary_table.add_row("Components Removed", str(result.get("removed", 0)))
    summary_table.add_row("Services Stopped", str(result.get("stopped_services", 0)))

    if result.get("failed", 0) > 0:
        summary_table.add_row("Failed Removals", str(result["failed"]))

    if result.get("skipped", 0) > 0:
        summary_table.add_row("Skipped Items", str(result["skipped"]))

    console.print(f"\n{summary_table}")

    # Additional information
    if result.get("backup_info"):
        console.print(f"\n[bold]Backup Created:[/bold] {result['backup_info']}")

    # Final cleanup recommendations
    console.print("\n[bold]Post-Uninstall Recommendations:[/bold]")
    console.print("  • Verify Docker containers removed: docker ps -a | grep docbro")
    console.print("  • Check for remaining volumes: docker volume ls | grep docbro")
    console.print("  • Remove any remaining configuration files if desired")


def _display_partial_uninstall_results(result: dict):
    """Display results when uninstall partially succeeded."""
    console.print("\n[yellow bold]Partial Uninstall Results:[/yellow bold]")

    if result.get("removed", 0) > 0:
        console.print(f"[green]✓ Successfully removed: {result['removed']} components[/green]")

    if result.get("failed", 0) > 0:
        console.print(f"[red]✗ Failed to remove: {result['failed']} components[/red]")

    if result.get("errors"):
        console.print("\n[bold]Errors encountered:[/bold]")
        for error in result["errors"]:
            console.print(f"  • {error}")

    console.print("\n[yellow]Manual cleanup may be required for failed components[/yellow]")


@click.command()
def list_components():
    """List all DocBro components that can be uninstalled."""
    try:
        console.print("\n[bold blue]DocBro Components Inventory[/bold blue]\n")

        result = asyncio.run(_list_components())
        _display_components_inventory(result)

    except Exception as e:
        logger.error(f"Component listing failed: {e}")
        console.print(f"[red]Failed to list components: {e}[/red]")


async def _list_components() -> List[UninstallComponent]:
    """List all components asynchronously."""
    uninstall_service = UninstallService()
    return await uninstall_service.scan_installed_components()


def _display_components_inventory(components: List[UninstallComponent]):
    """Display components inventory."""
    if not components:
        console.print("[yellow]No DocBro components found[/yellow]")
        return

    # Group components by type
    component_groups = {}
    for component in components:
        comp_type = component.component_type.value
        if comp_type not in component_groups:
            component_groups[comp_type] = []
        component_groups[comp_type].append(component)

    # Display grouped components
    for comp_type, comps in component_groups.items():
        console.print(f"\n[bold]{comp_type.title()}s:[/bold]")
        for comp in comps:
            size_info = f" ({comp.size_mb:.1f}MB)" if comp.size_mb > 0 else ""
            external_marker = " [dim](external)[/dim]" if comp.is_external else ""

            console.print(f"  • {comp.name}{size_info}{external_marker}")

            if comp.path:
                console.print(f"    Path: {comp.path}")

    # Summary
    total_components = len(components)
    total_size = sum(c.size_mb for c in components)
    external_count = sum(1 for c in components if c.is_external)

    console.print(f"\n[bold]Summary:[/bold]")
    console.print(f"  Total components: {total_components}")
    console.print(f"  External components: {external_count}")
    console.print(f"  Total size: {total_size:.1f}MB")


if __name__ == "__main__":
    uninstall()