"""Enhanced setup command with progress display and retry logic."""
import asyncio
import click
from typing import Optional
from rich.console import Console
from src.services.installation_wizard_service import InstallationWizardService
from src.services.system_requirements_service import SystemRequirementsService
from src.core.lib_logger import get_logger

logger = get_logger(__name__)
console = Console()


@click.group()
def setup():
    """Setup and installation commands for DocBro."""
    pass


@setup.command()
@click.option('--force', is_flag=True, help='Force reinstallation of existing components')
@click.option('--port', type=int, help='Custom port for Qdrant service (default: 6333)')
@click.option('--data-dir', type=str, help='Custom data directory for Qdrant storage')
@click.option('--skip-checks', is_flag=True, help='Skip system requirements validation')
@click.option('--interactive/--no-interactive', default=True, help='Interactive setup mode')
def wizard(force: bool, port: Optional[int], data_dir: Optional[str], skip_checks: bool, interactive: bool):
    """Run the interactive DocBro setup wizard with progress display."""
    try:
        console.print("\n[bold blue]DocBro Setup Wizard[/bold blue]")
        console.print("Setting up DocBro with automatic dependency detection and service configuration...\n")

        # Store interactive mode in context for error handling
        ctx = click.get_current_context()
        ctx.obj = ctx.obj or {}
        ctx.obj['interactive'] = interactive

        # Run async setup
        result = asyncio.run(_run_setup_wizard(force, port, data_dir, skip_checks))

        if result["success"]:
            _display_success_summary(result)
        else:
            _display_failure_summary(result)
            raise click.ClickException("Setup failed")

    except KeyboardInterrupt:
        console.print("\n[yellow]Setup cancelled by user[/yellow]")
        raise click.Abort()
    except Exception as e:
        logger.error(f"Setup wizard failed: {e}")
        console.print(f"\n[red]Setup failed: {e}[/red]")
        raise click.ClickException("Setup failed")


async def _run_setup_wizard(
    force: bool,
    port: Optional[int],
    data_dir: Optional[str],
    skip_checks: bool
) -> dict:
    """Run the setup wizard asynchronously."""
    wizard_service = InstallationWizardService()

    # Pre-installation checks if not skipped
    if not skip_checks:
        console.print("[dim]Performing pre-installation validation...[/dim]")

        system_service = SystemRequirementsService()
        quick_valid = await system_service.quick_validation()

        if not quick_valid:
            # Get detailed requirements report
            requirements = await system_service.validate_all_requirements()
            report = system_service.generate_requirements_report(requirements)

            console.print("\n[red]Pre-installation checks failed:[/red]")
            for req, details in report["requirements"].items():
                if not details["passed"]:
                    console.print(f"  ✗ {req}: {details['current']} (required: {details['required']})")

            recommendations = system_service.get_installation_recommendations(requirements)
            console.print("\n[yellow]Recommendations:[/yellow]")
            for rec in recommendations:
                console.print(f"  • {rec}")

            return {"success": False, "error": "System requirements not met"}

    # Start installation
    console.print("[dim]Starting installation with progress tracking...[/dim]\n")

    return await wizard_service.start_installation(
        force_reinstall=force,
        custom_qdrant_port=port,
        custom_data_dir=data_dir
    )


def _display_success_summary(result: dict):
    """Display success summary with service information."""
    console.print("\n[green bold]✓ DocBro Setup Completed Successfully![/green bold]\n")

    # Display services
    if "services" in result and result["services"]:
        console.print("[bold]Services Status:[/bold]")
        for service in result["services"]:
            status_color = "green" if service["status"] == "RUNNING" else "yellow"
            console.print(f"  • {service['service_name']}: [{status_color}]{service['status']}[/{status_color}]")
            if service.get("health_check_url"):
                console.print(f"    Health check: {service['health_check_url']}")

    # Display MCP configuration
    if "mcp_config_path" in result:
        console.print(f"\n[bold]MCP Configuration:[/bold]")
        console.print(f"  • Config file: {result['mcp_config_path']}")

    # Next steps
    console.print("\n[bold]Next Steps:[/bold]")
    console.print("  • Run 'docbro system-check' to validate installation")
    console.print("  • Run 'docbro services status' to monitor services")
    console.print("  • Start using DocBro with 'docbro crawl' and 'docbro search'")


def _display_failure_summary(result: dict):
    """Display failure summary with troubleshooting information."""
    console.print("\n[red bold]✗ DocBro Setup Failed[/red bold]\n")

    if "error" in result:
        console.print(f"[red]Error: {result['error']}[/red]\n")

    # Display failed steps
    if "results" in result and "failed_steps" in result["results"]:
        console.print("[bold]Failed Steps:[/bold]")
        for step in result["results"]["failed_steps"]:
            console.print(f"  ✗ {step}")

    # Troubleshooting recommendations
    console.print("\n[bold]Troubleshooting:[/bold]")
    console.print("  • Check Docker is running: docker info")
    console.print("  • Verify system requirements: docbro system-check")
    console.print("  • Review logs for detailed error information")
    console.print("  • Try running setup with --force flag")


@setup.command()
@click.option('--service', type=click.Choice(['all', 'qdrant']), default='all', help='Service to validate')
@click.option('--fix', is_flag=True, help='Attempt to fix issues automatically')
def validate(service: str, fix: bool):
    """Validate current installation and optionally fix issues."""
    try:
        console.print(f"\n[bold blue]Validating DocBro Installation[/bold blue] ({service})\n")

        result = asyncio.run(_run_installation_validation(service, fix))

        if result["success"]:
            console.print("\n[green]✓ Installation validation passed[/green]")
        else:
            console.print(f"\n[red]✗ Installation validation failed: {result.get('error', 'Unknown error')}[/red]")
            raise click.ClickException("Validation failed")

    except Exception as e:
        logger.error(f"Validation failed: {e}")
        raise click.ClickException(f"Validation failed: {e}")


async def _run_installation_validation(service: str, fix: bool) -> dict:
    """Run installation validation asynchronously."""
    wizard_service = InstallationWizardService()

    # Check installation status
    status = await wizard_service.check_installation_status()

    console.print(f"Installation Status: [bold]{status['status']}[/bold]")

    if status["status"] == "COMPLETED":
        console.print("[green]All services are running correctly[/green]")
        return {"success": True}
    elif status["status"] == "PARTIAL":
        console.print("[yellow]Some services need attention[/yellow]")

        # Display service statuses
        for svc in status.get("services", []):
            status_color = "green" if svc["status"] == "RUNNING" else "red"
            console.print(f"  • {svc['service_name']}: [{status_color}]{svc['status']}[/{status_color}]")

        if fix:
            console.print("\n[dim]Attempting to fix issues...[/dim]")
            # Attempt to restart services
            # This would be implemented based on specific service issues
            return {"success": False, "error": "Auto-fix not yet implemented"}

        return {"success": False, "error": "Some services are not running"}
    else:
        return {"success": False, "error": "DocBro is not installed"}


@setup.command()
def status():
    """Show current DocBro installation status."""
    try:
        console.print("\n[bold blue]DocBro Installation Status[/bold blue]\n")

        result = asyncio.run(_get_installation_status())
        _display_status_info(result)

    except Exception as e:
        logger.error(f"Status check failed: {e}")
        console.print(f"[red]Status check failed: {e}[/red]")


async def _get_installation_status() -> dict:
    """Get installation status asynchronously."""
    wizard_service = InstallationWizardService()
    return await wizard_service.check_installation_status()


def _display_status_info(status: dict):
    """Display installation status information."""
    # Overall status
    status_value = status.get("status", "UNKNOWN")
    status_colors = {
        "COMPLETED": "green",
        "PARTIAL": "yellow",
        "NOT_INSTALLED": "red",
        "ERROR": "red"
    }
    status_color = status_colors.get(status_value, "dim")

    console.print(f"Overall Status: [{status_color}]{status_value}[/{status_color}]")

    # Services
    if "services" in status:
        console.print("\n[bold]Services:[/bold]")
        for service in status["services"]:
            svc_status = service.get("status", "UNKNOWN")
            svc_color = "green" if svc_status == "RUNNING" else "red"
            console.print(f"  • {service.get('service_name', 'unknown')}: [{svc_color}]{svc_status}[/{svc_color}]")

            if service.get("container_name"):
                console.print(f"    Container: {service['container_name']}")
            if service.get("port"):
                console.print(f"    Port: {service['port']}")

    # MCP Configuration
    if status.get("mcp_config_exists"):
        console.print(f"\n[bold]MCP Config:[/bold] [green]✓[/green] {status.get('mcp_config_path', '')}")
    else:
        console.print(f"\n[bold]MCP Config:[/bold] [red]✗ Not found[/red]")

    # Timestamp
    if "timestamp" in status:
        console.print(f"\n[dim]Last checked: {status['timestamp']}[/dim]")


@setup.command()
@click.confirmation_option(prompt='This will remove DocBro and all associated data. Continue?')
@click.option('--keep-data', is_flag=True, help='Keep data volumes (preserve vector database)')
@click.option('--force', is_flag=True, help='Force removal without confirmation')
def uninstall(keep_data: bool, force: bool):
    """Uninstall DocBro and associated components."""
    try:
        if not force:
            console.print("\n[red bold]WARNING: This will permanently remove DocBro and all associated data![/red bold]")

        console.print("\n[dim]Starting DocBro uninstall...[/dim]\n")

        result = asyncio.run(_run_uninstall(not keep_data))

        if result["success"]:
            console.print("\n[green]✓ DocBro uninstalled successfully[/green]")

            if result.get("removed_components"):
                console.print("\n[bold]Removed components:[/bold]")
                for component in result["removed_components"]:
                    console.print(f"  • {component}")
        else:
            console.print(f"\n[red]✗ Uninstall failed: {result.get('error', 'Unknown error')}[/red]")

            if result.get("errors"):
                console.print("\n[bold]Errors encountered:[/bold]")
                for error in result["errors"]:
                    console.print(f"  • {error}")

            raise click.ClickException("Uninstall failed")

    except click.Abort:
        console.print("\n[yellow]Uninstall cancelled[/yellow]")
    except Exception as e:
        logger.error(f"Uninstall failed: {e}")
        raise click.ClickException(f"Uninstall failed: {e}")


async def _run_uninstall(remove_data: bool) -> dict:
    """Run uninstall process asynchronously."""
    wizard_service = InstallationWizardService()
    return await wizard_service.uninstall_docbro(remove_data=remove_data)


if __name__ == "__main__":
    setup()