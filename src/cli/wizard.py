"""Installation wizard CLI module for DocBro."""

import asyncio
from typing import Optional

import click
from rich.console import Console
from rich.prompt import Confirm

from src.services.setup import SetupWizardService
from src.services.config import ConfigService


def run_async(coro):
    """Run async coroutine in sync context."""
    # Optional uvloop for better performance
    try:
        import uvloop
        uvloop.install()
    except ImportError:
        pass

    return asyncio.run(coro)


@click.command()
@click.option("--force", is_flag=True, help="Re-run setup even if already completed")
@click.option("--non-interactive", is_flag=True, help="Non-interactive setup with defaults")
@click.option("--skip-services", is_flag=True, help="Skip service installation prompts")
@click.pass_context
def setup(ctx: click.Context, force: bool, non_interactive: bool, skip_services: bool):
    """Run the interactive setup wizard.

    This command guides you through the initial configuration of DocBro,
    including service detection, dependency installation guidance, and
    configuration setup.

    Examples:
        docbro setup                        # Interactive setup
        docbro setup --force                # Re-run setup
        docbro setup --non-interactive      # Non-interactive with defaults
        docbro setup --skip-services        # Skip service installation
    """
    async def _setup():
        console = Console()
        wizard = SetupWizardService()

        try:
            # Check if setup is required (unless --force)
            if not force and not wizard.check_setup_required():
                console.print("[yellow]DocBro is already set up![/yellow]")

                if non_interactive:
                    console.print("Use --force to re-run setup.")
                    return

                if not Confirm.ask("Would you like to run setup again?", default=False):
                    console.print("Setup cancelled.")
                    return

                # Clear existing configuration for re-setup
                config_service = ConfigService()
                config_path = config_service.installation_config_path
                if config_path.exists():
                    config_path.unlink()
                    console.print("[dim]Cleared existing configuration.[/dim]")

            # Handle non-interactive mode
            if non_interactive:
                console.print("[cyan]Running setup in non-interactive mode...[/cyan]")
                # For non-interactive mode, we'll run a streamlined setup
                context = await wizard.run_quiet_setup()
            else:
                # Run interactive setup
                context = await wizard.run_interactive_setup(skip_services=skip_services)

            # Show success message
            console.print(f"\n[green]✓ Setup completed successfully![/green]")
            console.print(f"[dim]Configuration saved to: {context.config_dir}[/dim]")

            # Show quick start tips
            console.print("\n[bold]Quick Start:[/bold]")
            console.print("1. Create a project: [cyan]docbro create myproject --url https://docs.example.com[/cyan]")
            console.print("2. Crawl documentation: [cyan]docbro crawl myproject[/cyan]")
            console.print("3. Search your docs: [cyan]docbro search \"your query\" --project myproject[/cyan]")

        except click.Abort:
            pass  # User cancelled, already handled
        except Exception as e:
            console.print(f"[red]✗ Setup failed: {e}[/red]")
            if ctx.obj and ctx.obj.get("verbose"):
                import traceback
                console.print("[dim]" + traceback.format_exc() + "[/dim]")
            raise click.ClickException(str(e))

    run_async(_setup())


@click.command()
@click.option("--detailed", is_flag=True, help="Show detailed installation status")
@click.pass_context
def installation_status(ctx: click.Context, detailed: bool):
    """Show DocBro installation status.

    This command displays the current installation status, including
    setup completion, configuration paths, and service availability.
    """
    async def _status():
        console = Console()
        wizard = SetupWizardService()

        try:
            status_info = wizard.get_setup_status()

            console.print("[bold]DocBro Installation Status[/bold]\n")

            if status_info["setup_completed"]:
                console.print("[green]✓ Installation completed[/green]")

                if detailed:
                    console.print(f"[cyan]Method:[/cyan] {status_info['install_method']}")
                    console.print(f"[cyan]Install Date:[/cyan] {status_info['install_date']}")
                    console.print(f"[cyan]Version:[/cyan] {status_info['version']}")
                    console.print(f"[cyan]Config Dir:[/cyan] {status_info['config_dir']}")
                    console.print(f"[cyan]Data Dir:[/cyan] {status_info['data_dir']}")

                    # Check external services if detailed
                    console.print(f"\n[bold]External Services[/bold]")
                    from src.services.detection import ServiceDetectionService
                    detection_service = ServiceDetectionService()
                    statuses = await detection_service.check_all_services()

                    available_count = sum(1 for s in statuses.values() if s.available)
                    total_count = len(statuses)
                    console.print(f"{available_count}/{total_count} services available")

                    for name, status in statuses.items():
                        status_icon = "[green]✓[/green]" if status.available else "[red]✗[/red]"
                        version_info = f" ({status.version})" if status.version else ""
                        console.print(f"  {status_icon} {name.title()}{version_info}")
                        if not status.available and status.error_message and detailed:
                            console.print(f"    [dim]{status.error_message}[/dim]")

            elif status_info["in_progress"]:
                console.print(f"[yellow]⚠ Setup in progress (step: {status_info['current_step']})[/yellow]")
                console.print("Run [bold]docbro setup[/bold] to continue.")
            else:
                console.print("[red]✗ Setup required[/red]")
                console.print("Run [bold]docbro setup[/bold] to get started.")

        except Exception as e:
            console.print(f"[red]✗ Failed to get installation status: {e}[/red]")
            if ctx.obj and ctx.obj.get("verbose"):
                import traceback
                console.print("[dim]" + traceback.format_exc() + "[/dim]")
            raise click.ClickException(str(e))

    run_async(_status())


@click.command()
@click.pass_context
def reset_setup(ctx: click.Context):
    """Reset DocBro setup configuration.

    This command removes all setup-related configuration files,
    allowing you to run the setup wizard from scratch.
    """
    console = Console()

    # Confirm action
    if not Confirm.ask("Are you sure you want to reset DocBro setup? This will remove all configuration.", default=False):
        console.print("Reset cancelled.")
        return

    try:
        config_service = ConfigService()

        # Remove installation context
        installation_path = config_service.installation_config_path
        if installation_path.exists():
            installation_path.unlink()
            console.print(f"[green]✓[/green] Removed installation config: {installation_path}")

        # Remove wizard state
        wizard_path = config_service.config_dir / "wizard.json"
        if wizard_path.exists():
            wizard_path.unlink()
            console.print(f"[green]✓[/green] Removed wizard state: {wizard_path}")

        # Remove services config if exists
        services_path = config_service.config_dir / "services.json"
        if services_path.exists():
            services_path.unlink()
            console.print(f"[green]✓[/green] Removed services config: {services_path}")

        console.print(f"\n[green]✓ Setup reset complete![/green]")
        console.print("Run [bold]docbro setup[/bold] to configure DocBro again.")

    except Exception as e:
        console.print(f"[red]✗ Failed to reset setup: {e}[/red]")
        if ctx.obj and ctx.obj.get("verbose"):
            import traceback
            console.print("[dim]" + traceback.format_exc() + "[/dim]")
        raise click.ClickException(str(e))


# Group for wizard-related commands
@click.group(name="wizard")
def wizard_group():
    """Installation and setup wizard commands."""
    pass


# Add commands to the group
wizard_group.add_command(setup)
wizard_group.add_command(installation_status, name="status")
wizard_group.add_command(reset_setup, name="reset")


# Export the main setup command for direct use
__all__ = ["setup", "installation_status", "reset_setup", "wizard_group"]