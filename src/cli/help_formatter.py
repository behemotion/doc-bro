"""Enhanced help formatter for CLI commands."""

import click
from typing import List, Optional, Dict, Any
from textwrap import dedent, fill


class CliHelpFormatter(click.HelpFormatter):
    """Custom help formatter with enhanced readability."""

    def __init__(self, *args, **kwargs):
        """Initialize formatter with custom settings."""
        super().__init__(*args, **kwargs)
        self.max_width = 100  # Wider for better readability

    def write_usage(self, prog_name: str, args: str = "", prefix: str = "Usage: ") -> None:
        """Write usage line with better formatting.

        Args:
            prog_name: Program name
            args: Arguments string
            prefix: Usage prefix
        """
        usage_prefix = click.style(prefix, fg="cyan", bold=True)
        prog = click.style(prog_name, fg="green")
        self.write(f"{usage_prefix}{prog} {args}\n")

    def write_heading(self, heading: str) -> None:
        """Write a section heading with styling.

        Args:
            heading: Section heading text
        """
        formatted = click.style(f"\n{heading}:", fg="yellow", bold=True)
        self.write(formatted)
        self.write("\n")

    def write_dl(
        self,
        rows: List[tuple],
        col_max: int = 30,
        col_spacing: int = 2
    ) -> None:
        """Write definition list with improved formatting.

        Args:
            rows: List of (term, definition) tuples
            col_max: Maximum column width
            col_spacing: Spacing between columns
        """
        if not rows:
            return

        # Calculate optimal column width
        term_widths = [len(term) for term, _ in rows if term]
        if term_widths:
            col_max = min(max(term_widths) + col_spacing, col_max)

        for term, definition in rows:
            if term:
                term_styled = click.style(term, fg="cyan")
                self.write(f"  {term_styled}")

                if len(term) < col_max - 2:
                    self.write(" " * (col_max - len(term) - 2))
                else:
                    self.write("\n" + " " * col_max)

                if definition:
                    # Wrap definition text
                    wrapped = fill(
                        definition,
                        width=self.max_width - col_max,
                        initial_indent="",
                        subsequent_indent=" " * col_max
                    )
                    self.write(wrapped)

                self.write("\n")
            else:
                # Separator or blank line
                self.write("\n")


def format_command_help(ctx: click.Context) -> str:
    """Format comprehensive help for a command.

    Args:
        ctx: Click context

    Returns:
        Formatted help text
    """
    formatter = CliHelpFormatter()

    # Command name and description
    if ctx.command:
        formatter.write_usage(
            ctx.command_path or ctx.command.name,
            "[OPTIONS] [ARGS]..."
        )

        if ctx.command.help:
            formatter.write("\n")
            formatter.write(dedent(ctx.command.help))
            formatter.write("\n")

    # Global options
    global_options = []
    command_options = []

    for param in ctx.command.params if ctx.command else []:
        if isinstance(param, click.Option):
            option_names = ", ".join(param.opts)
            help_text = param.help or ""

            if param.is_flag:
                option_desc = f"{option_names}"
            else:
                metavar = param.metavar or param.type.name.upper()
                option_desc = f"{option_names} {metavar}"

            if param.default is not None and not param.is_flag:
                help_text += f" [default: {param.default}]"

            if "debug" in param.name or "verbose" in param.name or "help" in param.name:
                global_options.append((option_desc, help_text))
            else:
                command_options.append((option_desc, help_text))

    # Write options sections
    if global_options:
        formatter.write_heading("Global Options")
        formatter.write_dl(global_options)

    if command_options:
        formatter.write_heading("Command Options")
        formatter.write_dl(command_options)

    # Add examples if available
    if hasattr(ctx.command, 'examples'):
        formatter.write_heading("Examples")
        for example in ctx.command.examples:
            formatter.write(f"  {click.style('$', fg='green')} {example}\n")

    return formatter.getvalue()


def format_bare_command_help() -> str:
    """Format help message when docbro is run without arguments.

    Returns:
        Formatted help suggestion
    """
    message = click.style("DocBro CLI", fg="cyan", bold=True)
    message += "\n\n"
    message += "No command specified. "
    message += click.style("Try 'docbro --help'", fg="green")
    message += " for available commands.\n\n"

    message += "Quick start:\n"
    commands = [
        ("docbro create", "Create a new documentation project"),
        ("docbro crawl", "Crawl documentation for a project"),
        ("docbro search", "Search indexed documentation"),
        ("docbro --help", "Show all available commands")
    ]

    for cmd, desc in commands:
        message += f"  {click.style(cmd, fg='cyan'):30} {desc}\n"

    return message


def enhance_click_group(group: click.Group) -> None:
    """Enhance a Click group with better help formatting.

    Args:
        group: Click group to enhance
    """
    original_format_help = group.format_help

    def format_help(ctx, formatter):
        """Custom help formatter for the group."""
        # Use custom formatter
        custom_formatter = CliHelpFormatter()

        # Write header
        custom_formatter.write_usage(
            ctx.command_path or "docbro",
            "[OPTIONS] COMMAND [ARGS]..."
        )

        # Write description
        if group.help:
            custom_formatter.write("\n")
            custom_formatter.write(dedent(group.help))
            custom_formatter.write("\n")

        # Write options
        options = []
        for param in group.params:
            if isinstance(param, click.Option):
                option_names = ", ".join(param.opts)
                help_text = param.help or ""
                options.append((option_names, help_text))

        if options:
            custom_formatter.write_heading("Options")
            custom_formatter.write_dl(options)

        # Write commands
        commands = []
        for name in sorted(group.commands):
            cmd = group.commands[name]
            if not cmd.hidden:
                help_text = cmd.get_short_help_str(limit=65) or ""
                commands.append((name, help_text))

        if commands:
            custom_formatter.write_heading("Commands")
            custom_formatter.write_dl(commands)

        # Additional help
        custom_formatter.write("\n")
        custom_formatter.write(
            click.style(
                "Run 'docbro COMMAND --help' for more information on a command.\n",
                fg="white",
                dim=True
            )
        )

        return custom_formatter.getvalue()

    group.format_help = format_help


class ComprehensiveHelpCommand(click.Command):
    """Command that shows comprehensive help for all subcommands."""

    def __init__(self, *args, **kwargs):
        """Initialize with comprehensive help."""
        super().__init__(*args, **kwargs)

    def format_help(self, ctx, formatter):
        """Format comprehensive help showing all commands and options."""
        custom_formatter = CliHelpFormatter()

        # Main usage
        custom_formatter.write_usage("docbro", "[OPTIONS] COMMAND [ARGS]...")
        custom_formatter.write("\n")
        custom_formatter.write("DocBro - Documentation crawler and search tool\n")

        # List all commands with their options
        if ctx.parent and hasattr(ctx.parent.command, 'commands'):
            custom_formatter.write_heading("Available Commands")

            for name in sorted(ctx.parent.command.commands):
                cmd = ctx.parent.command.commands[name]
                if not cmd.hidden:
                    # Command name and description
                    custom_formatter.write(f"\n  {click.style(name, fg='green', bold=True)}")
                    if cmd.help:
                        custom_formatter.write(f" - {cmd.get_short_help_str(limit=60)}")
                    custom_formatter.write("\n")

                    # Command options
                    for param in cmd.params:
                        if isinstance(param, click.Option):
                            option_str = ", ".join(param.opts)
                            custom_formatter.write(f"    {click.style(option_str, fg='cyan')}")
                            if param.help:
                                custom_formatter.write(f" - {param.help}")
                            custom_formatter.write("\n")

        return custom_formatter.getvalue()