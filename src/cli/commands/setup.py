"""Setup CLI command - now serves as interactive settings menu."""

import click
from rich.console import Console

from src.services.menu_ui_service import MenuUIService
from src.services.settings_service import SettingsService

console = Console()


@click.command()
@click.option('--reset', is_flag=True, help='Reset to factory defaults')
@click.option('--non-interactive', is_flag=True, help='Display current settings without menu')
def setup(reset: bool, non_interactive: bool):
    """Configure global settings interactively.

    This command provides an interactive menu to modify your global DocBro settings.
    Use arrow keys to navigate, Enter to edit, and Esc/q to quit.

    Examples:
      docbro setup              # Interactive settings menu
      docbro setup --reset      # Reset to factory defaults
      docbro setup --non-interactive  # Just show current settings
    """
    settings_service = SettingsService()

    try:
        # Handle reset flag
        if reset:
            if click.confirm("Reset all global settings to factory defaults?", abort=True):
                backup_path = settings_service.reset_to_factory_defaults(backup=True)
                if backup_path:
                    console.print(f"[green]✓[/green] Settings reset to defaults")
                    console.print(f"[dim]Backup saved to: {backup_path}[/dim]")
                else:
                    console.print("[green]✓[/green] Settings reset to defaults")
                return

        # Load current settings
        settings = settings_service.get_global_settings()

        if non_interactive:
            # Just display current settings
            from src.cli.commands.setup_settings import display_settings_table
            display_settings_table(settings)
            return

        # Show interactive menu
        menu_service = MenuUIService()

        try:
            # Check if settings exist
            if not settings_service.global_settings_path.exists():
                console.print("[yellow]⚠[/yellow] Global settings not found.")
                console.print("Run [cyan]docbro init[/cyan] first to initialize DocBro.")
                return

            # Run interactive menu
            updated_settings = menu_service.run_interactive_menu(settings)

            if updated_settings:
                # Save updated settings
                settings_service.save_global_settings(updated_settings)
                console.print("\n[green]✓[/green] Settings saved successfully!")
            else:
                console.print("\n[yellow]ℹ[/yellow] No changes made.")

        except KeyboardInterrupt:
            console.print("\n[yellow]⚠[/yellow] Setup cancelled by user")
        except Exception as e:
            console.print(f"\n[red]✗[/red] Error during setup: {e}")
            raise click.ClickException(str(e))

    except Exception as e:
        console.print(f"[red]✗[/red] Setup failed: {e}")
        raise click.ClickException(str(e))