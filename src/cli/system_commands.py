"""System check command for installation validation."""
import asyncio
import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from src.services.system_requirements_service import SystemRequirementsService
from src.services.installation_wizard_service import InstallationWizardService
from src.services.docker_service_manager import DockerServiceManager
from src.services.qdrant_container_service import QdrantContainerService
from src.core.lib_logger import get_logger

logger = get_logger(__name__)
console = Console()


@click.group()
def system():
    """System validation and diagnostic commands."""
    pass


@system.command()
@click.option('--detailed', is_flag=True, help='Show detailed system information')
@click.option('--requirements-only', is_flag=True, help='Check only system requirements')
@click.option('--services-only', is_flag=True, help='Check only service status')
@click.option('--fix', is_flag=True, help='Attempt to fix detected issues')
def check(detailed: bool, requirements_only: bool, services_only: bool, fix: bool):
    """Comprehensive system check for DocBro installation validation."""
    try:
        console.print("\n[bold blue]DocBro System Check[/bold blue]\n")

        # Run system validation with progress indicator
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
            transient=True
        ) as progress:
            task = progress.add_task("Running system diagnostics...", total=None)

            result = asyncio.run(_run_system_check(
                detailed, requirements_only, services_only, fix
            ))

            progress.update(task, completed=True)

        # Display results
        _display_system_check_results(result)

        # Exit with appropriate code
        if not result["overall_health"]:
            raise click.ClickException("System check failed")

    except Exception as e:
        logger.error(f"System check failed: {e}")
        console.print(f"[red]System check failed: {e}[/red]")
        raise click.ClickException("System check failed")


async def _run_system_check(
    detailed: bool,
    requirements_only: bool,
    services_only: bool,
    fix: bool
) -> dict:
    """Run comprehensive system check."""
    results = {
        "overall_health": True,
        "requirements": {},
        "services": {},
        "installation": {},
        "recommendations": []
    }

    system_service = SystemRequirementsService()

    try:
        # System Requirements Check
        if not services_only:
            console.print("[dim]Checking system requirements...[/dim]")
            requirements = await system_service.validate_all_requirements()
            requirements_report = system_service.generate_requirements_report(requirements)

            results["requirements"] = {
                "validation_results": requirements,
                "report": requirements_report,
                "passed": requirements_report["overall_passed"]
            }

            if not requirements_report["overall_passed"]:
                results["overall_health"] = False
                results["recommendations"].extend(
                    system_service.get_installation_recommendations(requirements)
                )

        # Services Check
        if not requirements_only:
            console.print("[dim]Checking DocBro services...[/dim]")
            services_status = await _check_services_health()
            results["services"] = services_status

            if not services_status["all_healthy"]:
                results["overall_health"] = False

            # Installation Status Check
            console.print("[dim]Checking installation status...[/dim]")
            wizard_service = InstallationWizardService()
            installation_status = await wizard_service.check_installation_status()
            results["installation"] = installation_status

            if installation_status["status"] != "COMPLETED":
                results["overall_health"] = False

        # Fix issues if requested
        if fix and not results["overall_health"]:
            console.print("[dim]Attempting to fix detected issues...[/dim]")
            fix_results = await _attempt_fixes(results)
            results["fix_results"] = fix_results

        return results

    except Exception as e:
        logger.error(f"System check execution failed: {e}")
        results["error"] = str(e)
        results["overall_health"] = False
        return results


async def _check_services_health() -> dict:
    """Check health of all DocBro services."""
    services_status = {
        "all_healthy": True,
        "services": {},
        "docker_available": False,
        "containers_running": 0,
        "containers_total": 0
    }

    try:
        # Check Docker availability
        docker_manager = DockerServiceManager()
        docker_available = await docker_manager.validate_docker_availability()
        services_status["docker_available"] = docker_available

        if docker_available:
            # Check DocBro containers
            containers = await docker_manager.list_docbro_containers()
            services_status["containers_total"] = len(containers)

            running_containers = [c for c in containers if c["status"] == "running"]
            services_status["containers_running"] = len(running_containers)

            # Check specific services
            qdrant_service = QdrantContainerService(docker_manager)

            # Qdrant check
            qdrant_status = await qdrant_service.get_qdrant_status()
            services_status["services"]["qdrant"] = {
                "name": "Qdrant Vector Database",
                "status": qdrant_status.status.value,
                "container_name": qdrant_status.container_name,
                "port": qdrant_status.port,
                "healthy": qdrant_status.status.value == "RUNNING"
            }

            if qdrant_status.status.value != "RUNNING":
                services_status["all_healthy"] = False
        else:
            services_status["all_healthy"] = False

        return services_status

    except Exception as e:
        logger.error(f"Services health check failed: {e}")
        services_status["error"] = str(e)
        services_status["all_healthy"] = False
        return services_status


async def _attempt_fixes(results: dict) -> dict:
    """Attempt to fix detected issues."""
    fix_results = {"attempted": [], "successful": [], "failed": []}

    try:
        # Try to start stopped services
        if "services" in results and not results["services"]["all_healthy"]:
            for service_name, service_info in results["services"]["services"].items():
                if not service_info["healthy"]:
                    fix_results["attempted"].append(f"start_{service_name}")

                    if service_name == "qdrant":
                        try:
                            qdrant_service = QdrantContainerService()
                            success = await qdrant_service.start_qdrant()
                            if success:
                                fix_results["successful"].append(f"start_{service_name}")
                            else:
                                fix_results["failed"].append(f"start_{service_name}")
                        except Exception as e:
                            fix_results["failed"].append(f"start_{service_name}: {e}")

        return fix_results

    except Exception as e:
        logger.error(f"Fix attempt failed: {e}")
        fix_results["error"] = str(e)
        return fix_results


def _display_system_check_results(results: dict):
    """Display comprehensive system check results."""
    # Overall health status
    if results["overall_health"]:
        health_panel = Panel(
            "[green bold]✓ System Health: GOOD[/green bold]\nAll checks passed successfully.",
            title="System Status",
            border_style="green"
        )
    else:
        health_panel = Panel(
            "[red bold]✗ System Health: ISSUES DETECTED[/red bold]\nSome checks failed. See details below.",
            title="System Status",
            border_style="red"
        )

    console.print(health_panel)

    # System Requirements
    if "requirements" in results:
        _display_requirements_results(results["requirements"])

    # Services Status
    if "services" in results:
        _display_services_results(results["services"])

    # Installation Status
    if "installation" in results:
        _display_installation_results(results["installation"])

    # Fix Results
    if "fix_results" in results:
        _display_fix_results(results["fix_results"])

    # Recommendations
    if results.get("recommendations"):
        _display_recommendations(results["recommendations"])


def _display_requirements_results(requirements: dict):
    """Display system requirements results."""
    console.print("\n[bold]System Requirements[/bold]")

    req_table = Table(show_header=True, header_style="bold blue")
    req_table.add_column("Requirement", style="dim")
    req_table.add_column("Status", width=12)
    req_table.add_column("Current", width=20)
    req_table.add_column("Required", width=20)

    if "report" in requirements:
        for req_name, req_info in requirements["report"]["requirements"].items():
            status = "[green]✓ PASS[/green]" if req_info["passed"] else "[red]✗ FAIL[/red]"

            req_table.add_row(
                req_name.replace("_", " ").title(),
                status,
                req_info["current"],
                req_info["required"]
            )

    console.print(req_table)


def _display_services_results(services: dict):
    """Display services status results."""
    console.print("\n[bold]Services Status[/bold]")

    # Docker status
    docker_status = "[green]✓ Available[/green]" if services["docker_available"] else "[red]✗ Not Available[/red]"
    console.print(f"Docker: {docker_status}")

    # Container summary
    if services["docker_available"]:
        console.print(f"DocBro Containers: {services['containers_running']}/{services['containers_total']} running")

    # Individual services
    if "services" in services:
        svc_table = Table(show_header=True, header_style="bold blue")
        svc_table.add_column("Service", style="dim")
        svc_table.add_column("Status", width=15)
        svc_table.add_column("Container", width=25)
        svc_table.add_column("Port", width=10)

        for svc_name, svc_info in services["services"].items():
            status = "[green]✓ HEALTHY[/green]" if svc_info["healthy"] else "[red]✗ UNHEALTHY[/red]"

            svc_table.add_row(
                svc_info["name"],
                status,
                svc_info.get("container_name", "N/A"),
                str(svc_info.get("port", "N/A"))
            )

        console.print(svc_table)


def _display_installation_results(installation: dict):
    """Display installation status results."""
    console.print("\n[bold]Installation Status[/bold]")

    status = installation.get("status", "UNKNOWN")
    status_colors = {
        "COMPLETED": "green",
        "PARTIAL": "yellow",
        "NOT_INSTALLED": "red",
        "ERROR": "red"
    }
    status_color = status_colors.get(status, "dim")

    console.print(f"Status: [{status_color}]{status}[/{status_color}]")

    if "services" in installation and installation["services"]:
        console.print("\nInstalled Services:")
        for service in installation["services"]:
            svc_status = service.get("status", "UNKNOWN")
            svc_color = "green" if svc_status == "RUNNING" else "red"
            console.print(f"  • {service.get('service_name', 'unknown')}: [{svc_color}]{svc_status}[/{svc_color}]")

    mcp_status = "[green]✓[/green]" if installation.get("mcp_config_exists") else "[red]✗[/red]"
    console.print(f"MCP Configuration: {mcp_status}")


def _display_fix_results(fix_results: dict):
    """Display fix attempt results."""
    if fix_results.get("attempted"):
        console.print("\n[bold]Fix Attempts[/bold]")

        for attempt in fix_results["attempted"]:
            if attempt in fix_results.get("successful", []):
                console.print(f"  [green]✓[/green] {attempt} - Fixed successfully")
            else:
                console.print(f"  [red]✗[/red] {attempt} - Fix failed")


def _display_recommendations(recommendations: list):
    """Display recommendations for fixing issues."""
    console.print("\n[bold yellow]Recommendations[/bold yellow]")
    for i, rec in enumerate(recommendations, 1):
        console.print(f"  {i}. {rec}")


@system.command()
@click.option('--output', type=click.Choice(['table', 'json']), default='table', help='Output format')
def info(output: str):
    """Display detailed system information."""
    try:
        console.print("\n[bold blue]DocBro System Information[/bold blue]\n")

        result = asyncio.run(_get_system_info())

        if output == 'json':
            import json
            console.print(json.dumps(result, indent=2, default=str))
        else:
            _display_system_info_table(result)

    except Exception as e:
        logger.error(f"System info failed: {e}")
        console.print(f"[red]System info failed: {e}[/red]")


async def _get_system_info() -> dict:
    """Get detailed system information."""
    system_service = SystemRequirementsService()
    system_info = system_service.get_system_info()

    docker_manager = DockerServiceManager()
    docker_available = await docker_manager.validate_docker_availability()

    return {
        "system": system_info.to_dict(),
        "docker_available": docker_available,
        "timestamp": system_info.detection_timestamp.isoformat()
    }


def _display_system_info_table(info: dict):
    """Display system information in table format."""
    info_table = Table(title="System Information", show_header=True, header_style="bold blue")
    info_table.add_column("Property", style="bold")
    info_table.add_column("Value", style="dim")

    system_info = info["system"]
    info_table.add_row("Python Version", system_info["python_version"])
    info_table.add_row("Operating System", f"{system_info['operating_system']} {system_info['os_version']}")
    info_table.add_row("Architecture", system_info["architecture"])
    info_table.add_row("Memory", f"{system_info['memory_gb']:.1f} GB")
    info_table.add_row("Available Disk", f"{system_info['disk_gb']:.1f} GB")
    info_table.add_row("Docker Available", "✓ Yes" if info["docker_available"] else "✗ No")
    info_table.add_row("Detection Time", info["timestamp"])

    console.print(info_table)


if __name__ == "__main__":
    system()