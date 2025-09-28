"""UV tool post-install hook for DocBro.

This module provides post-install functionality that is automatically triggered
after UV tool installation (`uv tool install`). It detects
first-time installations and launches the interactive installation wizard.

UV Integration:
- Follows UV's standard post-install hook conventions
- Handles UV environment variables and paths
- Supports both UV tool and development installations
- Integrates with InstallationWizardService for setup workflow

Usage:
    This hook is automatically executed by UV after package installation.
    Manual execution for testing:
        python -m src.cli.post_install
"""

import asyncio
import logging
import os
import sys
from pathlib import Path
from typing import Dict, Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from src.services.config import ConfigService
from src.services.installation_wizard import InstallationWizardService
from src.models.installation import InstallationRequest
from src.core.lib_logger import setup_logging, get_component_logger

# Initialize components
console = Console()


class PostInstallError(Exception):
    """Base exception for post-install hook errors."""
    pass


class UVPostInstallHook:
    """UV tool post-install hook manager.

    This class handles the post-installation workflow triggered by UV after
    tool installation. It detects installation context, validates environment,
    and launches the installation wizard for first-time setups.
    """

    def __init__(self):
        """Initialize post-install hook."""
        self.config_service = ConfigService()
        self.installation_wizard = InstallationWizardService()
        self.logger: Optional[logging.Logger] = None

        # UV-specific environment detection
        self.uv_context = self._detect_uv_context()

    def _detect_uv_context(self) -> Dict[str, Any]:
        """Detect UV installation context from environment.

        Returns:
            Dictionary with UV context information
        """
        context = {
            "is_uv_install": False,
            "install_method": "unknown",
            "install_path": None,
            "uv_version": None,
            "is_global": False,
            "uv_tool_dir": None,
            "uv_cache_dir": None
        }

        # Check for UV environment variables
        if "UV_TOOL_DIR" in os.environ:
            context["is_uv_install"] = True
            context["install_method"] = "uv-tool"
            context["uv_tool_dir"] = Path(os.environ["UV_TOOL_DIR"])
            context["is_global"] = True

        # Check for UVX installation
        if "UVX_ROOT" in os.environ:
            context["is_uv_install"] = True
            context["install_method"] = "uvx"
            context["is_global"] = True

        # Detect from execution context
        if not context["is_uv_install"]:
            current_executable = Path(sys.executable)

            # Check if running from UV virtual environment
            if "uv" in str(current_executable).lower():
                context["is_uv_install"] = True

                # Determine method based on path structure
                if ".local" in str(current_executable):
                    context["install_method"] = "uvx" if "uvx" in str(current_executable) else "uv-tool"
                else:
                    context["install_method"] = "uv-tool"

                context["is_global"] = True

        # Get install path
        try:
            import shutil
            docbro_path = shutil.which("docbro")
            if docbro_path:
                context["install_path"] = Path(docbro_path)
        except Exception:
            pass

        # Get UV version
        context["uv_version"] = self._get_uv_version()

        # Get UV cache directory
        if "UV_CACHE_DIR" in os.environ:
            context["uv_cache_dir"] = Path(os.environ["UV_CACHE_DIR"])

        return context

    def _get_uv_version(self) -> Optional[str]:
        """Get UV version if available.

        Returns:
            UV version string or None if not available
        """
        try:
            import subprocess
            result = subprocess.run(
                ["uv", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                # Extract version from output like "uv 0.4.0"
                parts = result.stdout.strip().split()
                if len(parts) >= 2:
                    return parts[-1]
        except (FileNotFoundError, subprocess.TimeoutExpired, Exception):
            pass
        return None

    def _is_first_time_installation(self) -> bool:
        """Check if this is a first-time installation.

        Returns:
            True if no previous installation context exists
        """
        try:
            # Check for existing installation context
            context = self.config_service.load_installation_context()
            if context:
                return False

            # Check for any existing configuration
            config_dir = self.config_service.config_dir
            if config_dir.exists():
                # Look for any configuration files
                config_files = list(config_dir.glob("*.json"))
                if config_files:
                    return False

            return True
        except Exception as e:
            # If we can't determine, assume first time for safety
            self.logger and self.logger.warning(f"Cannot determine installation status: {e}")
            return True

    async def _run_installation_wizard(self) -> bool:
        """Run the installation wizard for first-time setup.

        Returns:
            True if wizard completed successfully, False otherwise
        """
        try:
            # Create installation request from UV context
            request = InstallationRequest(
                install_method=self.uv_context["install_method"],
                version="1.0.0",  # TODO: Get from package metadata
                user_preferences={
                    "auto_setup": True,
                    "install_source": "uv-post-install"
                }
            )

            # Start installation process
            response = await self.installation_wizard.start_installation(request)

            if response.status == "started":
                self.logger and self.logger.info(
                    f"Installation wizard started: {response.installation_id}"
                )

                # Wait for completion with timeout
                max_wait_time = 300  # 5 minutes
                wait_interval = 2  # 2 seconds
                waited = 0

                while waited < max_wait_time:
                    await asyncio.sleep(wait_interval)
                    waited += wait_interval

                    status_info = self.installation_wizard.get_installation_status()

                    if status_info["status"] == "complete":
                        self.logger and self.logger.info("Installation completed successfully")
                        return True
                    elif status_info["status"] == "error":
                        self.logger and self.logger.error(
                            f"Installation failed: {status_info.get('message', 'Unknown error')}"
                        )
                        return False

                # Timeout reached
                self.logger and self.logger.warning("Installation wizard timed out")
                return False
            else:
                self.logger and self.logger.error(f"Failed to start installation: {response.message}")
                return False

        except Exception as e:
            self.logger and self.logger.error(f"Installation wizard failed: {e}")
            return False

    def _should_run_automatically(self) -> bool:
        """Determine if post-install hook should run automatically.

        Returns:
            True if hook should run without user confirmation
        """
        # Check environment variable to skip auto-setup
        if os.environ.get("DOCBRO_SKIP_AUTO_SETUP", "").lower() in ("1", "true", "yes"):
            return False

        # Check if running in CI/automated environment
        ci_indicators = [
            "CI", "CONTINUOUS_INTEGRATION", "BUILD_NUMBER",
            "GITHUB_ACTIONS", "GITLAB_CI", "JENKINS_URL"
        ]
        if any(var in os.environ for var in ci_indicators):
            return False

        # Check if TTY available for interactive prompts
        if not sys.stdout.isatty():
            return False

        # Run automatically for UV installations by default
        return self.uv_context["is_uv_install"]

    async def run_hook(self) -> int:
        """Main entry point for post-install hook.

        Returns:
            Exit code (0 for success, 1 for failure)
        """
        try:
            # Setup logging with default config for post-install
            from src.core.config import DocBroConfig
            default_config = DocBroConfig()
            setup_logging(default_config)
            self.logger = get_component_logger("post_install")

            self.logger.info("UV post-install hook starting")
            self.logger.debug(f"UV context: {self.uv_context}")

            # Check if this is a UV installation
            if not self.uv_context["is_uv_install"]:
                self.logger.info("Not a UV installation, skipping post-install hook")
                return 0

            # Check if first-time installation
            if not self._is_first_time_installation():
                self.logger.info("DocBro already configured, skipping setup")

                # Show brief welcome message for existing installations
                console.print("\n[green]✓[/green] DocBro is ready to use!")
                console.print("Run [bold]docbro --help[/bold] to get started.")
                return 0

            # Display welcome banner
            welcome_text = (
                "[bold green]Welcome to DocBro![/bold green]\n\n"
                "DocBro is a documentation crawler and search tool with RAG capabilities.\n"
                f"Installed via: {self.uv_context['install_method']}\n"
                f"Install path: {self.uv_context.get('install_path', 'Unknown')}\n\n"
                "This is your first time running DocBro. "
                "The setup wizard will help you configure external services."
            )

            console.print(Panel(welcome_text, title="DocBro Setup", padding=(1, 2)))

            # Determine if we should run automatically or ask user
            if self._should_run_automatically():
                run_setup = True
                console.print("\n[yellow]Starting automatic setup...[/yellow]")
            else:
                # Ask user if they want to run setup now
                run_setup = Confirm.ask(
                    "\nWould you like to run the setup wizard now?",
                    default=True
                )

            if run_setup:
                console.print("\n[cyan]Running installation wizard...[/cyan]")

                success = await self._run_installation_wizard()

                if success:
                    console.print("\n[green]✓ DocBro setup completed successfully![/green]")
                    console.print("\nYou can now:")
                    console.print("• Run [bold]docbro --help[/bold] to see all commands")
                    console.print("• Run [bold]docbro status[/bold] to check system status")
                    console.print("• Run [bold]docbro create <name> -u <url>[/bold] to create your first project")
                    return 0
                else:
                    console.print("\n[red]✗ Setup encountered issues.[/red]")
                    console.print("You can run [bold]docbro setup[/bold] manually to retry.")
                    return 1
            else:
                # User chose to skip setup
                console.print("\n[yellow]Setup skipped.[/yellow]")
                console.print("You can run [bold]docbro setup[/bold] anytime to configure DocBro.")
                console.print("Run [bold]docbro --help[/bold] to see available commands.")
                return 0

        except KeyboardInterrupt:
            console.print("\n[yellow]Setup cancelled by user.[/yellow]")
            return 1
        except Exception as e:
            error_msg = f"Post-install hook failed: {str(e)}"
            console.print(f"\n[red]✗ {error_msg}[/red]")

            if self.logger:
                self.logger.error(error_msg, exc_info=True)

            # Provide fallback instructions
            console.print("\n[yellow]Fallback instructions:[/yellow]")
            console.print("• Run [bold]docbro setup[/bold] to configure DocBro manually")
            console.print("• Run [bold]docbro --help[/bold] to see all available commands")

            return 1

    def log_installation_event(self) -> None:
        """Log installation event for telemetry/debugging purposes."""
        try:
            event_data = {
                "event": "uv_post_install",
                "timestamp": str(asyncio.get_event_loop().time()),
                "install_method": self.uv_context["install_method"],
                "uv_version": self.uv_context["uv_version"],
                "is_global": self.uv_context["is_global"],
                "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
                "platform": sys.platform
            }

            if self.logger:
                self.logger.info("Installation event logged", extra=event_data)

        except Exception as e:
            # Don't fail installation for logging errors
            if self.logger:
                self.logger.warning(f"Failed to log installation event: {e}")


def main() -> int:
    """Main entry point for UV post-install hook.

    Returns:
        Exit code (0 for success, 1 for failure)
    """
    hook = UVPostInstallHook()

    # Log installation event
    hook.log_installation_event()

    # Run async hook
    try:
        return asyncio.run(hook.run_hook())
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user.[/yellow]")
        return 1
    except Exception as e:
        console.print(f"\n[red]✗ Unexpected error: {e}[/red]")
        return 1


if __name__ == "__main__":
    sys.exit(main())