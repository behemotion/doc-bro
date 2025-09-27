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


def _get_sqlite_vec_install_guidance() -> str:
    """Get UV-specific guidance for installing sqlite-vec."""
    from src.services.sqlite_vec_service import detect_sqlite_vec

    available, message = detect_sqlite_vec()

    if not available and "compiled without extension support" in message:
        return (
            "SQLite extension support issue detected:\n"
            "  • Your Python's SQLite3 was compiled without extension support\n"
            "  • This is common on macOS with certain Python installations\n\n"
            "Recommended solution:\n"
            "  Use Qdrant instead: docbro init --vector-store qdrant --force\n\n"
            "Alternative solutions:\n"
            "  1. Install Python with Homebrew: brew install python@3.13\n"
            "  2. Use pyenv with correct build flags\n\n"
            "Qdrant provides better performance and reliability for vector operations."
        )
    else:
        return (
            "Install sqlite-vec using UV:\n"
            "  1. uv pip install --system sqlite-vec\n"
            "  2. Or reinstall docbro: uvx install --force git+https://github.com/behemotion/doc-bro"
        )


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
            await _run_setup_with_provider(setup_service, settings_service, detection_service, force, config, selected_provider, auto, no_prompt)
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

    # Check Docker availability for Qdrant
    from src.services.docker_manager import check_docker_availability
    docker_available, docker_message = check_docker_availability()

    # Show options with availability status
    options = []

    # SQLite-vec option
    status_icon = "[green]✓[/green]" if sqlite_vec_available else "[yellow]⚠[/yellow]"
    console.print(f"1. {status_icon} SQLite-vec (local, no external dependencies)")
    if not sqlite_vec_available:
        if "compiled without extension support" in sqlite_message:
            console.print(f"   [dim]{sqlite_message}[/dim]")
            console.print(f"   [yellow]Note:[/yellow] Your Python lacks SQLite extension support")
        else:
            console.print(f"   [dim]{sqlite_message}[/dim]")
    options.append((VectorStoreProvider.SQLITE_VEC, sqlite_vec_available))

    # Qdrant option
    qdrant_fully_available = qdrant_available and docker_available
    status_icon = "[green]✓[/green]" if qdrant_fully_available else "[yellow]⚠[/yellow]"

    # Add recommendation if SQLite has extension issues
    qdrant_description = "Qdrant (recommended for large deployments, requires Docker)"
    if not sqlite_vec_available and "compiled without extension support" in sqlite_message:
        qdrant_description = "Qdrant ([bold green]RECOMMENDED[/bold green] - better performance, requires Docker)"

    console.print(f"2. {status_icon} {qdrant_description}")
    if not docker_available:
        console.print(f"   [dim]Docker requirement: {docker_message}[/dim]")
    elif not qdrant_available:
        console.print("   [dim]Qdrant service not running[/dim]")
    options.append((VectorStoreProvider.QDRANT, qdrant_fully_available))

    console.print()

    while True:
        try:
            choice = click.prompt("Select option", type=int, default=1)
            if choice in [1, 2]:
                selected_provider, available = options[choice - 1]

                # Special handling for Qdrant selection
                if selected_provider == VectorStoreProvider.QDRANT:
                    if not docker_available:
                        console.print(f"\n[yellow]⚠[/yellow] Qdrant requires Docker and Docker Compose.")
                        console.print(f"   Issue: {docker_message}")
                        console.print("   Please install Docker from: https://docs.docker.com/get-docker/")

                        if not click.confirm("\nDo you want to continue anyway? (You'll need to install Docker later)", default=False):
                            continue
                    elif not qdrant_available:
                        console.print(f"\n[yellow]ℹ[/yellow] Qdrant service is not currently running.")
                        console.print("   DocBro can help you start Qdrant with Docker when needed.")

                        if not click.confirm("Continue with Qdrant setup?", default=True):
                            continue

                # For SQLite-vec, check if user wants to proceed despite missing dependency
                elif selected_provider == VectorStoreProvider.SQLITE_VEC and not available:
                    console.print(f"[yellow]⚠[/yellow] {sqlite_message}")
                    if not click.confirm("Do you want to proceed? (DocBro will attempt to install sqlite-vec automatically)", default=True):
                        continue

                return selected_provider
            else:
                console.print("[red]Please select 1 or 2[/red]")
        except click.Abort:
            raise UserCancellationError("User cancelled vector store selection")


async def _run_setup_with_provider(setup_service, settings_service, detection_service, force: bool, config: tuple, vector_store_provider: VectorStoreProvider, auto: bool = False, no_prompt: bool = False):
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
            error_msg = vector_setup_result["error"]
            progress.add_error(error_msg)

            # For Docker-related errors with Qdrant, provide helpful guidance
            if vector_store_provider == VectorStoreProvider.QDRANT and "Docker" in error_msg:
                setup_msg = vector_setup_result.get("setup_message", "")
                progress.add_error(f"Setup aborted: {setup_msg}")
                console.print(f"\n[red]✗[/red] Setup cannot continue without Docker for Qdrant.")
                console.print(f"[yellow]💡 Suggestion:[/yellow] Use SQLite-vec instead (no Docker required)")
                console.print(f"    or install Docker and run [cyan]docbro init --force[/cyan] again")
                raise SetupConfigurationError(f"Docker required for Qdrant: {setup_msg}")

            raise SetupConfigurationError(error_msg)

        progress.add_step(f"{vector_store_provider.value.title()} vector store", "✓")

        # Step 4: Check relevant services based on vector store selection
        progress.set_current("Detecting required services")
        await asyncio.sleep(0.3)

        # Only check services relevant to the selected vector store
        relevant_services = ['ollama']  # Always needed for embeddings
        if vector_store_provider == VectorStoreProvider.QDRANT:
            relevant_services.append('qdrant')

        # Check only relevant services
        service_checks = {}
        for service_name in relevant_services:
            if service_name == 'ollama':
                service_checks['ollama'] = await detection_service.check_ollama()
            elif service_name == 'qdrant':
                service_checks['qdrant'] = await detection_service.check_qdrant()

        for name, status in service_checks.items():
            progress.update_service(
                name.replace("_", " ").title(),
                status.available,
                status.version
            )
            if not status.available:
                if name == 'ollama':
                    progress.add_warning(f"{name.title()} not available - embeddings will not work")
                elif name == 'qdrant' and vector_store_provider == VectorStoreProvider.QDRANT:
                    progress.add_warning(f"{name.title()} not available - vector storage will not work")

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

        # Step 6: Finalize setup
        progress.set_current("Finalizing setup")
        await asyncio.sleep(0.3)

        # Create and save a minimal setup configuration to mark as completed
        from src.models.setup_configuration import SetupConfiguration
        from src.models.setup_types import SetupMode, VectorStorageConfig, EmbeddingModelConfig
        from src.version import __version__

        # Prepare vector storage config based on provider
        vector_storage_config = None
        if vector_store_provider == VectorStoreProvider.SQLITE_VEC:
            vector_storage_config = VectorStorageConfig(
                provider="sqlite_vec",
                connection_url="sqlite:///" + str(get_docbro_data_dir() / "projects"),
                data_path=get_docbro_data_dir() / "projects"
            )
        elif vector_store_provider == VectorStoreProvider.QDRANT:
            vector_storage_config = VectorStorageConfig(
                provider="qdrant",
                connection_url="http://localhost:6333",
                data_path=get_docbro_data_dir() / "qdrant"
            )

        # Prepare embedding model config if Ollama is available
        embedding_model_config = None
        if service_checks.get('ollama', type('', (), {'available': False})).available:
            embedding_model_config = EmbeddingModelConfig(
                model_name="mxbai-embed-large",
                download_required=False
            )

        setup_config = SetupConfiguration(
            setup_mode=SetupMode.AUTO if auto or no_prompt else SetupMode.INTERACTIVE,
            version=__version__,
            vector_storage=vector_storage_config,
            embedding_model=embedding_model_config,
        )

        # Mark as completed and save
        setup_config.mark_as_completed()
        await setup_service.config_service.save_configuration(setup_config)

        progress.add_step("Setup finalized", "✓")

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
            progress.set_current("Installing SQLite-vec extension")

            # Attempt automatic installation
            try:
                import subprocess
                import sys
                import shutil

                # Use UV for package management - this app is UV-dependent
                # Use --system flag to install into the current environment (UVX isolated env)
                install_cmd = ["uv", "pip", "install", "--system", "sqlite-vec"]

                # Verify UV is available and supports --system flag
                try:
                    test_result = subprocess.run(
                        ["uv", "pip", "install", "--help"],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    if test_result.returncode != 0:
                        progress.add_warning("UV not available - DocBro requires UV package manager")
                        return {
                            "success": False,
                            "error": "UV package manager not available",
                            "setup_message": "DocBro requires UV. Install UV from: https://docs.astral.sh/uv/"
                        }

                    # Check if --system flag is supported
                    if "--system" not in test_result.stdout:
                        progress.add_warning("UV version too old - --system flag not supported")
                        return {
                            "success": False,
                            "error": "UV version incompatible",
                            "setup_message": "Update UV to a newer version: pip install --upgrade uv"
                        }

                except (subprocess.TimeoutExpired, FileNotFoundError):
                    progress.add_warning("UV not found - DocBro requires UV package manager")
                    return {
                        "success": False,
                        "error": "UV package manager not found",
                        "setup_message": "DocBro requires UV. Install UV from: https://docs.astral.sh/uv/"
                    }

                # Run the installation command
                result = subprocess.run(
                    install_cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )

                if result.returncode == 0:
                    progress.add_step("SQLite-vec installation (uv pip)", "✓")

                    # Verify installation
                    available, message = detect_sqlite_vec()
                    if not available:
                        if "compiled without extension support" in message:
                            progress.add_warning("SQLite extension support unavailable - Python SQLite3 lacks extension loading")
                            progress.add_warning("RECOMMENDATION: Use Qdrant instead for better performance")
                            return {
                                "success": True,
                                "warning": "SQLite extension support unavailable",
                                "setup_message": (
                                    "Your Python installation lacks SQLite extension support.\n"
                                    "Consider using Qdrant instead: docbro init --vector-store qdrant --force\n"
                                    "Qdrant offers better performance and doesn't require SQLite extensions."
                                )
                            }
                        else:
                            progress.add_warning(f"SQLite-vec installed but still not working: {message}")
                            return {
                                "success": True,
                                "warning": "SQLite-vec installed but verification failed",
                                "setup_message": message
                            }
                else:
                    stderr_output = result.stderr.strip() if result.stderr else "Unknown error"
                    progress.add_warning(f"Failed to install SQLite-vec: {stderr_output}")

                    return {
                        "success": True,
                        "warning": "SQLite-vec automatic installation failed",
                        "setup_message": _get_sqlite_vec_install_guidance()
                    }
            except subprocess.TimeoutExpired:
                progress.add_warning("SQLite-vec installation timed out")
                return {
                    "success": True,
                    "warning": "SQLite-vec installation timed out",
                    "setup_message": _get_sqlite_vec_install_guidance()
                }
            except Exception as e:
                progress.add_warning(f"Failed to install SQLite-vec: {e}")
                return {
                    "success": True,
                    "warning": "SQLite-vec automatic installation failed",
                    "setup_message": _get_sqlite_vec_install_guidance()
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

        # Test SQLite-vec service initialization
        service = SQLiteVecService(test_config)
        await service.initialize()

        # Test basic vector operations to ensure extensions work properly
        try:
            # Create a test vector collection
            test_embedding = [0.1, 0.2, 0.3, 0.4, 0.5]  # Simple test vector

            # Try to add and search vectors to verify functionality
            await service.add_embeddings("test_collection", [("test_doc", test_embedding, {"test": "metadata"})])

            # Try to search
            results = await service.search("test_collection", test_embedding, limit=1)

            if results and len(results) > 0:
                progress.add_step("SQLite-vec vector operations test", "✓")
            else:
                progress.add_warning("SQLite-vec installed but vector operations failed")

            # Clean up test collection
            try:
                await service.delete_collection("test_collection")
            except:
                pass  # Ignore cleanup errors

        except Exception as e:
            progress.add_warning(f"SQLite-vec vector operations test failed: {e}")

        progress.add_step("SQLite-vec service test", "✓")
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
        # First check Docker availability
        from src.services.docker_manager import check_docker_availability
        docker_available, docker_message = check_docker_availability()

        if not docker_available:
            progress.add_warning(f"Docker not available: {docker_message}")
            return {
                "success": False,
                "error": "Docker is required for Qdrant",
                "setup_message": f"{docker_message}\nInstall Docker from: https://docs.docker.com/get-docker/"
            }

        progress.add_step("Docker availability check", "✓")

        # Check if Qdrant is available
        from src.services.detection import ServiceDetectionService
        detection = ServiceDetectionService()
        qdrant_status = await detection.check_qdrant()

        if not qdrant_status.available:
            progress.add_warning("Qdrant service not running - attempting to start container")

            # Try to start Qdrant container using subprocess (no Docker Python package needed)
            from src.services.docker_manager import run_qdrant_container
            try:
                container_success, container_message = await run_qdrant_container()
                if container_success:
                    progress.add_step("Qdrant container started", "✓")

                    # Wait a moment for Qdrant to fully start
                    await asyncio.sleep(3)

                    # Re-check Qdrant availability
                    qdrant_status = await detection.check_qdrant()
                    if qdrant_status.available:
                        progress.add_step("Qdrant service ready", "✓")
                    else:
                        progress.add_warning("Qdrant container started but service not yet ready")
                        return {
                            "success": True,
                            "warning": "Qdrant starting up",
                            "setup_message": "Qdrant container started but may need a few more seconds to be ready"
                        }
                else:
                    progress.add_warning(f"Failed to start Qdrant container: {container_message}")
                    return {
                        "success": True,
                        "warning": "Could not start Qdrant automatically",
                        "setup_message": f"Manual start needed: docker run -d -p 6333:6333 --name docbro-qdrant qdrant/qdrant\nError: {container_message}"
                    }
            except Exception as e:
                progress.add_warning(f"Error starting Qdrant container: {e}")
                return {
                    "success": True,
                    "warning": "Could not start Qdrant automatically",
                    "setup_message": "Start Qdrant manually with: docker run -d -p 6333:6333 --name docbro-qdrant qdrant/qdrant"
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
    await _run_setup_with_provider(setup_service, settings_service, detection_service, force, config, vector_store_provider, auto=False, no_prompt=False)


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