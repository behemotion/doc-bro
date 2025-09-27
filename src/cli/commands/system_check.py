"""System requirements validation CLI module.

This module provides a CLI command for validating system requirements independently
of the installation wizard. It uses SystemRequirementsService for validation and
displays results in a formatted table with helpful suggestions.
"""

import asyncio
import json
import sys
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text

from src.services.system_validator import SystemRequirementsService
from src.models.system_requirements import SystemRequirements


class SystemCheckCLI:
    """CLI interface for system requirements checking."""

    def __init__(self):
        """Initialize the system check CLI."""
        self.console = Console()
        self.service = SystemRequirementsService()

    async def run_system_check(self, json_output: bool = False, verbose: bool = False) -> int:
        """Run system requirements validation.

        Args:
            json_output: Output results in JSON format
            verbose: Show detailed information

        Returns:
            int: Exit code (0 for success, 1 for failure)
        """
        try:
            # Run validation
            requirements = await self.service.validate_system_requirements()

            if json_output:
                self._output_json(requirements, verbose)
            else:
                self._output_table(requirements, verbose)

            # Return appropriate exit code
            return 0 if requirements.is_system_ready() else 1

        except Exception as e:
            if json_output:
                error_data = {
                    "error": str(e),
                    "system_ready": False,
                    "validation_failed": True
                }
                click.echo(json.dumps(error_data, indent=2))
            else:
                self.console.print(f"[red]✗ System check failed: {e}[/red]")
            return 1

    def _output_table(self, requirements: SystemRequirements, verbose: bool) -> None:
        """Output requirements in formatted table.

        Args:
            requirements: System requirements validation results
            verbose: Show detailed information
        """
        # Main status panel
        overall_status = requirements.is_system_ready()
        status_text = "[green]✓ READY[/green]" if overall_status else "[red]✗ NOT READY[/red]"

        panel_content = Text()
        panel_content.append("System Requirements Status: ")
        if overall_status:
            panel_content.append("✓ READY", style="bold green")
        else:
            panel_content.append("✗ NOT READY", style="bold red")

        self.console.print(Panel(
            panel_content,
            title="DocBro System Check",
            border_style="green" if overall_status else "red"
        ))

        # Requirements table
        table = Table(title="System Requirements Validation")
        table.add_column("Requirement", style="cyan", width=20)
        table.add_column("Current", style="blue", width=20)
        table.add_column("Required", style="dim", width=15)
        table.add_column("Status", justify="center", width=10)
        if verbose:
            table.add_column("Details", style="dim", width=40)

        # Python version row
        python_status = "[green]✓[/green]" if requirements.python_valid else "[red]✗[/red]"
        python_row = [
            "Python Version",
            requirements.python_version,
            "≥ 3.13.0",
            python_status
        ]
        if verbose:
            if requirements.python_valid:
                python_row.append("Compatible Python version")
            else:
                python_row.append("Python 3.13+ is required for DocBro")
        table.add_row(*python_row)

        # Memory row
        memory_status = "[green]✓[/green]" if requirements.memory_valid else "[red]✗[/red]"
        memory_row = [
            "Available Memory",
            f"{requirements.available_memory} GB",
            "≥ 4 GB",
            memory_status
        ]
        if verbose:
            if requirements.memory_valid:
                memory_row.append("Sufficient memory for operation")
            else:
                memory_row.append("More memory needed for embeddings and vector operations")
        table.add_row(*memory_row)

        # Disk space row
        disk_status = "[green]✓[/green]" if requirements.disk_valid else "[red]✗[/red]"
        disk_row = [
            "Disk Space",
            f"{requirements.available_disk} GB",
            "≥ 2 GB",
            disk_status
        ]
        if verbose:
            if requirements.disk_valid:
                disk_row.append("Adequate storage for data and cache")
            else:
                disk_row.append("Additional storage required for databases and vector indices")
        table.add_row(*disk_row)

        # Platform row
        platform_status = "[green]✓[/green]" if requirements.platform_supported else "[red]✗[/red]"
        platform_row = [
            "Platform",
            requirements.platform,
            "darwin/linux/windows",
            platform_status
        ]
        if verbose:
            if requirements.platform_supported:
                platform_row.append("Supported operating system")
            else:
                platform_row.append("Unsupported platform - limited functionality")
        table.add_row(*platform_row)

        # UV availability row
        uv_status = "[green]✓[/green]" if requirements.uv_available else "[yellow]⚠[/yellow]"
        uv_current = requirements.uv_version or "Not available"
        uv_row = [
            "UV Package Manager",
            uv_current,
            "Recommended",
            uv_status
        ]
        if verbose:
            if requirements.uv_available:
                uv_row.append("Fast Python package management available")
            else:
                uv_row.append("Optional but recommended for better performance")
        table.add_row(*uv_row)

        self.console.print()
        self.console.print(table)

        # Show missing requirements if any
        if not overall_status:
            self.console.print()
            missing = requirements.get_missing_requirements()
            self.console.print("[bold red]Missing Requirements:[/bold red]")
            for requirement in missing:
                self.console.print(f"  • {requirement}")

            # Helpful suggestions
            self.console.print()
            self._show_suggestions(requirements)

        # Show next steps
        self.console.print()
        if overall_status:
            self.console.print("[green]✓ Your system meets all requirements for DocBro![/green]")
            self.console.print("Run [bold]docbro setup[/bold] to install and configure DocBro.")
        else:
            self.console.print("[yellow]⚠ Address the missing requirements above, then run this check again.[/yellow]")

    def _show_suggestions(self, requirements: SystemRequirements) -> None:
        """Show helpful suggestions for failed requirements.

        Args:
            requirements: System requirements validation results
        """
        suggestions = []

        if not requirements.python_valid:
            suggestions.append(
                "Python 3.13+: Install from https://python.org or use pyenv/conda"
            )

        if not requirements.memory_valid:
            suggestions.append(
                f"Memory: Close applications to free up memory (need {4 - requirements.available_memory} GB more)"
            )

        if not requirements.disk_valid:
            suggestions.append(
                f"Disk Space: Free up storage space (need {2 - requirements.available_disk} GB more)"
            )

        if not requirements.platform_supported:
            suggestions.append(
                f"Platform: Consider using a supported OS (darwin/linux/windows), "
                f"current platform '{requirements.platform}' may have limited support"
            )

        if not requirements.uv_available:
            suggestions.append(
                "UV (Optional): Install with 'curl -LsSf https://astral.sh/uv/install.sh | sh' for better performance"
            )

        if suggestions:
            self.console.print("[bold yellow]Suggestions:[/bold yellow]")
            for suggestion in suggestions:
                self.console.print(f"  • {suggestion}")

    def _output_json(self, requirements: SystemRequirements, verbose: bool) -> None:
        """Output requirements in JSON format.

        Args:
            requirements: System requirements validation results
            verbose: Show detailed information
        """
        # Get summary from service
        summary = self.service.get_requirements_summary(requirements)

        # Add additional metadata for JSON output
        output_data = {
            "system_ready": summary["system_ready"],
            "requirements": {
                "python": summary["python"],
                "memory": summary["memory"],
                "disk": summary["disk"],
                "platform": summary["platform"],
                "uv": summary["uv"]
            },
            "missing_requirements": summary["missing_requirements"]
        }

        if verbose:
            # Add detailed information in verbose mode
            output_data["details"] = {
                "suggestions": self._get_suggestions_list(requirements),
                "next_steps": self._get_next_steps(requirements.is_system_ready())
            }

        click.echo(json.dumps(output_data, indent=2))

    def _get_suggestions_list(self, requirements: SystemRequirements) -> list[str]:
        """Get suggestions as a list for JSON output.

        Args:
            requirements: System requirements validation results

        Returns:
            list[str]: List of suggestions
        """
        suggestions = []

        if not requirements.python_valid:
            suggestions.append("Install Python 3.13+ from https://python.org or use pyenv/conda")

        if not requirements.memory_valid:
            suggestions.append(f"Free up memory: need {4 - requirements.available_memory} GB more")

        if not requirements.disk_valid:
            suggestions.append(f"Free up disk space: need {2 - requirements.available_disk} GB more")

        if not requirements.platform_supported:
            suggestions.append(f"Use supported OS (current: {requirements.platform})")

        if not requirements.uv_available:
            suggestions.append("Install UV with: curl -LsSf https://astral.sh/uv/install.sh | sh")

        return suggestions

    def _get_next_steps(self, system_ready: bool) -> list[str]:
        """Get next steps as a list for JSON output.

        Args:
            system_ready: Whether system meets all requirements

        Returns:
            list[str]: List of next steps
        """
        if system_ready:
            return ["Run 'docbro setup' to install and configure DocBro"]
        else:
            return [
                "Address the missing requirements listed above",
                "Run 'docbro system-check' again to verify",
                "Once ready, run 'docbro setup' to install DocBro"
            ]


# Click command definition
@click.command("system-check")
@click.option(
    "--json",
    "json_output",
    is_flag=True,
    help="Output results in JSON format for machine-readable parsing"
)
@click.option(
    "--verbose",
    "-v",
    is_flag=True,
    help="Show detailed information and suggestions"
)
@click.pass_context
def system_check(ctx: click.Context, json_output: bool, verbose: bool):
    """Check system requirements for DocBro installation.

    Validates your system against DocBro's requirements including Python version,
    memory, disk space, platform support, and optional dependencies like UV.

    This command can be run independently to verify system compatibility
    before installing DocBro.

    Examples:

        # Basic system check
        docbro system-check

        # Verbose output with suggestions
        docbro system-check --verbose

        # JSON output for scripts
        docbro system-check --json
    """
    async def _run_check():
        cli = SystemCheckCLI()
        exit_code = await cli.run_system_check(json_output=json_output, verbose=verbose)
        sys.exit(exit_code)

    # Handle asyncio event loop
    try:
        # Try to get existing event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # If loop is already running, create a new task
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(asyncio.run, _run_check())
                future.result()
        else:
            # Run in existing loop
            loop.run_until_complete(_run_check())
    except RuntimeError:
        # No event loop exists, create new one
        asyncio.run(_run_check())


if __name__ == "__main__":
    system_check()