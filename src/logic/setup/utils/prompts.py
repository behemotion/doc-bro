"""User prompt utilities."""

from rich.console import Console
from rich.prompt import Confirm, Prompt
from rich.table import Table

from src.cli.utils.navigation import prompt_with_arrows
from src.core.lib_logger import get_logger

logger = get_logger(__name__)


def confirm_action(
    prompt: str,
    default: bool = False,
    console: Console | None = None
) -> bool:
    """Get confirmation for an action.

    Args:
        prompt: Confirmation prompt
        default: Default value if user presses Enter
        console: Optional Rich console

    Returns:
        True if confirmed
    """
    console = console or Console()

    try:
        return Confirm.ask(prompt, default=default, console=console)
    except (KeyboardInterrupt, EOFError):
        return False


def confirm_dangerous_action(
    first_prompt: str,
    second_prompt: str,
    default: bool = False,
    console: Console | None = None
) -> bool:
    """Get double confirmation for dangerous actions with red text warning.

    Args:
        first_prompt: First confirmation prompt
        second_prompt: Second confirmation prompt (shown in red)
        default: Default value if user presses Enter
        console: Optional Rich console

    Returns:
        True if both confirmations are accepted
    """
    console = console or Console()

    try:
        # First confirmation
        if not Confirm.ask(first_prompt, default=default, console=console):
            return False

        # Second confirmation with red text
        console.print(f"\n[bold red]{second_prompt}[/bold red]")
        return Confirm.ask("[bold red]Are you absolutely sure?[/bold red]", default=False, console=console)
    except (KeyboardInterrupt, EOFError):
        return False


def prompt_choice(
    prompt: str,
    choices: list[tuple[str, str]],
    default: str | None = None,
    console: Console | None = None
) -> str:
    """Prompt user to select from choices with arrow key navigation.

    Args:
        prompt: Prompt message
        choices: List of (value, description) tuples
        default: Default choice value
        console: Optional Rich console

    Returns:
        Selected choice value
    """
    result = prompt_with_arrows(prompt, choices, default, console)
    return result or (default or choices[0][0] if choices else "")


def prompt_text(
    prompt: str,
    default: str | None = None,
    password: bool = False,
    console: Console | None = None
) -> str:
    """Prompt for text input.

    Args:
        prompt: Prompt message
        default: Default value
        password: Hide input (for passwords)
        console: Optional Rich console

    Returns:
        User input
    """
    console = console or Console()

    try:
        return Prompt.ask(
            prompt,
            default=default,
            password=password,
            console=console
        )
    except (KeyboardInterrupt, EOFError):
        return default or ""


def prompt_path(
    prompt: str,
    default: str | None = None,
    must_exist: bool = False,
    console: Console | None = None
) -> str:
    """Prompt for a file or directory path.

    Args:
        prompt: Prompt message
        default: Default path
        must_exist: Whether path must exist
        console: Optional Rich console

    Returns:
        Path string
    """
    from pathlib import Path

    console = console or Console()

    while True:
        path_str = prompt_text(prompt, default=default, console=console)

        if not path_str:
            return default or ""

        path = Path(path_str).expanduser()

        if must_exist and not path.exists():
            console.print(f"[red]Path does not exist: {path}[/red]")
            if not confirm_action("Try again?", default=True, console=console):
                return default or ""
        else:
            return str(path)


def prompt_url(
    prompt: str,
    default: str | None = None,
    validate: bool = True,
    console: Console | None = None
) -> str:
    """Prompt for a URL.

    Args:
        prompt: Prompt message
        default: Default URL
        validate: Whether to validate URL format
        console: Optional Rich console

    Returns:
        URL string
    """
    console = console or Console()

    while True:
        url = prompt_text(prompt, default=default, console=console)

        if not url:
            return default or ""

        if validate:
            if not url.startswith(("http://", "https://")):
                console.print(f"[red]Invalid URL format: {url}[/red]")
                console.print("[dim]URL must start with http:// or https://[/dim]")
                if not confirm_action("Try again?", default=True, console=console):
                    return default or ""
            else:
                return url
        else:
            return url


def prompt_multiselect(
    prompt: str,
    choices: list[tuple[str, str, bool]],
    console: Console | None = None
) -> list[str]:
    """Prompt for multiple selections.

    Args:
        prompt: Prompt message
        choices: List of (value, description, default_selected) tuples
        console: Optional Rich console

    Returns:
        List of selected values
    """
    console = console or Console()
    selected = {}

    # Initialize selections
    for value, _, default in choices:
        selected[value] = default

    console.print(f"\n[cyan]{prompt}[/cyan]")
    console.print("[dim]Use numbers to toggle, 'a' for all, 'n' for none, Enter to confirm[/dim]\n")

    while True:
        # Display current selections
        table = Table(show_header=False, show_edge=False)
        table.add_column("Num", style="yellow")
        table.add_column("Selected", style="green")
        table.add_column("Option")

        for i, (value, description, _) in enumerate(choices, 1):
            check = "✓" if selected[value] else " "
            table.add_row(str(i), f"[{check}]", description)

        console.print(table)

        # Get user input
        try:
            choice = Prompt.ask(
                "Toggle option (or a/n/Enter)",
                default="",
                console=console
            )

            if choice == "":
                # Confirm selections
                break
            elif choice.lower() == "a":
                # Select all
                for value, _, _ in choices:
                    selected[value] = True
            elif choice.lower() == "n":
                # Select none
                for value, _, _ in choices:
                    selected[value] = False
            elif choice.isdigit():
                # Toggle specific option
                idx = int(choice) - 1
                if 0 <= idx < len(choices):
                    value = choices[idx][0]
                    selected[value] = not selected[value]
                else:
                    console.print("[red]Invalid option number[/red]")
            else:
                console.print("[red]Invalid input[/red]")

            # Clear previous display
            console.clear()

        except (KeyboardInterrupt, EOFError):
            break

    return [value for value, is_selected in selected.items() if is_selected]


def show_warning(
    message: str,
    console: Console | None = None
) -> None:
    """Show a warning message.

    Args:
        message: Warning message
        console: Optional Rich console
    """
    console = console or Console()
    console.print(f"[yellow]⚠ Warning:[/yellow] {message}")


def show_error(
    message: str,
    console: Console | None = None
) -> None:
    """Show an error message.

    Args:
        message: Error message
        console: Optional Rich console
    """
    console = console or Console()
    console.print(f"[red]✗ Error:[/red] {message}")


def show_success(
    message: str,
    console: Console | None = None
) -> None:
    """Show a success message.

    Args:
        message: Success message
        console: Optional Rich console
    """
    console = console or Console()
    console.print(f"[green]✓[/green] {message}")
