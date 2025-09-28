"""Unified setup command for all setup operations."""

import click
from typing import Optional
from src.logic.setup.core.orchestrator import SetupOrchestrator
from src.logic.setup.core.router import CommandRouter
from src.core.lib_logger import get_logger
from src.core.config import get_config
from src.logic.health.services.health_reporter import HealthReporter
from rich.console import Console
from rich.table import Table

logger = get_logger(__name__)
console = Console()


def display_global_settings():
    """Display global settings in a table format."""
    config = get_config()

    table = Table(title="[bold cyan]Global Settings[/bold cyan]", show_header=True, header_style="bold magenta")
    table.add_column("Setting", style="yellow", width=25)
    table.add_column("Value", style="green", width=40)
    table.add_column("Description", style="dim", width=30)

    # Core settings
    table.add_row("Vector Store", str(config.vector_store_provider.value), "Vector database provider")
    table.add_row("Embedding Model", config.embedding_model, "AI model for embeddings")
    table.add_row("Data Directory", str(config.data_dir), "Local data storage path")
    table.add_row("Log Level", config.log_level, "Logging verbosity level")

    # Crawling settings
    table.add_row("Default Crawl Depth", str(config.crawl_depth), "Maximum link depth")
    table.add_row("Rate Limit", f"{config.rate_limit} req/s", "Request throttling")
    table.add_row("Chunk Size", str(config.chunk_size), "Text processing chunk size")
    table.add_row("Chunk Overlap", str(config.chunk_overlap), "Text chunk overlap")

    # Service URLs
    table.add_row("Qdrant URL", config.qdrant_url, "Vector database endpoint")
    table.add_row("Ollama URL", config.ollama_url, "Embedding service endpoint")
    table.add_row("MCP Port", str(config.mcp_port), "MCP server port")

    console.print(table)




@click.command()
@click.option(
    "--init",
    is_flag=True,
    help="Initialize DocBro configuration"
)
@click.option(
    "--uninstall",
    is_flag=True,
    help="Uninstall DocBro completely"
)
@click.option(
    "--reset",
    is_flag=True,
    help="Reset DocBro to fresh state"
)
@click.option(
    "--force",
    is_flag=True,
    help="Skip confirmation prompts"
)
@click.option(
    "--auto",
    is_flag=True,
    help="Use automatic mode with defaults"
)
@click.option(
    "--non-interactive",
    is_flag=True,
    help="Disable interactive prompts"
)
@click.option(
    "--vector-store",
    type=click.Choice(["sqlite_vec", "qdrant"]),
    help="Select vector store provider (with --init)"
)
@click.option(
    "--backup",
    is_flag=True,
    help="Create backup before uninstalling (with --uninstall)"
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Show what would be removed (with --uninstall)"
)
@click.option(
    "--preserve-data",
    is_flag=True,
    help="Keep user project data (with --uninstall or --reset)"
)
@click.pass_context
def setup(
    ctx: click.Context,
    init: bool,
    uninstall: bool,
    reset: bool,
    force: bool,
    auto: bool,
    non_interactive: bool,
    vector_store: Optional[str],
    backup: bool,
    dry_run: bool,
    preserve_data: bool
):
    """Unified setup command for DocBro configuration.

    This command consolidates all setup operations:
    - Initialize configuration (--init)
    - Uninstall DocBro (--uninstall)
    - Reset installation (--reset)
    - Interactive menu (no flags)

    Examples:
        docbro setup                           # Interactive menu
        docbro setup --init --auto             # Quick setup with defaults
        docbro setup --init --vector-store sqlite_vec
        docbro setup --uninstall --force       # Uninstall without confirmation
        docbro setup --reset --preserve-data   # Reset but keep projects
    """

    # Initialize router and orchestrator
    router = CommandRouter()
    orchestrator = SetupOrchestrator()

    try:
        # Route to appropriate operation
        operation = router.route_operation(
            init=init,
            uninstall=uninstall,
            reset=reset,
            force=force,
            auto=auto,
            non_interactive=non_interactive,
            vector_store=vector_store,
            backup=backup,
            dry_run=dry_run,
            preserve_data=preserve_data
        )

        # Execute the operation
        if operation.type == "init":
            console.print("[cyan]Initializing DocBro...[/cyan]")
            try:
                result = orchestrator.initialize(**operation.options)
            except RuntimeError as e:
                # Check if it's the "already initialized" error
                if "already initialized" in str(e).lower():
                    console.print("[yellow]ℹ DocBro is already initialized.[/yellow]")
                    console.print("[dim]Use 'docbro setup --init --force' to reinitialize.[/dim]")
                    ctx.exit(0)  # Exit gracefully
                else:
                    # Re-raise other runtime errors
                    raise

        elif operation.type == "uninstall":
            console.print("[yellow]Preparing to uninstall DocBro...[/yellow]")
            result = orchestrator.uninstall(**operation.options)

        elif operation.type == "reset":
            console.print("[yellow]Resetting DocBro installation...[/yellow]")
            result = orchestrator.reset(**operation.options)

        elif operation.type == "menu":
            # Launch interactive menu
            console.print("[cyan]Welcome to DocBro Setup[/cyan]")
            result = orchestrator.run_interactive_menu()

        else:
            raise ValueError(f"Unknown operation type: {operation.type}")

        # Display result
        if result.status == "completed":
            console.print(f"[green]✓ {operation.type.title()} completed successfully[/green]")

            # Display settings and help tables after successful init
            if operation.type == "init":
                console.print("\n")
                display_global_settings()
                console.print("\n")
                health_reporter = HealthReporter()
                help_output = health_reporter.display_command_guide()
                console.print(help_output)

        elif result.status == "cancelled":
            console.print("[yellow]Operation cancelled[/yellow]")
        elif result.status == "dry_run":
            console.print("[blue]Dry run completed - no changes made[/blue]")
        else:
            console.print(f"[red]Operation failed: {result.error_message}[/red]")
            ctx.exit(1)

    except ValueError as e:
        # Flag validation error
        console.print(f"[red]Error: {e}[/red]")
        console.print("\n[dim]Run 'docbro setup --help' for usage information[/dim]")
        ctx.exit(1)

    except click.exceptions.Exit:
        # Allow clean exits from nested code
        raise

    except Exception as e:
        logger.exception("Setup command failed")
        console.print(f"[red]Setup failed: {e}[/red]")
        ctx.exit(1)