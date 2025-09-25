"""Setup wizard service for first-run configuration."""

import asyncio
import subprocess
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import logging

import click
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table
from rich.text import Text

from .config import ConfigService
from .detection import ServiceDetectionService
from src.models.installation import (
    InstallationContext, ServiceStatus, SetupWizardState, PackageMetadata
)

logger = logging.getLogger(__name__)
console = Console()


class SetupError(Exception):
    """Base exception for setup-related errors."""
    pass


class ServiceInstallationError(SetupError):
    """Service installation failed."""
    pass


class SetupWizardService:
    """Interactive setup wizard for first-run configuration."""

    def __init__(self):
        """Initialize setup wizard service."""
        self.config_service = ConfigService()
        self.detection_service = ServiceDetectionService()
        self.state: Optional[SetupWizardState] = None

    def create_wizard_state(self) -> SetupWizardState:
        """Create new setup wizard state."""
        self.state = SetupWizardState(
            current_step="welcome",
            setup_start_time=datetime.now()
        )
        return self.state

    def load_wizard_state(self) -> Optional[SetupWizardState]:
        """Load existing setup wizard state if available."""
        wizard_path = self.config_service.config_dir / "wizard.json"
        if not wizard_path.exists():
            return None

        try:
            with open(wizard_path, 'r') as f:
                import json
                data = json.load(f)
                if 'setup_start_time' in data:
                    data['setup_start_time'] = datetime.fromisoformat(data['setup_start_time'])
                return SetupWizardState.model_validate(data)
        except Exception as e:
            logger.warning(f"Failed to load wizard state: {e}")
            return None

    def save_wizard_state(self, state: SetupWizardState) -> None:
        """Save setup wizard state to disk."""
        self.config_service.ensure_directories()
        wizard_path = self.config_service.config_dir / "wizard.json"

        try:
            with open(wizard_path, 'w') as f:
                import json
                json.dump(state.model_dump(mode='json'), f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save wizard state: {e}")

    def clear_wizard_state(self) -> None:
        """Remove wizard state file after completion."""
        wizard_path = self.config_service.config_dir / "wizard.json"
        if wizard_path.exists():
            wizard_path.unlink()

    async def run_interactive_setup(self) -> InstallationContext:
        """Run the complete interactive setup process."""
        console.clear()

        # Load or create wizard state
        self.state = self.load_wizard_state()
        if self.state is None:
            self.state = self.create_wizard_state()

        try:
            # Step 1: Welcome
            if "welcome" not in self.state.completed_steps:
                self._show_welcome()
                self.state.completed_steps.append("welcome")
                self.state.current_step = "python_check"
                self.save_wizard_state(self.state)

            # Step 2: Python version check
            if "python_check" not in self.state.completed_steps:
                self._check_python_version()
                self.state.completed_steps.append("python_check")
                self.state.current_step = "service_check"
                self.save_wizard_state(self.state)

            # Step 3: Service detection
            if "service_check" not in self.state.completed_steps:
                service_statuses = await self._detect_services()
                self.state.completed_steps.append("service_check")
                self.state.current_step = "service_install"
                self.save_wizard_state(self.state)
            else:
                # Re-detect services
                service_statuses = await self._detect_services()

            # Step 4: Service installation (if needed)
            if "service_install" not in self.state.completed_steps:
                await self._handle_service_installation(service_statuses)
                self.state.completed_steps.append("service_install")
                self.state.current_step = "config_setup"
                self.save_wizard_state(self.state)

            # Step 5: Configuration setup
            if "config_setup" not in self.state.completed_steps:
                context = self._create_installation_context()
                self.state.completed_steps.append("config_setup")
                self.state.current_step = "complete"
                self.save_wizard_state(self.state)
            else:
                context = self._create_installation_context()

            # Step 6: Complete
            self._show_completion(context)
            self.state.completed_steps.append("complete")

            # Clean up wizard state
            self.clear_wizard_state()

            return context

        except KeyboardInterrupt:
            console.print("\n[yellow]Setup interrupted. Progress has been saved.[/yellow]")
            console.print("Run [bold]docbro setup[/bold] again to continue.")
            raise click.Abort()
        except Exception as e:
            logger.error(f"Setup failed: {e}")
            console.print(f"[red]Setup failed: {e}[/red]")
            raise SetupError(f"Setup wizard failed: {e}")

    def _show_welcome(self) -> None:
        """Display welcome message and introduction."""
        welcome_text = """
[bold blue]Welcome to DocBro![/bold blue]

DocBro is a documentation crawler and search tool with RAG capabilities.
This setup wizard will help you configure DocBro for first use.

[dim]This will take about 2-3 minutes to complete.[/dim]
        """

        console.print(Panel(welcome_text.strip(), title="Setup Wizard", expand=False))
        console.print()

        if not Confirm.ask("Ready to begin setup?", default=True):
            raise click.Abort()

    def _check_python_version(self) -> None:
        """Verify Python version meets requirements."""
        import sys

        version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        console.print(f"[dim]Checking Python version: {version}[/dim]")

        if not version.startswith("3.13."):
            console.print(f"[red]✗ Python 3.13.x required, found {version}[/red]")
            console.print("\nPlease install Python 3.13.x and try again.")
            console.print("Visit: https://python.org/downloads/")
            raise SetupError(f"Unsupported Python version: {version}")

        console.print(f"[green]✓ Python version OK: {version}[/green]")

    async def _detect_services(self) -> Dict[str, ServiceStatus]:
        """Detect external service availability."""
        console.print("\n[bold]Detecting external services...[/bold]")

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Checking services...", total=None)

            statuses = await self.detection_service.check_all_services()

        # Display results in a table
        table = Table(title="Service Status")
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Version", style="dim")
        table.add_column("Notes", style="yellow")

        for name, status in statuses.items():
            if status.available:
                status_text = "[green]✓ Available[/green]"
                version_text = status.version or "unknown"
                notes = ""
            else:
                status_text = "[red]✗ Not available[/red]"
                version_text = "—"
                notes = status.error_message or ""

            table.add_row(name.title(), status_text, version_text, notes)

        console.print()
        console.print(table)

        return statuses

    async def _handle_service_installation(self, statuses: Dict[str, ServiceStatus]) -> None:
        """Handle installation of missing services."""
        missing_services = [name for name, status in statuses.items() if not status.available]

        if not missing_services:
            console.print("\n[green]✓ All services are available![/green]")
            return

        console.print(f"\n[yellow]Missing services: {', '.join(missing_services)}[/yellow]")

        if not Confirm.ask("Would you like help installing missing services?", default=True):
            console.print("[dim]Skipping service installation. You can install them later.[/dim]")
            self.state.skip_services = missing_services
            return

        # Provide installation guidance
        for service in missing_services:
            self._show_service_installation_help(service)

        # Ask if they want to continue
        console.print("\n[dim]After installing services, they will be detected automatically.[/dim]")
        if Confirm.ask("Continue setup without waiting?", default=True):
            self.state.skip_services = missing_services
        else:
            # Re-detect services
            console.print("Re-checking services...")
            updated_statuses = await self._detect_services()
            still_missing = [name for name, status in updated_statuses.items() if not status.available]
            if still_missing:
                console.print(f"[yellow]Still missing: {', '.join(still_missing)}[/yellow]")
                self.state.skip_services = still_missing

    def _show_service_installation_help(self, service: str) -> None:
        """Show installation instructions for a specific service."""
        instructions = {
            "docker": {
                "title": "Docker Installation",
                "content": """
Docker is required for running Qdrant and Redis services.

[bold]Installation:[/bold]
• macOS: Download Docker Desktop from https://docker.com/products/docker-desktop
• Ubuntu: sudo apt install docker.io
• Windows: Download Docker Desktop from https://docker.com/products/docker-desktop

After installation, start Docker and ensure it's running.
                """.strip()
            },
            "ollama": {
                "title": "Ollama Installation",
                "content": """
Ollama provides local AI embeddings for document search.

[bold]Installation:[/bold]
• macOS/Linux: curl -fsSL https://ollama.ai/install.sh | sh
• Windows: Download from https://ollama.ai/download

After installation, start Ollama and pull the embedding model:
• ollama serve
• ollama pull mxbai-embed-large
                """.strip()
            },
            "redis": {
                "title": "Redis Installation",
                "content": """
Redis is used for caching and task queues.

[bold]Via Docker (recommended):[/bold]
• docker run -d -p 6379:6379 redis:7-alpine

[bold]Native installation:[/bold]
• macOS: brew install redis
• Ubuntu: sudo apt install redis-server
• Windows: Use Docker or WSL
                """.strip()
            },
            "qdrant": {
                "title": "Qdrant Installation",
                "content": """
Qdrant is the vector database for storing document embeddings.

[bold]Via Docker (recommended):[/bold]
• docker run -d -p 6333:6333 qdrant/qdrant

[bold]Alternative:[/bold]
• Use the included docker-compose.yml:
• docker-compose -f docker/docker-compose.yml up -d
                """.strip()
            }
        }

        if service in instructions:
            info = instructions[service]
            console.print()
            console.print(Panel(info["content"], title=info["title"], expand=False))

    def _create_installation_context(self) -> InstallationContext:
        """Create and save installation context."""
        console.print("\n[bold]Setting up configuration...[/bold]")

        # Detect installation details
        install_path = shutil.which("docbro")
        if install_path:
            install_path = Path(install_path)
            # Check if it's a uvx installation
            if ".local" in str(install_path) and "pipx" not in str(install_path):
                install_method = "uvx"
            else:
                install_method = "manual"
        else:
            install_path = Path("./docbro")  # Development mode
            install_method = "development"

        # Get Python version
        import sys
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

        # Try to get UV version
        uv_version = None
        try:
            result = subprocess.run(["uv", "--version"], capture_output=True, text=True)
            if result.returncode == 0:
                uv_version = result.stdout.strip().split()[-1]  # Extract version from "uv 0.x.x"
        except FileNotFoundError:
            pass

        # Create context
        context = self.config_service.create_installation_context(
            install_method=install_method,
            version="1.0.0",
            python_version=python_version,
            uv_version=uv_version,
            install_path=install_path,
            is_global=(install_method != "development")
        )

        console.print(f"[green]✓ Configuration saved to {self.config_service.config_dir}[/green]")

        return context

    def _show_completion(self, context: InstallationContext) -> None:
        """Show setup completion message."""
        completion_text = f"""
[bold green]✓ Setup Complete![/bold green]

DocBro has been successfully configured:

[dim]Installation Method:[/dim] {context.install_method}
[dim]Install Path:[/dim] {context.install_path}
[dim]Config Directory:[/dim] {context.config_dir}
[dim]Data Directory:[/dim] {context.user_data_dir}

[bold]Next Steps:[/bold]
1. Create your first project: [cyan]docbro create myproject --url https://docs.example.com[/cyan]
2. Crawl documentation: [cyan]docbro crawl myproject[/cyan]
3. Search your docs: [cyan]docbro search "query" --project myproject[/cyan]

[bold]Need help?[/bold]
• Check status: [cyan]docbro status[/cyan]
• List projects: [cyan]docbro list[/cyan]
• Get help: [cyan]docbro --help[/cyan]

[dim]If you skipped service installation, you can set them up later.
DocBro will guide you through the process when needed.[/dim]
        """

        console.print()
        console.print(Panel(completion_text.strip(), title="🎉 Welcome to DocBro!", expand=False))

    def check_setup_required(self) -> bool:
        """Check if setup wizard needs to run."""
        context = self.config_service.load_installation_context()
        return context is None

    def get_setup_status(self) -> Dict[str, any]:
        """Get current setup status for display."""
        context = self.config_service.load_installation_context()
        wizard_state = self.load_wizard_state()

        if context is None:
            return {
                "setup_completed": False,
                "setup_required": True,
                "in_progress": wizard_state is not None,
                "current_step": wizard_state.current_step if wizard_state else None
            }

        return {
            "setup_completed": True,
            "setup_required": False,
            "in_progress": False,
            "install_method": context.install_method,
            "install_date": context.install_date.isoformat(),
            "version": context.version,
            "config_dir": str(context.config_dir),
            "data_dir": str(context.user_data_dir)
        }