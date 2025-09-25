"""CLI commands for managing external service setup and configuration."""

import asyncio
from typing import Optional, List
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm, Prompt, IntPrompt
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.text import Text

from src.services.service_manager import ServiceConfigurationService, ServiceConflictError, ServiceSetupError
from src.services.detection import ServiceDetectionService
from src.services.config import ConfigService
from src.models.service_config import ServiceName, ServiceStatusType, ServiceConfiguration


# Global console for rich output
console = Console()


def run_async(coro):
    """Run async coroutine in sync context."""
    # Optional uvloop for better performance
    try:
        import uvloop
        uvloop.install()
    except ImportError:
        pass

    return asyncio.run(coro)


@click.group(name='services')
@click.pass_context
def services_group(ctx: click.Context):
    """Manage external service setup and configuration.

    Commands for managing Docker, Qdrant, Ollama, and other external services
    that DocBro depends on for full functionality.
    """
    ctx.ensure_object(dict)


@services_group.command('list')
@click.option('--service', '-s', help='Filter by specific service name')
@click.option('--status', help='Filter by service status')
@click.option('--detailed', '-d', is_flag=True, help='Show detailed service information')
@click.pass_context
def list_services(ctx: click.Context, service: Optional[str], status: Optional[str], detailed: bool):
    """List all external services with their current status.

    Shows service availability, versions, endpoints, and configuration status.
    """
    async def _list_services():
        service_manager = ServiceConfigurationService()

        try:
            # Get service configurations or detect if none exist
            configs = await service_manager.get_all_configurations()

            # If no configs exist, perform fresh detection
            if not configs:
                console.print("[yellow]No service configurations found. Performing service detection...[/yellow]\n")

                # Detect all services
                detection_service = ServiceDetectionService()
                statuses = await detection_service.check_all_services()

                # Create configurations from detection results
                for service_name, service_status in statuses.items():
                    try:
                        config = await service_manager.setup_service(
                            ServiceName(service_name),
                            auto_start=False
                        )
                        configs[service_name] = config
                    except Exception as e:
                        console.print(f"[yellow]Warning: Failed to setup {service_name}: {e}[/yellow]")
            else:
                # Refresh existing configurations
                for service_name in configs.keys():
                    try:
                        configs[service_name] = await service_manager.refresh_service_status(ServiceName(service_name))
                    except Exception as e:
                        console.print(f"[yellow]Warning: Failed to refresh {service_name}: {e}[/yellow]")

            # Apply filters
            if service:
                configs = {k: v for k, v in configs.items() if k.lower() == service.lower()}
                if not configs:
                    console.print(f"[red]Service '{service}' not found or not supported[/red]")
                    return

            if status:
                configs = {k: v for k, v in configs.items() if v.status.lower() == status.lower()}
                if not configs:
                    console.print(f"[yellow]No services found with status '{status}'[/yellow]")
                    return

            if not configs:
                console.print("No services found.")
                return

            # Create display table
            table = Table(title="External Services Status", show_header=True, header_style="bold cyan")
            table.add_column("Service", style="cyan", no_wrap=True)
            table.add_column("Status", justify="center")
            table.add_column("Version", style="dim")
            table.add_column("Endpoint", style="blue")
            table.add_column("Port", justify="right")

            if detailed:
                table.add_column("Auto-Start", justify="center")
                table.add_column("Health", justify="center")
                table.add_column("Error", style="red")

            # Populate table rows
            for service_name, config in sorted(configs.items()):
                # Status with color coding
                status_text = config.status
                if config.status == ServiceStatusType.RUNNING:
                    status_color = "[green]●[/green]"
                elif config.status == ServiceStatusType.CONFIGURED:
                    status_color = "[yellow]●[/yellow]"
                elif config.status == ServiceStatusType.FAILED:
                    status_color = "[red]●[/red]"
                else:
                    status_color = "[dim]●[/dim]"

                status_display = f"{status_color} {status_text}"

                # Version display
                version_display = config.detected_version or "Unknown"

                # Basic columns
                row_data = [
                    service_name.title(),
                    status_display,
                    version_display,
                    config.endpoint,
                    str(config.port)
                ]

                # Additional detailed columns
                if detailed:
                    auto_start = "[green]Yes[/green]" if config.auto_start else "[dim]No[/dim]"
                    health = "[green]Healthy[/green]" if config.is_healthy() else "[red]Unhealthy[/red]"
                    error = config.error_message[:50] + "..." if config.error_message and len(config.error_message) > 50 else (config.error_message or "")

                    row_data.extend([auto_start, health, error])

                table.add_row(*row_data)

            console.print(table)

            # Summary information
            total_services = len(configs)
            healthy_services = sum(1 for config in configs.values() if config.is_healthy())
            needs_attention = sum(1 for config in configs.values() if config.needs_attention())

            console.print(f"\n[dim]Summary: {healthy_services}/{total_services} services healthy")
            if needs_attention > 0:
                console.print(f"[yellow]{needs_attention} service(s) need attention[/yellow]")

        except Exception as e:
            console.print(f"[red]✗ Failed to list services: {e}[/red]")
            raise click.ClickException(str(e))

    run_async(_list_services())


@services_group.command('setup')
@click.option('--service', '-s', help='Setup specific service (docker, qdrant, ollama)')
@click.option('--auto-start', is_flag=True, help='Enable auto-start for the service')
@click.option('--port', type=int, help='Custom port for the service')
@click.option('--endpoint', help='Custom endpoint URL for the service')
@click.option('--force', is_flag=True, help='Force setup even if service already configured')
@click.pass_context
def setup_services(ctx: click.Context, service: Optional[str], auto_start: bool,
                   port: Optional[int], endpoint: Optional[str], force: bool):
    """Setup and configure external services.

    Interactive setup wizard for Docker, Qdrant, Ollama and other services.
    Handles port conflicts, dependency checks, and auto-start configuration.
    """
    async def _setup_services():
        service_manager = ServiceConfigurationService()

        try:
            # Determine which services to setup
            services_to_setup = []

            if service:
                # Setup specific service
                try:
                    service_name = ServiceName(service.lower())
                    services_to_setup.append(service_name)
                except ValueError:
                    available_services = [s.value for s in ServiceName]
                    console.print(f"[red]Invalid service '{service}'. Available services: {', '.join(available_services)}[/red]")
                    return
            else:
                # Interactive service selection
                console.print("[bold]DocBro Service Setup[/bold]\n")
                console.print("Select which services to setup:")

                available_services = [
                    (ServiceName.DOCKER, "Docker - Container runtime for Qdrant and other services"),
                    (ServiceName.QDRANT, "Qdrant - Vector database for document search"),
                    (ServiceName.OLLAMA, "Ollama - Local embeddings and language models")
                ]

                for service_enum, description in available_services:
                    if Confirm.ask(f"Setup {service_enum.value}? ({description})", default=True):
                        services_to_setup.append(service_enum)

                if not services_to_setup:
                    console.print("[yellow]No services selected for setup.[/yellow]")
                    return

            # Check existing configurations
            if not force:
                existing_configs = await service_manager.get_all_configurations()
                already_configured = [s for s in services_to_setup if s in existing_configs and existing_configs[s].is_healthy()]

                if already_configured:
                    services_list = ", ".join(s.value for s in already_configured)
                    if not Confirm.ask(f"Services already configured: {services_list}. Continue anyway?", default=False):
                        console.print("[yellow]Setup cancelled.[/yellow]")
                        return

            # Setup services with progress tracking
            console.print(f"\n[bold]Setting up {len(services_to_setup)} service(s)...[/bold]\n")

            setup_requests = []
            for service_name in services_to_setup:
                # Interactive configuration for each service
                console.print(f"[cyan]Configuring {service_name.value}...[/cyan]")

                # Get custom configuration
                service_port = port
                service_endpoint = endpoint
                service_auto_start = auto_start

                # Interactive prompts if not provided via CLI
                if not service_port and not service_endpoint:
                    config = await service_manager.get_service_configuration(service_name)
                    default_port = config.get_default_port() if config else ServiceConfiguration.create_default_config(service_name).get_default_port()

                    if Confirm.ask(f"Use default port {default_port} for {service_name.value}?", default=True):
                        service_port = default_port
                    else:
                        service_port = IntPrompt.ask(f"Enter port for {service_name.value}", default=default_port)

                if not service_auto_start:
                    service_auto_start = Confirm.ask(f"Enable auto-start for {service_name.value}?", default=False)

                setup_requests.append({
                    'service_name': service_name,
                    'custom_port': service_port,
                    'custom_endpoint': service_endpoint,
                    'auto_start': service_auto_start
                })

            # Perform setup with progress display
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console,
                transient=True
            ) as progress:
                task = progress.add_task("[cyan]Setting up services...", total=len(setup_requests))

                # Setup services (handles dependencies automatically)
                results = await service_manager.setup_multiple_services(setup_requests)

                progress.update(task, completed=len(setup_requests))

            # Display results
            console.print("\n[bold]Setup Results[/bold]\n")

            success_count = 0
            failure_count = 0

            for service_name, config in results.items():
                if config.is_healthy():
                    console.print(f"[green]✓[/green] {service_name.title()}: {config.status}")
                    if config.detected_version:
                        console.print(f"  Version: {config.detected_version}")
                    console.print(f"  Endpoint: {config.endpoint}")
                    if config.auto_start:
                        console.print(f"  Auto-start: [green]Enabled[/green]")
                    success_count += 1
                else:
                    console.print(f"[red]✗[/red] {service_name.title()}: {config.status}")
                    if config.error_message:
                        console.print(f"  Error: {config.error_message}")
                    failure_count += 1

                console.print()

            # Final summary
            if success_count == len(results):
                console.print(f"[green]✓ All {success_count} service(s) setup successfully![/green]")
            elif failure_count == len(results):
                console.print(f"[red]✗ All {failure_count} service(s) failed to setup[/red]")
            else:
                console.print(f"[yellow]Mixed results: {success_count} successful, {failure_count} failed[/yellow]")

            # Check for port conflicts and offer resolution
            conflicts = await service_manager.resolve_port_conflicts()
            if conflicts:
                console.print(f"\n[yellow]Resolved {len(conflicts)} port conflict(s):[/yellow]")
                for conflict in conflicts:
                    console.print(f"  - {conflict['service']}: Port changed from {conflict['old_port']} to {conflict['new_port']}")

        except ServiceConflictError as e:
            console.print(f"[red]✗ Service conflict: {e}[/red]")
            console.print("[yellow]Use --force to override conflicts or specify different ports[/yellow]")
            raise click.ClickException(str(e))

        except ServiceSetupError as e:
            console.print(f"[red]✗ Service setup failed: {e}[/red]")
            raise click.ClickException(str(e))

        except Exception as e:
            console.print(f"[red]✗ Unexpected error during service setup: {e}[/red]")
            raise click.ClickException(str(e))

    run_async(_setup_services())


@services_group.command('check')
@click.option('--service', '-s', help='Check specific service health')
@click.option('--fix', is_flag=True, help='Attempt to fix unhealthy services')
@click.option('--timeout', default=10, help='Timeout for health checks in seconds')
@click.pass_context
def check_services(ctx: click.Context, service: Optional[str], fix: bool, timeout: int):
    """Check health status of external services.

    Performs comprehensive health checks and optionally attempts to fix
    issues with unhealthy services.
    """
    async def _check_services():
        service_manager = ServiceConfigurationService(timeout=timeout)
        detection_service = ServiceDetectionService(timeout=timeout)

        try:
            console.print("[bold]Service Health Check[/bold]\n")

            # Get services to check
            if service:
                try:
                    service_name = ServiceName(service.lower())
                    services_to_check = [service_name]
                except ValueError:
                    available_services = [s.value for s in ServiceName]
                    console.print(f"[red]Invalid service '{service}'. Available services: {', '.join(available_services)}[/red]")
                    return
            else:
                services_to_check = list(ServiceName)

            # Perform health checks with progress
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("[cyan]Checking services...", total=len(services_to_check))

                health_results = {}

                for service_name in services_to_check:
                    progress.update(task, description=f"[cyan]Checking {service_name.value}...")

                    # Refresh service status
                    config = await service_manager.refresh_service_status(service_name)

                    # Perform detailed health check
                    is_healthy = await service_manager.check_service_health(service_name)

                    health_results[service_name] = {
                        'config': config,
                        'healthy': is_healthy
                    }

                    progress.advance(task)

            console.print()

            # Display health check results
            healthy_count = 0
            unhealthy_count = 0

            for service_name, result in health_results.items():
                config = result['config']
                is_healthy = result['healthy']

                if is_healthy:
                    console.print(f"[green]✓ {service_name.value.title()}[/green] - Healthy")
                    if config.detected_version:
                        console.print(f"  Version: {config.detected_version}")
                    console.print(f"  Status: {config.status}")
                    console.print(f"  Endpoint: {config.endpoint}")
                    healthy_count += 1
                else:
                    console.print(f"[red]✗ {service_name.value.title()}[/red] - Unhealthy")
                    console.print(f"  Status: {config.status}")
                    if config.error_message:
                        console.print(f"  Error: {config.error_message}")

                    # Suggest fixes
                    if config.status == ServiceStatusType.NOT_FOUND:
                        if service_name == ServiceName.DOCKER:
                            console.print("  [yellow]Fix:[/yellow] Install Docker Desktop or Docker Engine")
                        elif service_name == ServiceName.OLLAMA:
                            console.print("  [yellow]Fix:[/yellow] Install Ollama and run 'ollama serve'")
                        elif service_name == ServiceName.QDRANT:
                            console.print("  [yellow]Fix:[/yellow] Run 'docbro services setup --service qdrant'")

                    unhealthy_count += 1

                console.print()

            # Summary
            total_services = len(health_results)
            console.print(f"[bold]Health Check Summary[/bold]")
            console.print(f"Total services: {total_services}")
            console.print(f"[green]Healthy: {healthy_count}[/green]")
            console.print(f"[red]Unhealthy: {unhealthy_count}[/red]")

            # Attempt fixes if requested
            if fix and unhealthy_count > 0:
                console.print(f"\n[yellow]Attempting to fix {unhealthy_count} unhealthy service(s)...[/yellow]\n")

                fixed_count = 0
                for service_name, result in health_results.items():
                    if not result['healthy']:
                        console.print(f"[cyan]Attempting to fix {service_name.value}...[/cyan]")

                        try:
                            # Re-setup the service
                            config = await service_manager.setup_service(
                                service_name,
                                auto_start=result['config'].auto_start
                            )

                            if config.is_healthy():
                                console.print(f"[green]✓ Fixed {service_name.value}[/green]")
                                fixed_count += 1
                            else:
                                console.print(f"[red]✗ Could not fix {service_name.value}: {config.error_message}[/red]")

                        except Exception as e:
                            console.print(f"[red]✗ Error fixing {service_name.value}: {e}[/red]")

                console.print(f"\n[bold]Fix Summary: {fixed_count}/{unhealthy_count} services fixed[/bold]")

            # Exit with appropriate code
            if unhealthy_count > 0:
                raise click.ClickException(f"{unhealthy_count} service(s) are unhealthy")

        except Exception as e:
            if not isinstance(e, click.ClickException):
                console.print(f"[red]✗ Health check failed: {e}[/red]")
                raise click.ClickException(str(e))
            else:
                raise

    run_async(_check_services())


@services_group.command('reset')
@click.option('--service', '-s', help='Reset specific service configuration')
@click.option('--all', 'reset_all', is_flag=True, help='Reset all service configurations')
@click.option('--confirm', is_flag=True, help='Skip confirmation prompts')
@click.pass_context
def reset_services(ctx: click.Context, service: Optional[str], reset_all: bool, confirm: bool):
    """Reset service configurations to default state.

    Removes saved configurations and resets services to their default settings.
    This does not stop running services, only resets DocBro's configuration.
    """
    async def _reset_services():
        service_manager = ServiceConfigurationService()
        config_service = ConfigService()

        try:
            # Determine what to reset
            if service and reset_all:
                console.print("[red]Error: Cannot specify both --service and --all options[/red]")
                return

            if not service and not reset_all:
                console.print("[yellow]Please specify either --service <name> or --all[/yellow]")
                return

            # Get current configurations
            current_configs = await service_manager.get_all_configurations()

            if service:
                # Reset specific service
                try:
                    service_name = ServiceName(service.lower())
                except ValueError:
                    available_services = [s.value for s in ServiceName]
                    console.print(f"[red]Invalid service '{service}'. Available services: {', '.join(available_services)}[/red]")
                    return

                if service_name not in current_configs:
                    console.print(f"[yellow]Service '{service}' is not currently configured[/yellow]")
                    return

                services_to_reset = [service_name]
                reset_description = f"service '{service}'"

            else:
                # Reset all services
                if not current_configs:
                    console.print("[yellow]No service configurations found to reset[/yellow]")
                    return

                services_to_reset = list(current_configs.keys())
                reset_description = f"all {len(services_to_reset)} services"

            # Confirmation prompt
            if not confirm:
                console.print(f"[bold]Reset {reset_description}?[/bold]\n")

                for service_name in services_to_reset:
                    if service_name in current_configs:
                        config = current_configs[service_name]
                        console.print(f"[cyan]{service_name.value.title()}[/cyan]:")
                        console.print(f"  Status: {config.status}")
                        console.print(f"  Endpoint: {config.endpoint}")
                        console.print(f"  Auto-start: {'Yes' if config.auto_start else 'No'}")
                        console.print()

                console.print("[red]This will remove all saved configuration for these services.[/red]")
                console.print("[dim]Note: Running services will not be stopped, only DocBro's configuration will be reset.[/dim]\n")

                if not Confirm.ask(f"Are you sure you want to reset {reset_description}?", default=False):
                    console.print("[yellow]Reset cancelled.[/yellow]")
                    return

            # Perform reset
            console.print(f"[yellow]Resetting {reset_description}...[/yellow]\n")

            # Remove configurations from service manager
            for service_name in services_to_reset:
                # This would ideally be a method on the service manager
                # For now, we'll clear and reload
                pass

            # Clear saved configurations
            if reset_all:
                # Remove entire services config file
                services_config_path = config_service.services_config_path
                if services_config_path.exists():
                    services_config_path.unlink()
                    console.print("[yellow]Removed services configuration file[/yellow]")

                # Clear service manager state
                service_manager._service_configs.clear()
                service_manager._port_registry.clear()

            else:
                # Remove specific service from config
                try:
                    services_config = config_service.load_services_config()
                    services_config = [s for s in services_config if s.name != service_name.value]
                    config_service.save_services_config(services_config)

                    # Remove from service manager
                    if service_name in service_manager._service_configs:
                        config = service_manager._service_configs[service_name]
                        if config.port in service_manager._port_registry:
                            del service_manager._port_registry[config.port]
                        del service_manager._service_configs[service_name]

                except Exception as e:
                    console.print(f"[yellow]Warning: Could not update services config file: {e}[/yellow]")

            # Success message
            console.print(f"[green]✓ Successfully reset {reset_description}[/green]")
            console.print("[dim]Run 'docbro services setup' to reconfigure services[/dim]")

        except Exception as e:
            console.print(f"[red]✗ Failed to reset services: {e}[/red]")
            raise click.ClickException(str(e))

    run_async(_reset_services())


# Export the command group for integration with main CLI
def get_services_command_group():
    """Get the services command group for integration with main CLI."""
    return services_group