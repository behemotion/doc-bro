"""Health check command for DocBro CLI."""

import asyncio
import json

import click
from rich.console import Console
from rich.table import Table

from src.version import __version__

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


@click.command(name="health")
@click.option("--json", "output_json", is_flag=True, help="Output in JSON format")
@click.option("--verbose", is_flag=True, help="Show detailed health information")
@click.pass_context
def health(ctx: click.Context, output_json: bool, verbose: bool):
    """Check health status of all DocBro services.

    This command performs a comprehensive health check of:
    - Required services (Python, UV, SQLite)
    - Optional services (Docker, Qdrant, Ollama)
    - System resources (memory, disk space)

    Examples:
      docbro health            # Basic health check
      docbro health --json     # Output as JSON
      docbro health --verbose  # Detailed diagnostics
    """
    async def _health_check():
        from src.services.detection import ServiceDetectionService

        console = Console()
        detection_service = ServiceDetectionService()

        try:
            # Check all services
            statuses = await detection_service.check_all_services()

            if output_json:
                health_data = {
                    "version": __version__,
                    "services": {},
                    "overall": "healthy"
                }
                for name, status in statuses.items():
                    health_data["services"][name] = {
                        "available": status.available,
                        "version": status.version,
                        "status": "healthy" if status.available else "unhealthy",
                        "error": status.error_message if not status.available else None
                    }
                    if not status.available and name in ['python', 'uv', 'sqlite']:
                        health_data["overall"] = "unhealthy"

                print(json.dumps(health_data, indent=2))
                return

            console.print(f"📊 DocBro Health Check (v{__version__})\n")

            # Create health table
            table = Table(title="Service Health Status", show_header=True, header_style="bold cyan")
            table.add_column("Service", style="cyan", no_wrap=True, width=20)
            table.add_column("Status", style="green", width=15)
            table.add_column("Version", style="yellow", width=15)
            if verbose:
                table.add_column("Details", style="dim")

            overall_healthy = True
            required_healthy = True
            optional_services = ['docker', 'qdrant', 'ollama']

            for name, status in statuses.items():
                # Determine status display
                if status.available:
                    status_text = "✅ Healthy"
                    status_style = "green"
                else:
                    status_text = "❌ Unhealthy"
                    status_style = "red"
                    if name not in optional_services:
                        required_healthy = False
                    overall_healthy = False

                # Format service name
                service_name = name.title().replace('_', ' ')
                if name in optional_services:
                    service_name = f"{service_name} [dim](optional)[/dim]"

                version_text = status.version or "unknown"

                if verbose:
                    details = status.error_message if not status.available else "Running normally"
                    if len(details) > 50:
                        details = details[:47] + "..."

                    table.add_row(
                        service_name,
                        f"[{status_style}]{status_text}[/{status_style}]",
                        version_text,
                        details
                    )
                else:
                    table.add_row(
                        service_name,
                        f"[{status_style}]{status_text}[/{status_style}]",
                        version_text
                    )

            console.print(table)

            # System resources check if verbose
            if verbose:
                console.print("\n[cyan]System Resources:[/cyan]")
                try:
                    import psutil

                    # Memory
                    mem = psutil.virtual_memory()
                    mem_gb = mem.available / (1024**3)
                    mem_status = "✅" if mem_gb >= 2 else "⚠️"
                    console.print(f"  {mem_status} Memory: {mem_gb:.1f} GB available ({mem.percent:.1f}% used)")

                    # Disk space
                    disk = psutil.disk_usage('/')
                    disk_gb = disk.free / (1024**3)
                    disk_status = "✅" if disk_gb >= 1 else "⚠️"
                    console.print(f"  {disk_status} Disk: {disk_gb:.1f} GB free ({disk.percent:.1f}% used)")

                    # CPU
                    cpu_count = psutil.cpu_count()
                    console.print(f"  ℹ️ CPU: {cpu_count} cores available")
                except ImportError:
                    console.print("  [dim]Install psutil for system resource information[/dim]")

            # Overall status
            console.print("")
            if required_healthy:
                if overall_healthy:
                    console.print("✅ [bold green]All services are healthy[/bold green]")
                    console.print("[dim]DocBro is fully operational[/dim]")
                else:
                    console.print("✅ [bold green]Required services are healthy[/bold green]")
                    console.print("⚠️  [yellow]Optional services unavailable (Qdrant/Ollama)[/yellow]")
                    console.print("💡 Run [cyan]docbro services setup[/cyan] to enable optional features")
            else:
                console.print("❌ [bold red]Critical services are unhealthy[/bold red]")
                console.print("💡 Run [cyan]docbro setup[/cyan] to fix installation issues")

            # Show next steps
            if not overall_healthy:
                console.print("\n[cyan]Next steps:[/cyan]")
                if 'docker' in statuses and not statuses['docker'].available:
                    console.print("  1. Install Docker for Qdrant support")
                if 'qdrant' in statuses and not statuses['qdrant'].available:
                    console.print("  2. Run [cyan]docbro services setup qdrant[/cyan]")
                if 'ollama' in statuses and not statuses['ollama'].available:
                    console.print("  3. Run [cyan]docbro services setup ollama[/cyan]")

        except Exception as e:
            console = Console()
            console.print(f"❌ Health check failed: {e}")
            raise click.ClickException(str(e))

    run_async(_health_check())