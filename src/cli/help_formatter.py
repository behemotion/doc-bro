"""
CLI Help formatter for enhanced command line documentation.
"""


import click


class CliHelpFormatter:
    """Enhanced help formatter for DocBro CLI commands."""

    def __init__(self):
        """Initialize the help formatter."""
        self.max_width = 80
        self.current_indent = 0

    def format_usage(self, ctx: click.Context, prog_name: str, args: list[str] = None) -> str:
        """Format the usage line for a command."""
        if args is None:
            args = []

        usage_pieces = [prog_name]
        usage_pieces.extend(args)

        return "Usage: " + " ".join(usage_pieces)

    def format_help_text(self, ctx: click.Context, text: str) -> str:
        """Format help text with proper wrapping and indentation."""
        if not text:
            return ""

        # Simple text formatting - wrap at max_width
        lines = []
        for line in text.split('\n'):
            if len(line) <= self.max_width:
                lines.append(line)
            else:
                # Simple word wrapping
                words = line.split()
                current_line = ""
                for word in words:
                    if len(current_line + " " + word) <= self.max_width:
                        if current_line:
                            current_line += " " + word
                        else:
                            current_line = word
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = word
                if current_line:
                    lines.append(current_line)

        return '\n'.join(lines)

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Format the list of available commands."""
        commands = []
        if hasattr(ctx.command, 'list_commands'):
            for name in ctx.command.list_commands(ctx):
                cmd = ctx.command.get_command(ctx, name)
                if cmd is not None:
                    help_text = cmd.get_short_help_str() or ""
                    commands.append((name, help_text))

        if commands:
            with formatter.section("Commands"):
                formatter.write_dl(commands)

    def format_options(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """Format command options."""
        opts = []
        for param in ctx.command.get_params(ctx):
            rv = param.get_help_record(ctx)
            if rv is not None:
                opts.append(rv)

        if opts:
            with formatter.section("Options"):
                formatter.write_dl(opts)
