"""Wizard manager for interactive CLI operations."""

import click
from typing import Any, Optional, Dict, Callable, List
from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.table import Table

from src.models.wizard_state import WizardState, WizardType, WizardStep


class WizardManager:
    """Manages interactive wizard flows for CLI commands."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize wizard manager.

        Args:
            console: Rich console for output
        """
        self.console = console or Console()
        self.state: Optional[WizardState] = None
        self.validators: Dict[str, Callable] = {
            'url': self._validate_url,
            'project_name': self._validate_project_name,
            'depth': self._validate_depth,
            'model': self._validate_model,
            'port': self._validate_port,
        }

    def create_project_wizard(self) -> Dict[str, Any]:
        """Run the create project wizard.

        Returns:
            Dictionary of collected inputs
        """
        # Initialize wizard state
        self.state = WizardState(
            wizard_type=WizardType.CREATE_PROJECT,
            total_steps=4
        )

        # Define steps
        steps = [
            WizardStep(
                name="Project Name",
                prompt="Enter project name",
                field_name="name",
                required=True,
                validator="project_name",
                help_text="Unique name for your documentation project (letters, numbers, hyphens)"
            ),
            WizardStep(
                name="Documentation URL",
                prompt="Enter documentation URL",
                field_name="url",
                required=True,
                validator="url",
                help_text="URL of the documentation to crawl (e.g., https://docs.example.com)"
            ),
            WizardStep(
                name="Crawl Depth",
                prompt="Enter crawl depth",
                field_name="depth",
                required=False,
                default="2",
                validator="depth",
                help_text="How many levels deep to crawl (1-10, default: 2)"
            ),
            WizardStep(
                name="Embedding Model",
                prompt="Enter embedding model",
                field_name="model",
                required=False,
                default="mxbai-embed-large",
                validator="model",
                help_text="Model for generating embeddings (default: mxbai-embed-large)"
            ),
        ]

        for step in steps:
            self.state.add_step(step)

        # Show welcome
        self._show_welcome("Create Documentation Project")

        try:
            # Run through steps
            while not self.state.is_complete() and not self.state.cancelled:
                self._show_progress()

                current_step = self.state.get_current_step()
                if not current_step:
                    break

                value = self._prompt_for_input(current_step)

                if value is None:  # User cancelled
                    self.state.cancel()
                    break

                # Validate input
                if self._validate_input(current_step, value):
                    self.state.collect_input(value)
                    self.state.advance_step()
                else:
                    # Show error and retry
                    self._show_validation_errors()

            # Handle completion
            if self.state.is_complete():
                # Show summary and confirm
                if self._confirm_inputs():
                    return self.state.collected_inputs
                else:
                    self.state.cancel()

        except KeyboardInterrupt:
            self.state.cancel()
            self.console.print("\n[yellow]Wizard cancelled[/yellow]")

        return {}

    def _show_welcome(self, title: str) -> None:
        """Show welcome message.

        Args:
            title: Wizard title
        """
        panel = Panel.fit(
            f"[bold cyan]{title}[/bold cyan]\n\n"
            "Follow the prompts to complete the setup.\n"
            "Press Ctrl+C to cancel at any time.",
            border_style="cyan"
        )
        self.console.print(panel)
        self.console.print()

    def _show_progress(self) -> None:
        """Show current progress."""
        if not self.state:
            return

        progress_text = self.state.get_progress_text()
        progress_bar = "█" * int(self.state.get_progress() / 10) + "░" * (10 - int(self.state.get_progress() / 10))

        self.console.print(
            f"[cyan]{progress_text}[/cyan] {progress_bar} {self.state.get_progress():.0f}%\n"
        )

    def _prompt_for_input(self, step: WizardStep) -> Optional[str]:
        """Prompt user for input.

        Args:
            step: Current wizard step

        Returns:
            User input or None if cancelled
        """
        # Build prompt text
        prompt_text = f"[bold]{step.name}[/bold]"
        if step.help_text:
            self.console.print(f"[dim]{step.help_text}[/dim]")

        # Show default if available
        if step.default:
            prompt_text += f" [dim](default: {step.default})[/dim]"

        try:
            value = Prompt.ask(prompt_text, default=step.default if step.default else ...)

            if not value and step.required:
                self.console.print("[red]This field is required[/red]")
                return self._prompt_for_input(step)  # Retry

            return value

        except KeyboardInterrupt:
            return None

    def _validate_input(self, step: WizardStep, value: str) -> bool:
        """Validate user input.

        Args:
            step: Current step
            value: Input value

        Returns:
            True if valid
        """
        if not self.state:
            return False

        # Check required
        if step.required and not value:
            self.state.add_validation_error(f"{step.name} is required")
            return False

        # Run validator if specified
        if step.validator and step.validator in self.validators:
            validator = self.validators[step.validator]
            is_valid, error_message = validator(value)
            if not is_valid:
                self.state.add_validation_error(error_message)
                return False

        self.state.clear_validation_errors()
        return True

    def _show_validation_errors(self) -> None:
        """Show validation errors to user."""
        if not self.state or not self.state.validation_errors:
            return

        for error in self.state.validation_errors:
            self.console.print(f"[red]✗ {error}[/red]")

        self.state.clear_validation_errors()

    def _confirm_inputs(self) -> bool:
        """Show summary and confirm inputs.

        Returns:
            True if confirmed
        """
        if not self.state:
            return False

        # Create summary table
        table = Table(title="Review Your Settings", show_header=True)
        table.add_column("Setting", style="cyan")
        table.add_column("Value", style="green")

        for key, value in self.state.collected_inputs.items():
            # Make key more readable
            display_key = key.replace('_', ' ').title()
            table.add_row(display_key, str(value))

        self.console.print()
        self.console.print(table)
        self.console.print()

        return Confirm.ask("Create project with these settings?", default=True)

    # Validators

    def _validate_url(self, value: str) -> tuple[bool, str]:
        """Validate URL format.

        Args:
            value: URL to validate

        Returns:
            (is_valid, error_message)
        """
        if not value.startswith(('http://', 'https://')):
            return False, "URL must start with http:// or https://"

        # Basic URL validation
        from urllib.parse import urlparse
        try:
            result = urlparse(value)
            if not all([result.scheme, result.netloc]):
                return False, "Invalid URL format"
        except Exception:
            return False, "Invalid URL format"

        return True, ""

    def _validate_project_name(self, value: str) -> tuple[bool, str]:
        """Validate project name.

        Args:
            value: Project name to validate

        Returns:
            (is_valid, error_message)
        """
        import re
        if not re.match(r'^[a-zA-Z0-9_-]+$', value):
            return False, "Project name can only contain letters, numbers, hyphens, and underscores"

        if len(value) < 1 or len(value) > 50:
            return False, "Project name must be between 1 and 50 characters"

        return True, ""

    def _validate_depth(self, value: str) -> tuple[bool, str]:
        """Validate crawl depth.

        Args:
            value: Depth to validate

        Returns:
            (is_valid, error_message)
        """
        try:
            depth = int(value)
            if depth < 1 or depth > 10:
                return False, "Depth must be between 1 and 10"
        except ValueError:
            return False, "Depth must be a number"

        return True, ""

    def _validate_model(self, value: str) -> tuple[bool, str]:
        """Validate embedding model name.

        Args:
            value: Model name to validate

        Returns:
            (is_valid, error_message)
        """
        # For now, accept any non-empty model name
        if not value or len(value.strip()) == 0:
            return False, "Model name cannot be empty"

        return True, ""

    def _validate_port(self, value: str) -> tuple[bool, str]:
        """Validate port number.

        Args:
            value: Port to validate

        Returns:
            (is_valid, error_message)
        """
        try:
            port = int(value)
            if port < 1 or port > 65535:
                return False, "Port must be between 1 and 65535"
        except ValueError:
            return False, "Port must be a number"

        return True, ""

    def configure_service_wizard(self, service_name: str) -> Dict[str, Any]:
        """Run wizard to configure a service.

        Args:
            service_name: Name of service to configure

        Returns:
            Configuration dictionary
        """
        # Initialize wizard state
        self.state = WizardState(
            wizard_type=WizardType.CONFIGURE_SERVICE,
            total_steps=3  # Adjust based on service
        )

        # Service-specific steps would go here
        # For now, return empty dict
        return {}

    def get_state(self) -> Optional[WizardState]:
        """Get current wizard state.

        Returns:
            Current state or None
        """
        return self.state

    def reset(self) -> None:
        """Reset wizard state."""
        if self.state:
            self.state.reset()