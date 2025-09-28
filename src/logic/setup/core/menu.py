"""Interactive menu system for setup operations."""

import sys
from typing import Optional, List, Dict, Any, Tuple
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from src.logic.setup.models.menu_state import MenuState
from src.core.lib_logger import get_logger

logger = get_logger(__name__)

# Platform-specific imports
try:
    import termios
    import tty
    HAS_TERMIOS = True
except ImportError:
    HAS_TERMIOS = False


class InteractiveMenu:
    """Interactive menu for setup operations."""

    def __init__(self, console: Optional[Console] = None):
        """Initialize the interactive menu.

        Args:
            console: Optional Rich console for testing
        """
        self.console = console or Console()
        self.state = MenuState()
        self.options: List[str] = []
        self.current_index = 0
        self._use_keyboard_navigation = sys.stdin.isatty() and HAS_TERMIOS

    def run(self) -> Optional[str]:
        """Run the interactive menu.

        Returns:
            Selected operation or None if cancelled
        """
        try:
            while True:
                self.clear_screen()
                selection = self._show_current_menu()

                if selection == "exit":
                    return None
                elif selection == "back":
                    if self.state.is_at_root():
                        return None
                    self.state.go_back()
                elif selection in ["initialize", "uninstall", "reset"]:
                    return selection
                elif selection == "configuration":
                    self._handle_configuration()
                else:
                    # Navigate to submenu
                    self.state.push_menu(selection)

        except KeyboardInterrupt:
            return None
        except Exception as e:
            logger.error(f"Menu error: {e}")
            return None

    def display_main_menu(self) -> None:
        """Display the main menu."""
        self.console.print("\n[bold cyan]DocBro Setup Menu[/bold cyan]\n")

        options = [
            ("1", "Initialize DocBro", "initialize"),
            ("2", "Modify Configuration", "configuration"),
            ("3", "Uninstall DocBro", "uninstall"),
            ("4", "Reset Installation", "reset"),
            ("5", "Exit", "exit")
        ]

        table = Table(show_header=False, show_edge=False)
        table.add_column("Key", style="yellow")
        table.add_column("Option")

        for i, (key, label, _) in enumerate(options):
            if self.current_index == i:
                table.add_row(f"→ {key}", f"[bold bright_white on blue] {label} [/bold bright_white on blue]")
            else:
                table.add_row(f"  {key}", label)

        self.console.print(table)

    def display_configuration_menu(self) -> None:
        """Display configuration modification menu."""
        self.console.print("\n[bold cyan]Configuration Settings[/bold cyan]\n")

        # Load current configuration
        from src.logic.setup.services.configurator import SetupConfigurator
        configurator = SetupConfigurator()

        try:
            config = configurator.load_config()
        except FileNotFoundError:
            self.console.print("[red]No configuration found. Please initialize first.[/red]")
            self.console.print("\nPress Enter to go back...")
            input()
            self.state.go_back()
            return

        # Display current settings
        table = Table(show_header=True)
        table.add_column("Setting", style="cyan")
        table.add_column("Current Value", style="green")

        table.add_row("Vector Store", config.get("vector_store_provider", "Not set"))
        table.add_row("Ollama URL", config.get("ollama_url", "Not set"))
        table.add_row("Embedding Model", config.get("embedding_model", "Not set"))

        self.console.print(table)

        options = [
            ("1", "Change Vector Store", "vector_store"),
            ("2", "Change Ollama URL", "ollama_url"),
            ("3", "Change Embedding Model", "embedding_model"),
            ("4", "Back to Main Menu", "back")
        ]

        self.console.print("\n[yellow]Select an option:[/yellow]")
        options_table = Table(show_header=False, show_edge=False)
        options_table.add_column("Key", style="yellow")
        options_table.add_column("Option")

        for i, (key, label, _) in enumerate(options):
            if self.current_index == i:
                options_table.add_row(f"→ {key}", f"[bold bright_white on blue] {label} [/bold bright_white on blue]")
            else:
                options_table.add_row(f"  {key}", label)

        self.console.print(options_table)

    def _get_char(self) -> str:
        """Get a single character from stdin without Enter.

        Returns:
            Character pressed or special key name
        """
        if not self._use_keyboard_navigation or not HAS_TERMIOS:
            # Fallback for non-TTY environments or platforms without termios
            return input().strip()

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)

        try:
            tty.setraw(sys.stdin.fileno())
            ch = sys.stdin.read(1)

            # Handle escape sequences (arrow keys)
            if ch == '\x1b':  # ESC
                ch2 = sys.stdin.read(1)
                if ch2 == '[':
                    ch3 = sys.stdin.read(1)
                    if ch3 == 'A':
                        return 'up'
                    elif ch3 == 'B':
                        return 'down'
                    elif ch3 == 'C':
                        return 'right'
                    elif ch3 == 'D':
                        return 'left'
                return 'escape'
            elif ch == '\r' or ch == '\n':
                return 'enter'
            elif ch == '\x03':  # Ctrl+C
                raise KeyboardInterrupt
            elif ch == 'q':
                return 'quit'
            elif ch == '?':
                return 'help'
            elif ch.isdigit():
                return ch
            else:
                return ch

        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)

    def handle_key(self, key: str) -> Optional[str]:
        """Handle keyboard input.

        Args:
            key: Key pressed

        Returns:
            Selected option or None
        """
        if key == "down":
            self.current_index = (self.current_index + 1) % len(self.options)
        elif key == "up":
            self.current_index = (self.current_index - 1) % len(self.options)
        elif key == "enter":
            if self.options:
                return self.options[self.current_index]
        elif key == "escape" or key == "quit":
            return "back" if not self.state.is_at_root() else "exit"
        elif key == "?":
            self.display_help()
        elif key.isdigit():
            # Allow direct number selection as fallback
            idx = int(key) - 1
            if 0 <= idx < len(self.options):
                return self.options[idx]

        return None

    def display_help(self) -> None:
        """Display help information."""
        help_text = """
[bold yellow]Navigation Help[/bold yellow]

• [cyan]↑/↓[/cyan] Arrow keys - Navigate menu options
• [cyan]1-5[/cyan] Numbers - Direct option selection
• [cyan]Enter[/cyan] - Select highlighted option
• [cyan]Escape[/cyan] or [cyan]q[/cyan] - Go back/quit
• [cyan]?[/cyan] - Show this help

[dim]Press any key to continue...[/dim]
"""
        self.console.print(Panel(help_text, title="Help", border_style="cyan"))
        if self._use_keyboard_navigation:
            self._get_char()
        else:
            input()

    def render(self) -> None:
        """Render the current menu state."""
        self.clear_screen()

        if self.state.current_menu == "main":
            self.display_main_menu()
        elif self.state.current_menu == "configuration":
            self.display_configuration_menu()

        # Show navigation path
        if not self.state.is_at_root():
            path = self.state.get_navigation_path()
            self.console.print(f"\n[dim]{path}[/dim]")

        # Show help hint
        if not self.state.help_visible:
            self.console.print("\n[dim]Press ? for help[/dim]")

    def clear_screen(self) -> None:
        """Clear the terminal screen."""
        self.console.clear()

    def show_error(self, message: str) -> None:
        """Display an error message.

        Args:
            message: Error message to display
        """
        self.console.print(f"[red]Error: {message}[/red]")
        self.console.print("\n[dim]Press Enter to continue...[/dim]")
        input()

    def validate_url(self, url: str) -> bool:
        """Validate URL format.

        Args:
            url: URL to validate

        Returns:
            True if valid
        """
        return url.startswith(("http://", "https://"))

    def validate_config_value(self, key: str, value: Any) -> bool:
        """Validate a configuration value.

        Args:
            key: Configuration key
            value: Value to validate

        Returns:
            True if valid
        """
        if key == "vector_store_provider":
            return value in ["sqlite_vec", "qdrant"]
        elif key == "ollama_url":
            return self.validate_url(value)
        elif key == "embedding_model":
            valid_models = ["mxbai-embed-large", "nomic-embed-text", "all-minilm"]
            return value in valid_models

        return True

    def enter_submenu(self, menu_id: str) -> None:
        """Navigate to a submenu.

        Args:
            menu_id: Menu identifier
        """
        self.state.push_menu(menu_id)
        self.current_index = 0

    def get_main_menu_options(self) -> List[str]:
        """Get main menu options.

        Returns:
            List of option labels
        """
        return [
            "Initialize DocBro",
            "Modify Configuration",
            "Uninstall DocBro",
            "Reset Installation",
            "Exit"
        ]

    def filter_options(self, search: str) -> List[str]:
        """Filter options by search term.

        Args:
            search: Search term

        Returns:
            Filtered options
        """
        if not search:
            return self.options

        search_lower = search.lower()
        return [opt for opt in self.options if search_lower in opt.lower()]

    def _show_current_menu(self) -> Optional[str]:
        """Show the current menu and get selection.

        Returns:
            Selected option
        """
        if self.state.current_menu == "main":
            return self._show_main_menu()
        elif self.state.current_menu == "configuration":
            return self._show_configuration_menu()
        else:
            return None

    def _show_main_menu(self) -> Optional[str]:
        """Show main menu and get selection.

        Returns:
            Selected option
        """
        # Setup menu options
        self.options = ["initialize", "configuration", "uninstall", "reset", "exit"]
        self.current_index = 0

        while True:
            self.clear_screen()
            self.display_main_menu()

            if self._use_keyboard_navigation:
                self.console.print("\n[dim]Use ↑/↓ arrows or numbers to navigate, Enter to select, ? for help, q to quit[/dim]")
                key = self._get_char()
            else:
                # Fallback to numbered input for non-TTY environments
                choice = Prompt.ask(
                    "\n[yellow]Select an option[/yellow]",
                    choices=["1", "2", "3", "4", "5"],
                    default="5"
                )
                option_map = {
                    "1": "initialize",
                    "2": "configuration",
                    "3": "uninstall",
                    "4": "reset",
                    "5": "exit"
                }
                return option_map.get(choice)

            result = self.handle_key(key)
            if result:
                return result

    def _show_configuration_menu(self) -> Optional[str]:
        """Show configuration menu and get selection.

        Returns:
            Selected option
        """
        # Setup menu options
        self.options = ["vector_store", "ollama_url", "embedding_model", "back"]
        self.current_index = 0

        while True:
            self.clear_screen()
            self.display_configuration_menu()

            if self._use_keyboard_navigation:
                self.console.print("\n[dim]Use ↑/↓ arrows or numbers to navigate, Enter to select, ? for help, q to quit[/dim]")
                key = self._get_char()
            else:
                # Fallback to numbered input for non-TTY environments
                choice = Prompt.ask(
                    "\n[yellow]Select an option[/yellow]",
                    choices=["1", "2", "3", "4"],
                    default="4"
                )
                if choice == "4":
                    return "back"

                option_map = {
                    "1": "vector_store",
                    "2": "ollama_url",
                    "3": "embedding_model"
                }
                config_key = option_map.get(choice)
                if config_key:
                    self._modify_config_value(config_key)
                continue

            result = self.handle_key(key)
            if result == "back":
                return "back"
            elif result in ["vector_store", "ollama_url", "embedding_model"]:
                self._modify_config_value(result)
                # Stay in menu after modification
                continue

    def _handle_configuration(self) -> None:
        """Handle configuration menu navigation."""
        self.state.push_menu("configuration")

    def _modify_config_value(self, key: str) -> None:
        """Modify a configuration value.

        Args:
            key: Configuration key to modify
        """
        from src.logic.setup.services.configurator import SetupConfigurator
        configurator = SetupConfigurator()

        # Get new value from user
        if key == "vector_store":
            new_value = Prompt.ask(
                "Select vector store",
                choices=["sqlite_vec", "qdrant"],
                default="sqlite_vec"
            )
        elif key == "ollama_url":
            new_value = Prompt.ask(
                "Enter Ollama URL",
                default="http://localhost:11434"
            )
        elif key == "embedding_model":
            new_value = Prompt.ask(
                "Select embedding model",
                choices=["mxbai-embed-large", "nomic-embed-text", "all-minilm"],
                default="mxbai-embed-large"
            )
        else:
            return

        # Validate and save
        if self.validate_config_value(key, new_value):
            try:
                config = configurator.load_config()
                config[key] = new_value
                configurator.save_config(config)
                self.console.print(f"[green]✓ {key} updated successfully[/green]")
            except Exception as e:
                self.show_error(f"Failed to update configuration: {e}")
        else:
            self.show_error(f"Invalid value for {key}")

    def confirm_action(self, action: str) -> bool:
        """Get confirmation for an action.

        Args:
            action: Action to confirm

        Returns:
            True if confirmed
        """
        return Confirm.ask(f"Are you sure you want to {action}?", default=False)

    def save_configuration(self) -> None:
        """Save pending configuration changes."""
        if self.state.has_pending_changes():
            if self.confirm_action("save configuration changes"):
                changes = self.state.save_changes()
                # Apply changes through configurator
                from src.logic.setup.services.configurator import SetupConfigurator
                configurator = SetupConfigurator()
                config = configurator.load_config()
                config.update(changes)
                configurator.save_config(config)
                self.console.print("[green]✓ Configuration saved[/green]")

    def start_uninstall(self) -> Optional[str]:
        """Start uninstall process with confirmation.

        Returns:
            "uninstall" if confirmed, None otherwise
        """
        from src.logic.setup.services.uninstaller import SetupUninstaller
        uninstaller = SetupUninstaller()

        # Generate and show manifest
        manifest = uninstaller.generate_manifest()

        self.console.print("\n[bold red]Uninstall Manifest[/bold red]\n")
        for line in manifest.to_display_list():
            self.console.print(line)

        if self.confirm_action("proceed with uninstallation"):
            return "uninstall"

        return None