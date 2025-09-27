"""Initialize DocBro system - unified setup command with box interface."""

import asyncio
import logging
import sys
import time
from typing import Optional, Dict, Any
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.live import Live
import json

from src.services.settings_service import SettingsService
from src.models.settings import GlobalSettings
from src.lib.paths import get_docbro_config_dir, get_docbro_data_dir, get_docbro_cache_dir
from src.models.setup_types import (
    SetupConfigurationError,
    ExternalDependencyError,
    UserCancellationError
)
from src.services.setup_logic_service import SetupLogicService
from src.services.detection import ServiceDetectionService
from src.lib.utils import run_async, async_command
from src.services.sqlite_vec_service import detect_sqlite_vec
from src.models.vector_store_types import VectorStoreProvider

console = Console()
logger = logging.getLogger(__name__)


class InitProgressDisplay:
    """Progress display for initialization with box interface."""

    def __init__(self):
        self.console = Console()
        self.steps_completed = []
        self.current_step = ""
        self.warnings = []
        self.errors = []
        self.service_status = {}
        self.live = None

    def start(self):
        """Start the live display."""
        self.live = Live(self._get_display(), console=self.console, refresh_per_second=2)
        self.live.start()

    def stop(self):
        """Stop the live display."""
        if self.live:
            self.live.stop()

    def add_step(self, step: str, status: str = "✓"):
        """Add a completed step."""
        self.steps_completed.append((step, status))
        self.update()

    def set_current(self, step: str):
        """Set current step being processed."""
        self.current_step = step
        self.update()

    def add_warning(self, warning: str):
        """Add a warning message."""
        self.warnings.append(warning)
        self.update()

    def add_error(self, error: str):
        """Add an error message."""
        self.errors.append(error)
        self.update()

    def update_service(self, name: str, available: bool, version: str = None):
        """Update service status."""
        self.service_status[name] = {
            'available': available,
            'version': version
        }
        self.update()

    def update(self):
        """Update the display."""
        if self.live:
            self.live.update(self._get_display())

    def _get_display(self) -> Panel:
        """Generate the display panel."""
        table = Table(show_header=False, box=None, padding=0)
        table.add_column(style="cyan", width=25)
        table.add_column(style="white")

        # Show completed steps
        for step, status in self.steps_completed:
            table.add_row(f"[green]{status}[/green] {step}", "")

        # Show current step
        if self.current_step:
            table.add_row(f"[yellow]⟳[/yellow] {self.current_step}", "[dim]in progress...[/dim]")

        # Add separator if we have services
        if self.service_status:
            table.add_row("", "")
            table.add_row("[bold]Services:[/bold]", "")

            for name, status in self.service_status.items():
                icon = "[green]✓[/green]" if status['available'] else "[red]✗[/red]"
                version_str = f" (v{status['version']})" if status.get('version') else ""
                table.add_row(f"  {icon} {name}", f"{'Available' if status['available'] else 'Not available'}{version_str}")

        # Add warnings
        if self.warnings:
            table.add_row("", "")
            table.add_row("[yellow]⚠ Warnings:[/yellow]", "")
            for warning in self.warnings:
                table.add_row("", f"[yellow]{warning}[/yellow]")

        # Add errors
        if self.errors:
            table.add_row("", "")
            table.add_row("[red]✗ Errors:[/red]", "")
            for error in self.errors:
                table.add_row("", f"[red]{error}[/red]")

        return Panel(
            table,
            title="[bold cyan]DocBro Initialization[/bold cyan]",
            border_style="cyan"
        )

    def __enter__(self):
        """Context manager entry."""
        self.start()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.stop()


@click.command()
@click.option('--auto', is_flag=True, help='Automatic setup with defaults')
@click.option('--force', is_flag=True, help='Force re-run setup even if completed')
@click.option('--status', is_flag=True, help='Show current setup status')
@click.option('--verbose', '-v', is_flag=True, help='Enable verbose output')
@click.option('--json', 'output_json', is_flag=True, help='Output status in JSON format')
@click.option('--no-prompt', is_flag=True, help='Skip all interactive prompts (use defaults)')
@click.option('--config', multiple=True, help='Initial configuration key=value pairs')
@click.option('--vector-store', type=click.Choice(['qdrant', 'sqlite_vec']), help='Vector store backend to use')
@click.option('--sqlite-vec-path', type=click.Path(), help='Custom path for SQLite-vec databases')
@async_command
async def init(auto: bool, force: bool, status: bool, verbose: bool, output_json: bool, no_prompt: bool, config: tuple, vector_store: str, sqlite_vec_path: str):
    """Initialize DocBro system with all required components.

    This command handles:
    • System requirements validation
    • Service configuration (Docker, Qdrant, Ollama)
    • Global settings initialization
    • Directory structure creation

    Examples:
      docbro init                    # Interactive setup
      docbro init --auto             # Automatic with defaults
      docbro init --status           # Check setup status
      docbro init --config key=val   # Set initial configs
    """

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        logging.getLogger().setLevel(logging.WARNING)

    setup_service = SetupLogicService()
    settings_service = SettingsService()
    detection_service = ServiceDetectionService()

    try:
        # Handle status check
        if status:
            return await _handle_status(setup_service, output_json)

        # Check if already initialized
        if not force:
            setup_status = await setup_service.get_setup_status()
            if setup_status["setup_completed"] and settings_service.global_settings_path.exists():
                console.print(Panel(
                    f"[green]✓[/green] DocBro is already initialized\n\n"
                    f"Last setup: {setup_status['last_setup_time']}\n"
                    f"Settings: {settings_service.global_settings_path}\n\n"
                    f"Use [cyan]--force[/cyan] to re-initialize\n"
                    f"Use [cyan]docbro setup[/cyan] to modify settings",
                    title="[bold green]Already Initialized[/bold green]",
                    border_style="green"
                ))
                return

        # Run initialization with progress display
        if auto or no_prompt:
            # Use specified vector store or default
            selected_provider = VectorStoreProvider.from_string(vector_store) if vector_store else VectorStoreProvider.SQLITE_VEC
            await _run_setup_with_provider(setup_service, settings_service, detection_service, force, config, selected_provider)
        else:
            await _run_interactive_init(setup_service, settings_service, detection_service, force, config)

    except UserCancellationError as e:
        console.print(f"\n[yellow]⚠[/yellow] Initialization cancelled: {e}")
        sys.exit(4)
    except SetupConfigurationError as e:
        console.print(f"\n[red]✗[/red] Configuration error: {e}")
        sys.exit(2)
    except ExternalDependencyError as e:
        console.print(f"\n[red]✗[/red] Dependency error: {e}")
        _show_dependency_help(str(e))
        sys.exit(3)
    except Exception as e:
        console.print(f"\n[red]✗[/red] Initialization failed: {e}")
        if verbose:
            logger.exception("Init failed with exception")
        sys.exit(1)


async def _prompt_vector_store_selection(detection_service) -> VectorStoreProvider:
    """Prompt user to select vector store provider."""

    console.print("\n[bold cyan]Vector Database Selection[/bold cyan]")
    console.print("Choose your vector database backend:\n")

    # Check service availability
    service_checks = await detection_service.check_all_services()
    qdrant_available = service_checks.get('qdrant', type('', (), {'available': False})).available
    sqlite_vec_available, sqlite_message = detect_sqlite_vec()

    # Show options with availability status
    options = []

    # SQLite-vec option
    status_icon = "[green]✓[/green]" if sqlite_vec_available else "[yellow]⚠[/yellow]"
    console.print(f"1. {status_icon} SQLite-vec (local, no external dependencies)")
    if not sqlite_vec_available:
        console.print(f"   [dim]{sqlite_message}[/dim]")
    options.append((VectorStoreProvider.SQLITE_VEC, sqlite_vec_available))

    # Qdrant option
    status_icon = "[green]✓[/green]" if qdrant_available else "[yellow]⚠[/yellow]"
    console.print(f"2. {status_icon} Qdrant (recommended for large deployments)")
    if not qdrant_available:
        console.print("   [dim]Qdrant service not running[/dim]")
    options.append((VectorStoreProvider.QDRANT, qdrant_available))

    console.print()

    while True:
        try:
            choice = click.prompt("Select option", type=int, default=1)
            if choice in [1, 2]:
                selected_provider, available = options[choice - 1]

                if not available:
                    console.print(f"[yellow]⚠[/yellow] {selected_provider.value} is not currently available.")
                    if click.confirm("Do you want to proceed anyway and set it up later?", default=False):
                        return selected_provider
                    continue

                return selected_provider
            else:
                console.print("[red]Please select 1 or 2[/red]")
        except click.Abort:
            raise UserCancellationError("User cancelled vector store selection")


async def _run_setup_with_provider(setup_service, settings_service, detection_service, force: bool, config: tuple, vector_store_provider: VectorStoreProvider):
    """Run initialization with progress display and selected vector store provider."""

    with InitProgressDisplay() as progress:
        # Step 1: Check system requirements
        progress.set_current("Checking system requirements")
        await asyncio.sleep(0.5)  # Brief pause for visibility

        try:
            requirements = await setup_service.check_system_requirements()
            if requirements['meets_requirements']:
                progress.add_step("System requirements", "✓")
            else:
                for issue in requirements.get('issues', []):
                    progress.add_error(issue)
                raise SetupConfigurationError("System requirements not met")
        except Exception as e:
            progress.add_error(str(e))
            raise

        # Step 2: Create directories
        progress.set_current("Creating directory structure")
        await asyncio.sleep(0.3)

        for dir_path in [get_docbro_config_dir(), get_docbro_data_dir(), get_docbro_cache_dir()]:
            dir_path.mkdir(parents=True, exist_ok=True)
        progress.add_step("Directory structure", "✓")

        # Step 3: Setup vector store
        progress.set_current(f"Setting up {vector_store_provider.value} vector store")
        await asyncio.sleep(0.3)

        vector_setup_result = await _setup_vector_store(vector_store_provider, progress)
        if not vector_setup_result["success"]:
            progress.add_error(vector_setup_result["error"])
            raise SetupConfigurationError(vector_setup_result["error"])

        progress.add_step(f"{vector_store_provider.value.title()} vector store", "✓")

        # Step 4: Check other services
        progress.set_current("Detecting additional services")
        await asyncio.sleep(0.3)

        service_checks = await detection_service.check_all_services()

        for name, status in service_checks.items():
            progress.update_service(
                name.replace("_", " ").title(),
                status.available,
                status.version
            )
            if not status.available and name in ['ollama']:
                progress.add_warning(f"{name.title()} not available - some features may be limited")

        progress.add_step("Service detection", "✓")

        # Step 5: Initialize settings
        progress.set_current("Initializing global settings")
        await asyncio.sleep(0.3)

        # Backup existing if force mode
        if force and settings_service.global_settings_path.exists():
            backup_path = settings_service.reset_to_factory_defaults(backup=True)
            if backup_path:
                progress.add_step(f"Backed up existing to {backup_path.name}", "↻")

        # Create settings with config overrides and selected vector store
        settings = GlobalSettings(vector_store_provider=vector_store_provider)
        if config:
            for item in config:
                if '=' in item:
                    key, value = item.split('=', 1)
                    if hasattr(settings, key):
                        try:
                            # Type conversion
                            if key in ['crawl_depth', 'chunk_size', 'rag_top_k', 'max_retries', 'timeout']:
                                setattr(settings, key, int(value))
                            elif key in ['rag_temperature', 'rate_limit']:
                                setattr(settings, key, float(value))
                            else:
                                setattr(settings, key, value)
                        except ValueError as e:
                            progress.add_warning(f"Invalid value for {key}: {e}")

        settings_service.save_global_settings(settings)
        progress.add_step("Global settings", "✓")

        # Step 6: Run setup service initialization
        progress.set_current("Completing system setup")
        await asyncio.sleep(0.3)

        result = await setup_service.run_automated_setup(force=force)
        if result["success"]:
            progress.add_step("System setup", "✓")
            if result.get("warnings"):
                for warning in result["warnings"]:
                    progress.add_warning(warning)
        else:
            progress.add_error(result.get('error', 'Setup failed'))
            raise SetupConfigurationError(result.get('error', 'Setup failed'))

    # Show final success message
    console.print("\n")
    console.print(Panel(
        f"[green]✓[/green] DocBro initialization complete!\n\n"
        f"Vector Store: {VectorStoreProvider.get_display_name(vector_store_provider)}\n"
        f"Settings: {settings_service.global_settings_path}\n"
        f"Data: {get_docbro_data_dir()}\n\n"
        f"Next steps:\n"
        f"  • Run [cyan]docbro setup[/cyan] to modify settings\n"
        f"  • Run [cyan]docbro create <name> --url <url>[/cyan] to add a project\n"
        f"  • Run [cyan]docbro serve[/cyan] to start the MCP server",
        title="[bold green]Initialization Complete[/bold green]",
        border_style="green"
    ))


async def _setup_vector_store(provider: VectorStoreProvider, progress: InitProgressDisplay) -> Dict[str, Any]:
    """Setup the selected vector store provider."""

    if provider == VectorStoreProvider.SQLITE_VEC:
        return await _setup_sqlite_vec(progress)
    elif provider == VectorStoreProvider.QDRANT:
        return await _setup_qdrant(progress)
    else:
        return {"success": False, "error": f"Unknown vector store provider: {provider}"}


async def _setup_sqlite_vec(progress: InitProgressDisplay) -> Dict[str, Any]:
    """Setup SQLite-vec vector store."""

    try:
        # Check if sqlite-vec is available
        available, message = detect_sqlite_vec()

        if not available:
            progress.add_warning("SQLite-vec not available - will need to install: pip install sqlite-vec")
            return {
                "success": True,
                "warning": "SQLite-vec extension not found, installation required",
                "setup_message": "Run 'pip install sqlite-vec' to complete setup"
            }

        # Test basic functionality
        import tempfile
        import os
        from src.services.sqlite_vec_service import SQLiteVecService
        from src.core.config import DocBroConfig

        # Create a test config
        test_config = DocBroConfig(
            data_dir=str(get_docbro_data_dir()),
            qdrant_url="http://localhost:6333",
            ollama_url="http://localhost:11434"
        )

        # Test SQLite-vec service
        service = SQLiteVecService(test_config)
        await service.initialize()

        progress.add_step("SQLite-vec test", "✓")
        return {
            "success": True,
            "message": "SQLite-vec configured successfully",
            "provider": "sqlite_vec"
        }

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to setup SQLite-vec: {str(e)}"
        }


async def _setup_qdrant(progress: InitProgressDisplay) -> Dict[str, Any]:
    """Setup Qdrant vector store."""

    try:
        # Check if Qdrant is available
        from src.services.detection import ServiceDetectionService
        detection = ServiceDetectionService()
        qdrant_status = await detection.check_qdrant()

        if not qdrant_status.available:
            progress.add_warning("Qdrant service not available - will need to start Qdrant server")
            return {
                "success": True,
                "warning": "Qdrant service not running",
                "setup_message": "Run 'docker run -p 6333:6333 qdrant/qdrant' to start Qdrant"
            }

        # Test basic connectivity
        import httpx
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:6333/health")
            if response.status_code == 200:
                progress.add_step("Qdrant connectivity test", "✓")
                return {
                    "success": True,
                    "message": "Qdrant configured successfully",
                    "provider": "qdrant"
                }
            else:
                raise Exception(f"Qdrant health check failed: {response.status_code}")

    except Exception as e:
        return {
            "success": False,
            "error": f"Failed to setup Qdrant: {str(e)}"
        }


async def _run_interactive_init(setup_service, settings_service, detection_service, force: bool, config: tuple):
    """Run interactive initialization."""

    # Show welcome message
    console.print(Panel(
        "Welcome to DocBro initialization!\n\n"
        "This wizard will help you:\n"
        "  • Validate system requirements\n"
        "  • Choose vector database backend\n"
        "  • Configure external services\n"
        "  • Set up global settings\n"
        "  • Create necessary directories\n\n"
        "Press [cyan]Ctrl+C[/cyan] at any time to cancel",
        title="[bold cyan]DocBro Setup Wizard[/bold cyan]",
        border_style="cyan"
    ))

    if not click.confirm("\nProceed with initialization?", default=True):
        raise UserCancellationError("User cancelled")

    # Let user choose vector store provider
    vector_store_provider = await _prompt_vector_store_selection(detection_service)

    # Run the setup with selected provider
    await _run_setup_with_provider(setup_service, settings_service, detection_service, force, config, vector_store_provider)


async def _handle_status(setup_service: SetupLogicService, output_json: bool) -> None:
    """Handle status command with box interface."""
    status = await setup_service.get_setup_status()

    if output_json:
        print(json.dumps(status, indent=2))
        return

    # Create status table
    table = Table(show_header=False, box=None, padding=0)
    table.add_column(style="cyan", width=20)
    table.add_column(style="white")

    # Setup status
    if status["setup_completed"]:
        table.add_row("Setup:", f"[green]✓ Complete[/green]")
        table.add_row("Last setup:", status['last_setup_time'])
        table.add_row("Mode:", status.get('setup_mode', 'unknown'))
    else:
        table.add_row("Setup:", "[red]✗ Not completed[/red]")

    table.add_row("", "")  # Separator

    # Component status
    table.add_row("[bold]Components:[/bold]", "")

    components_status = status.get("components_status", {})
    for comp_name, comp_info in components_status.items():
        if isinstance(comp_info, list):  # MCP clients
            for client in comp_info:
                icon = "[green]✓[/green]" if client["available"] else "[red]✗[/red]"
                version = f" (v{client['version']})" if client.get('version') else ""
                table.add_row(
                    f"  {icon} MCP/{client['name']}",
                    f"{client['status']}{version}"
                )
        else:
            icon = "[green]✓[/green]" if comp_info["available"] else "[red]✗[/red]"
            version = f" (v{comp_info['version']})" if comp_info.get('version') else ""
            table.add_row(
                f"  {icon} {comp_name.replace('_', ' ').title()}",
                f"{comp_info['status']}{version}"
            )

    # Settings status
    settings_service = SettingsService()
    if settings_service.global_settings_path.exists():
        table.add_row("", "")
        table.add_row("[bold]Settings:[/bold]", "")
        table.add_row("  Global config:", f"[green]✓[/green] {settings_service.global_settings_path}")

        # Count projects with settings
        project_count = 0
        if settings_service.global_settings_path.parent.exists():
            project_dirs = [d for d in settings_service.global_settings_path.parent.iterdir() if d.is_dir() and d.name.startswith("project_")]
            project_count = len(project_dirs)

        if project_count > 0:
            table.add_row("  Project configs:", f"{project_count} projects")
    else:
        table.add_row("", "")
        table.add_row("[bold]Settings:[/bold]", "[yellow]Not initialized[/yellow]")

    console.print(Panel(
        table,
        title="[bold cyan]DocBro Status[/bold cyan]",
        border_style="cyan"
    ))


def _show_dependency_help(error_msg: str):
    """Show helpful suggestions for dependency errors."""
    console.print("\n[yellow]💡 Suggestions:[/yellow]")

    if "docker" in error_msg.lower():
        console.print("  • Install Docker: https://docs.docker.com/get-docker/")
        console.print("  • Start Docker service: [cyan]docker --version[/cyan] to verify")

    if "ollama" in error_msg.lower():
        console.print("  • Install Ollama: https://ollama.ai/")
        console.print("  • Start Ollama: [cyan]ollama serve[/cyan]")
        console.print("  • Pull embedding model: [cyan]ollama pull mxbai-embed-large[/cyan]")

    if "qdrant" in error_msg.lower():
        console.print("  • Run with Docker: [cyan]docker run -p 6333:6333 qdrant/qdrant[/cyan]")
        console.print("  • Or install locally: https://qdrant.tech/documentation/quick-start/")