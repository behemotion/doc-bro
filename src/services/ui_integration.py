"""UI integration service for connecting InstallationWizardService to Rich UI components.

This service provides a polished interface layer that bridges the business logic
of the installation process with Rich UI components for enhanced user experience.
"""

import asyncio
import signal
import sys
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Dict, List, Optional, Any, Callable, AsyncGenerator
import logging

from rich.console import Console
from rich.progress import (
    Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn,
    TimeRemainingColumn, MofNCompleteColumn
)
from rich.prompt import Prompt, Confirm, IntPrompt
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.layout import Layout
from rich.live import Live
from rich.align import Align
from rich.columns import Columns
from rich.status import Status
from rich.markdown import Markdown

from .installation_wizard import InstallationWizardService, InstallationWizardError
from src.models.installation import (
    CriticalDecisionPoint, InstallationRequest, InstallationResponse,
    ServiceStatus
)
from src.models.installation_state import InstallationState
from src.models.system_requirements import SystemRequirements

logger = logging.getLogger(__name__)


class UIIntegrationService:
    """UI integration service for enhanced installation experience.

    This service connects the InstallationWizardService to Rich UI components,
    providing progress bars, status displays, user prompts, and real-time updates
    for a polished installation experience.
    """

    def __init__(self, console: Optional[Console] = None, interactive: bool = True):
        """Initialize UI integration service.

        Args:
            console: Rich console instance (creates new if None)
            interactive: Whether to run in interactive mode
        """
        self.console = console or Console()
        self.interactive = interactive
        self.wizard = InstallationWizardService()

        # UI state
        self.main_progress: Optional[Progress] = None
        self.phase_progress: Optional[Progress] = None
        self.current_layout: Optional[Layout] = None
        self.live_display: Optional[Live] = None
        self.cancelled = False

        # Progress tracking
        self.phase_task_id: Optional[int] = None
        self.step_task_id: Optional[int] = None

        # Set up the progress callback
        self.wizard.set_progress_callback(self._handle_progress_update)

        # Signal handlers for graceful cancellation
        self._setup_signal_handlers()

    def _setup_signal_handlers(self) -> None:
        """Setup signal handlers for graceful cancellation."""
        def signal_handler(signum, frame):
            self.cancelled = True
            if self.live_display:
                self.live_display.stop()
            self.console.print("\n[yellow]Installation cancelled by user.[/yellow]")
            sys.exit(0)

        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)

    @asynccontextmanager
    async def progress_context(self) -> AsyncGenerator[None, None]:
        """Context manager for progress display management."""
        if not self.interactive:
            yield
            return

        # Create layout for progress display
        self.current_layout = Layout()

        # Create main progress for phases
        self.main_progress = Progress(
            SpinnerColumn(),
            TextColumn("[bold blue]{task.description}"),
            BarColumn(),
            TaskProgressColumn(),
            TimeRemainingColumn(),
            console=self.console,
            expand=True
        )

        # Create secondary progress for steps within phases
        self.phase_progress = Progress(
            TextColumn("  ├─ {task.description}"),
            SpinnerColumn(),
            console=self.console,
            expand=True
        )

        # Setup layout
        self.current_layout.split_column(
            Layout(self._create_header(), size=3),
            Layout(self.main_progress, name="main_progress", size=3),
            Layout(self.phase_progress, name="phase_progress", size=3),
            Layout(self._create_status_panel(), name="status", size=5)
        )

        # Start live display
        self.live_display = Live(
            self.current_layout,
            console=self.console,
            refresh_per_second=4,
            transient=True
        )

        try:
            self.live_display.start()
            yield
        finally:
            if self.live_display:
                self.live_display.stop()
            self.main_progress = None
            self.phase_progress = None
            self.current_layout = None
            self.live_display = None

    def _create_header(self) -> Panel:
        """Create header panel for installation."""
        title = Text("DocBro Installation", style="bold cyan", justify="center")
        return Panel(title, style="blue", padding=(0, 1))

    def _create_status_panel(self) -> Panel:
        """Create status information panel."""
        if not self.wizard.installation_state:
            content = Text("Initializing installation...", style="dim")
        else:
            state = self.wizard.installation_state
            content = Text()
            content.append(f"Phase: {state.current_phase.replace('_', ' ').title()}\n", style="cyan")
            content.append(f"Step: {state.current_step}\n", style="white")
            content.append(f"Progress: {state.progress_percentage:.1f}%\n", style="green")

            if state.error_occurred:
                content.append(f"Error: {state.error_details or 'Unknown error'}", style="red")
            elif state.current_phase == "complete":
                content.append("Installation completed successfully!", style="green")

        return Panel(content, title="Status", style="dim", padding=(0, 1))

    def _handle_progress_update(self, progress_data: Dict[str, Any]) -> None:
        """Handle progress updates from the installation wizard.

        Args:
            progress_data: Progress information from installation wizard
        """
        if not self.main_progress or not self.phase_progress:
            return

        state = self.wizard.installation_state
        if not state:
            return

        # Update main progress (phases)
        if self.phase_task_id is None:
            self.phase_task_id = self.main_progress.add_task(
                "Starting installation...",
                total=state.total_phases
            )

        # Calculate phase index
        phase_order = ["initializing", "system_check", "service_setup", "configuration", "finalization", "complete"]
        current_phase_index = phase_order.index(state.current_phase) if state.current_phase in phase_order else 0

        phase_description = f"Phase {current_phase_index + 1}/{state.total_phases}: {state.current_phase.replace('_', ' ').title()}"
        self.main_progress.update(
            self.phase_task_id,
            description=phase_description,
            completed=current_phase_index,
            total=state.total_phases
        )

        # Update step progress
        if self.step_task_id is not None:
            self.phase_progress.remove_task(self.step_task_id)

        self.step_task_id = self.phase_progress.add_task(
            state.current_step,
            total=None  # Indeterminate progress for steps
        )

        # Update status panel in layout
        if self.current_layout:
            self.current_layout["status"].update(self._create_status_panel())

    async def start_installation_with_ui(self, request: InstallationRequest) -> InstallationResponse:
        """Start installation with full UI integration.

        Args:
            request: Installation request

        Returns:
            Installation response

        Raises:
            InstallationWizardError: If installation fails
        """
        if self.interactive:
            self.console.clear()
            self._show_welcome()

            if not Confirm.ask("Ready to begin installation?", default=True):
                self.console.print("[yellow]Installation cancelled.[/yellow]")
                raise InstallationWizardError("Installation cancelled by user")

        async with self.progress_context():
            try:
                # Start the installation
                response = await self.wizard.start_installation(request)

                if self.interactive:
                    self.console.print("[green]✓ Installation started successfully![/green]")

                    # Wait for installation to complete
                    await self._wait_for_completion()

                return response

            except KeyboardInterrupt:
                self.cancelled = True
                await self._handle_cancellation()
                raise InstallationWizardError("Installation cancelled by user")

    async def _wait_for_completion(self) -> None:
        """Wait for installation to complete with periodic updates."""
        while True:
            if self.cancelled:
                break

            state = self.wizard.installation_state
            if not state:
                break

            if state.current_phase in ["complete", "error"]:
                break

            # Small delay to avoid busy waiting
            await asyncio.sleep(0.5)

        # Show completion or error
        await self._show_final_status()

    async def _show_final_status(self) -> None:
        """Show final installation status."""
        state = self.wizard.installation_state
        if not state:
            return

        if state.current_phase == "complete":
            self._show_completion_success()
        elif state.current_phase == "error":
            self._show_completion_error(state.error_details)

    def _show_welcome(self) -> None:
        """Show welcome message."""
        welcome_content = """
# Welcome to DocBro Installation

DocBro is a documentation crawler and search tool with RAG capabilities.
This installer will guide you through the setup process.

**What will be installed:**
- DocBro command-line tool
- Configuration directories
- Service detection and setup

**Requirements:**
- Python 3.13+
- UV package manager
- Optional: Docker, Ollama, Qdrant

This installation will take approximately 2-3 minutes.
        """.strip()

        self.console.print(Panel(
            Markdown(welcome_content),
            title="DocBro Installer",
            style="blue",
            expand=False
        ))
        self.console.print()

    def _show_completion_success(self) -> None:
        """Show successful completion message."""
        success_content = """
# ✓ Installation Complete!

DocBro has been successfully installed and configured.

**Next Steps:**
1. Create your first project: `docbro create myproject --url https://docs.example.com`
2. Crawl documentation: `docbro crawl myproject`
3. Search your docs: `docbro search "query" --project myproject`

**Useful Commands:**
- Check status: `docbro status`
- List projects: `docbro list`
- Get help: `docbro --help`

For more information, visit the DocBro documentation.
        """.strip()

        self.console.print()
        self.console.print(Panel(
            Markdown(success_content),
            title="🎉 Installation Successful",
            style="green",
            expand=False
        ))

    def _show_completion_error(self, error_details: Optional[str] = None) -> None:
        """Show installation error message.

        Args:
            error_details: Optional error details
        """
        error_content = f"""
# ✗ Installation Failed

The installation encountered an error and could not complete.

**Error Details:**
{error_details or "No specific error details available."}

**Troubleshooting:**
1. Check system requirements (Python 3.13+, UV)
2. Ensure sufficient disk space and memory
3. Check network connectivity for service detection
4. Review logs for detailed error information

**Next Steps:**
- Run `docbro setup --force` to retry
- Check the documentation for troubleshooting tips
- Report issues on the project repository

You can also run installation in non-interactive mode: `docbro setup --non-interactive`
        """.strip()

        self.console.print()
        self.console.print(Panel(
            Markdown(error_content),
            title="❌ Installation Error",
            style="red",
            expand=False
        ))

    async def _handle_cancellation(self) -> None:
        """Handle installation cancellation."""
        if not self.interactive:
            return

        self.console.print("\n[yellow]Installation was cancelled.[/yellow]")

        if Confirm.ask("Would you like to save progress for later resume?", default=True):
            self.console.print("[dim]Progress has been saved. Run 'docbro setup' to resume.[/dim]")
        else:
            await self.wizard.rollback_installation()
            self.console.print("[dim]Installation state has been cleared.[/dim]")

    async def handle_critical_decisions(self, decisions: List[CriticalDecisionPoint]) -> Dict[str, Any]:
        """Handle critical decision points with interactive UI.

        Args:
            decisions: List of critical decisions requiring user input

        Returns:
            Dictionary mapping decision IDs to user choices
        """
        if not decisions:
            return {}

        choices = {}

        for decision in decisions:
            if self.cancelled:
                break

            choice = await self._prompt_for_decision(decision)
            choices[decision.decision_id] = choice
            decision.user_choice = choice
            decision.resolved = True

        return choices

    async def _prompt_for_decision(self, decision: CriticalDecisionPoint) -> Any:
        """Prompt user for a critical decision.

        Args:
            decision: Critical decision point

        Returns:
            User's choice
        """
        if not self.interactive:
            # Return default option in non-interactive mode
            return decision.default_option

        # Create decision display
        self.console.print()
        self.console.print(Panel(
            f"[bold]{decision.title}[/bold]\n\n{decision.description}",
            title="⚠️  Decision Required",
            style="yellow",
            expand=False
        ))

        # Show options
        table = Table(title="Available Options", show_header=True)
        table.add_column("Option", style="cyan", no_wrap=True)
        table.add_column("Description", style="white")
        table.add_column("Notes", style="dim")

        for i, option in enumerate(decision.options, 1):
            notes = []
            if option.get("recommended"):
                notes.append("[green]Recommended[/green]")
            if option.get("warning"):
                notes.append(f"[red]{option['warning']}[/red]")

            table.add_row(
                f"{i}. {option['id']}",
                option["label"],
                " • ".join(notes) if notes else ""
            )

        self.console.print(table)
        self.console.print()

        # Get user choice
        max_option = len(decision.options)

        while True:
            try:
                choice_num = IntPrompt.ask(
                    "Select an option",
                    default=self._get_default_option_number(decision),
                    show_default=True
                )

                if 1 <= choice_num <= max_option:
                    selected_option = decision.options[choice_num - 1]

                    # Handle custom input requirement
                    if selected_option.get("requires_input"):
                        custom_value = Prompt.ask(f"Enter custom {decision.decision_type}")

                        # Validate custom input if pattern provided
                        if decision.validation_pattern:
                            import re
                            if not re.match(decision.validation_pattern, custom_value):
                                self.console.print("[red]Invalid input format. Please try again.[/red]")
                                continue

                        return custom_value

                    return selected_option["id"]
                else:
                    self.console.print(f"[red]Please select a number between 1 and {max_option}.[/red]")

            except KeyboardInterrupt:
                self.cancelled = True
                return decision.default_option

    def _get_default_option_number(self, decision: CriticalDecisionPoint) -> int:
        """Get the default option number for a decision.

        Args:
            decision: Critical decision point

        Returns:
            Option number (1-based) for default option
        """
        if not decision.default_option:
            return 1

        for i, option in enumerate(decision.options, 1):
            if option["id"] == decision.default_option:
                return i

        return 1

    async def display_system_requirements(self, requirements: SystemRequirements) -> None:
        """Display system requirements validation with formatted table.

        Args:
            requirements: System requirements validation results
        """
        if not self.interactive:
            return

        self.console.print("\n[bold]System Requirements Validation[/bold]")

        # Create requirements table
        table = Table(title="System Requirements", show_header=True)
        table.add_column("Requirement", style="cyan")
        table.add_column("Current", style="white")
        table.add_column("Required", style="yellow")
        table.add_column("Status", style="bold")

        # Add requirement rows
        python_status = "✓ OK" if requirements.python_valid else "✗ Failed"
        table.add_row(
            "Python Version",
            requirements.python_version,
            "3.13.x",
            f"[green]{python_status}[/green]" if requirements.python_valid else f"[red]{python_status}[/red]"
        )

        memory_status = "✓ OK" if requirements.memory_valid else "✗ Insufficient"
        table.add_row(
            "Memory",
            f"{requirements.available_memory} GB",
            "4 GB",
            f"[green]{memory_status}[/green]" if requirements.memory_valid else f"[red]{memory_status}[/red]"
        )

        disk_status = "✓ OK" if requirements.disk_valid else "✗ Insufficient"
        table.add_row(
            "Disk Space",
            f"{requirements.available_disk} GB",
            "2 GB",
            f"[green]{disk_status}[/green]" if requirements.disk_valid else f"[red]{disk_status}[/red]"
        )

        platform_status = "✓ Supported" if requirements.platform_supported else "✗ Not supported"
        table.add_row(
            "Platform",
            requirements.platform,
            "darwin/linux/windows",
            f"[green]{platform_status}[/green]" if requirements.platform_supported else f"[red]{platform_status}[/red]"
        )

        uv_status = "✓ Available" if requirements.uv_available else "✗ Not found"
        uv_version = requirements.uv_version or "Not detected"
        table.add_row(
            "UV Package Manager",
            uv_version,
            "Any version",
            f"[green]{uv_status}[/green]" if requirements.uv_available else f"[red]{uv_status}[/red]"
        )

        self.console.print(table)

    def display_service_status(self, statuses: Dict[str, ServiceStatus]) -> None:
        """Display service configuration status with color-coded indicators.

        Args:
            statuses: Service status information
        """
        if not self.interactive:
            return

        self.console.print("\n[bold]External Services Status[/bold]")

        # Create service status table
        table = Table(title="Service Detection Results", show_header=True)
        table.add_column("Service", style="cyan")
        table.add_column("Status", style="bold")
        table.add_column("Version", style="white")
        table.add_column("Endpoint", style="dim")
        table.add_column("Notes", style="yellow")

        for name, status in statuses.items():
            if status.available:
                status_display = "[green]✓ Available[/green]"
                version_display = status.version or "Unknown"
                endpoint_display = status.endpoint or "Default"
                notes = ""
            else:
                status_display = "[red]✗ Not Available[/red]"
                version_display = "—"
                endpoint_display = "—"
                notes = status.error_message or "Service not found"

            table.add_row(
                name.title(),
                status_display,
                version_display,
                endpoint_display,
                notes
            )

        self.console.print(table)

        # Show summary
        available_count = sum(1 for status in statuses.values() if status.available)
        total_count = len(statuses)

        if available_count == total_count:
            summary_style = "green"
            summary_text = f"All {total_count} services are available!"
        else:
            summary_style = "yellow"
            summary_text = f"{available_count}/{total_count} services available. Missing services will be configured during setup."

        self.console.print(f"\n[{summary_style}]{summary_text}[/{summary_style}]")

    async def run_non_interactive_setup(self, request: InstallationRequest) -> InstallationResponse:
        """Run setup in non-interactive mode with minimal output.

        Args:
            request: Installation request

        Returns:
            Installation response
        """
        self.console.print("[cyan]Running DocBro installation in non-interactive mode...[/cyan]")

        with Status("[dim]Installing DocBro...", console=self.console, spinner="dots"):
            try:
                response = await self.wizard.start_installation(request)

                # Wait for completion
                while True:
                    state = self.wizard.installation_state
                    if not state or state.current_phase in ["complete", "error"]:
                        break
                    await asyncio.sleep(1)

                if state and state.current_phase == "complete":
                    self.console.print("[green]✓ DocBro installation completed successfully.[/green]")
                elif state and state.current_phase == "error":
                    error_msg = state.error_details or "Unknown error"
                    self.console.print(f"[red]✗ Installation failed: {error_msg}[/red]")
                    raise InstallationWizardError(f"Installation failed: {error_msg}")

                return response

            except Exception as e:
                self.console.print(f"[red]✗ Installation failed: {e}[/red]")
                raise

    async def resume_installation_with_ui(self) -> bool:
        """Resume interrupted installation with UI.

        Returns:
            True if installation was resumed, False otherwise
        """
        if not await self.wizard.resume_installation():
            return False

        if self.interactive:
            self.console.print("[yellow]Resuming interrupted installation...[/yellow]")

            async with self.progress_context():
                await self._wait_for_completion()
        else:
            with Status("[dim]Resuming installation...", console=self.console):
                await self._wait_for_completion()

        return True

    def show_installation_status(self) -> None:
        """Show current installation status."""
        status = self.wizard.get_installation_status()

        if status["status"] == "not_started":
            self.console.print("[dim]No installation in progress.[/dim]")
            return

        # Create status display
        table = Table(title="Installation Status", show_header=True)
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="white")

        table.add_row("Status", status.get("status", "Unknown"))
        table.add_row("Progress", f"{status.get('progress_percentage', 0):.1f}%")
        table.add_row("Current Phase", status.get("current_phase", "Unknown"))
        table.add_row("Message", status.get("message", "No message"))

        if "installation_id" in status:
            table.add_row("Installation ID", status["installation_id"])
            table.add_row("Method", status.get("install_method", "Unknown"))
            table.add_row("Version", status.get("version", "Unknown"))

        if "duration_seconds" in status:
            duration = status["duration_seconds"]
            table.add_row("Duration", f"{duration:.1f}s")

        self.console.print(table)

    # Integration helper methods for CLI commands

    @classmethod
    def create_for_interactive_setup(cls, console: Optional[Console] = None) -> "UIIntegrationService":
        """Create UI integration service configured for interactive setup.

        Args:
            console: Optional Rich console instance

        Returns:
            UIIntegrationService configured for interactive mode
        """
        return cls(console=console, interactive=True)

    @classmethod
    def create_for_noninteractive_setup(cls, console: Optional[Console] = None) -> "UIIntegrationService":
        """Create UI integration service configured for non-interactive setup.

        Args:
            console: Optional Rich console instance

        Returns:
            UIIntegrationService configured for non-interactive mode
        """
        return cls(console=console, interactive=False)

    async def run_setup_wizard(
        self,
        install_method: str = "uvx",
        version: str = "1.0.0",
        force: bool = False,
        skip_services: bool = False
    ) -> bool:
        """Run the setup wizard with UI integration.

        Args:
            install_method: Installation method to use
            version: Version to install
            force: Whether to force reinstall
            skip_services: Whether to skip service installation

        Returns:
            True if setup completed successfully, False otherwise
        """
        try:
            # Check if setup is already completed
            if not force:
                from .setup import SetupWizardService
                setup_wizard = SetupWizardService()
                if not setup_wizard.check_setup_required():
                    if self.interactive:
                        self.console.print("[yellow]DocBro is already set up![/yellow]")
                        if not Confirm.ask("Would you like to run setup again?", default=False):
                            return True
                    else:
                        self.console.print("[dim]Setup already completed. Use --force to re-run.[/dim]")
                        return True

            # Create installation request
            request = InstallationRequest(
                install_method=install_method,
                version=version,
                user_preferences={
                    "skip_services": skip_services,
                    "interactive": self.interactive
                }
            )

            # Start installation with UI
            if self.interactive:
                await self.start_installation_with_ui(request)
            else:
                await self.run_non_interactive_setup(request)

            return True

        except InstallationWizardError as e:
            if self.interactive:
                self.console.print(f"[red]Setup failed: {e}[/red]")
            else:
                self.console.print(f"[red]✗ Setup failed: {e}[/red]")
            return False
        except KeyboardInterrupt:
            if self.interactive:
                self.console.print("\n[yellow]Setup cancelled by user.[/yellow]")
            return False

    def check_and_resume_installation(self) -> Optional[bool]:
        """Check for interrupted installation and offer to resume.

        Returns:
            True if resumed successfully, False if failed, None if no resume needed
        """
        # Check if there's a resumable installation
        if not asyncio.run(self.wizard.load_installation_state()):
            return None

        if not self.interactive:
            # Auto-resume in non-interactive mode
            self.console.print("[dim]Resuming interrupted installation...[/dim]")
            return asyncio.run(self.resume_installation_with_ui())

        # Prompt user in interactive mode
        self.console.print("[yellow]Found interrupted installation.[/yellow]")
        if Confirm.ask("Would you like to resume where you left off?", default=True):
            return asyncio.run(self.resume_installation_with_ui())
        else:
            # Offer to start fresh
            if Confirm.ask("Start a fresh installation instead?", default=False):
                asyncio.run(self.wizard.rollback_installation())
                return None  # Indicate caller should start fresh
            return False

    async def handle_service_installation_decisions(self) -> Dict[str, Any]:
        """Handle service installation decisions during setup.

        Returns:
            Dictionary with service installation decisions
        """
        if not self.interactive:
            return {"skip_all": True}

        # Detect critical decisions for services
        try:
            from .detection import ServiceDetectionService
            detection_service = ServiceDetectionService()
            service_statuses = await detection_service.check_all_services()

            missing_services = [name for name, status in service_statuses.items() if not status.available]

            if not missing_services:
                self.console.print("[green]✓ All required services are available.[/green]")
                return {"skip_all": False, "install_services": []}

            # Display service status
            self.display_service_status(service_statuses)

            # Ask about missing services
            decisions = {}
            if Confirm.ask(f"Install missing services ({', '.join(missing_services)})?", default=True):
                decisions["install_services"] = missing_services
                decisions["skip_all"] = False

                # Show installation instructions for each missing service
                for service in missing_services:
                    self._show_service_help(service)

            else:
                decisions["skip_all"] = True
                decisions["install_services"] = []

            return decisions

        except Exception as e:
            logger.error(f"Error handling service decisions: {e}")
            return {"skip_all": True, "error": str(e)}

    def _show_service_help(self, service: str) -> None:
        """Show installation help for a specific service.

        Args:
            service: Service name to show help for
        """
        help_content = {
            "docker": """
**Docker Installation**

Docker is required for running Qdrant vector database.

**Installation:**
- macOS: Download Docker Desktop from https://docker.com/products/docker-desktop
- Ubuntu: `sudo apt install docker.io`
- Windows: Download Docker Desktop from https://docker.com/products/docker-desktop

After installation, start Docker and ensure it's running.
            """.strip(),

            "ollama": """
**Ollama Installation**

Ollama provides local AI embeddings for document search.

**Installation:**
- macOS/Linux: `curl -fsSL https://ollama.ai/install.sh | sh`
- Windows: Download from https://ollama.ai/download

After installation:
1. Start Ollama: `ollama serve`
2. Pull embedding model: `ollama pull mxbai-embed-large`
            """.strip(),

            "qdrant": """
**Qdrant Installation**

Qdrant is the vector database for storing document embeddings.

**Via Docker (recommended):**
`docker run -d -p 6333:6333 qdrant/qdrant`

**Alternative:**
Use the included docker-compose.yml:
`docker-compose -f docker/docker-compose.yml up -d`
            """.strip()
        }

        if service in help_content:
            self.console.print()
            self.console.print(Panel(
                Markdown(help_content[service]),
                title=f"{service.title()} Setup",
                style="blue",
                expand=False
            ))
            self.console.print()


# Example usage:
#
# # Interactive setup with UI
# async def run_interactive_setup():
#     ui_service = UIIntegrationService.create_for_interactive_setup()
#
#     # Check for interrupted installation first
#     resume_result = ui_service.check_and_resume_installation()
#     if resume_result is not None:
#         return resume_result
#
#     # Run new installation
#     return await ui_service.run_setup_wizard(
#         install_method="uvx",
#         version="1.0.0",
#         force=False,
#         skip_services=False
#     )
#
# # Non-interactive setup
# async def run_quiet_setup():
#     ui_service = UIIntegrationService.create_for_noninteractive_setup()
#     return await ui_service.run_setup_wizard(
#         install_method="uvx",
#         version="1.0.0",
#         skip_services=True
#     )
#
# # Manual installation with critical decisions
# async def run_custom_installation():
#     ui_service = UIIntegrationService.create_for_interactive_setup()
#
#     # Create custom installation request
#     request = InstallationRequest(
#         install_method="development",
#         version="1.0.0",
#         user_preferences={
#             "custom_install_path": "/opt/docbro",
#             "skip_services": False
#         }
#     )
#
#     # Start installation with full UI
#     response = await ui_service.start_installation_with_ui(request)
#
#     # Handle any critical decisions that arise
#     if ui_service.wizard.critical_decisions:
#         decisions = await ui_service.handle_critical_decisions(
#             ui_service.wizard.critical_decisions
#         )
#         print(f"User decisions: {decisions}")
#
#     return response