"""Main CLI entry point for DocBro - Simplified version with commands in separate modules."""

import asyncio
import sys
from pathlib import Path
from typing import Optional, Any, List

import click
from rich.console import Console

# Optional uvloop for better performance
try:
    import uvloop
    UVLOOP_AVAILABLE = True
except ImportError:
    UVLOOP_AVAILABLE = False

from src.core.config import DocBroConfig
from src.core.lib_logger import setup_logging, get_component_logger
from src.services.database import DatabaseManager
from src.services.vector_store import VectorStoreService
from src.services.embeddings import EmbeddingService
from src.services.rag import RAGSearchService
from src.logic.crawler.core.crawler import DocumentationCrawler
from src.version import __version__


class AliasedGroup(click.Group):
    """Click group that supports command aliases."""

    def get_command(self, ctx, cmd_name):
        """Get command by name or alias."""
        # Define aliases
        aliases = {
            'add': 'create',
            'new': 'create',
            'delete': 'remove',
            'erase': 'remove',
            'rm': 'remove',
            'ls': 'list'
        }

        # Resolve alias to actual command name
        cmd_name = aliases.get(cmd_name, cmd_name)

        # Get the actual command
        return super().get_command(ctx, cmd_name)

    def list_commands(self, ctx):
        """List commands in alphabetical order."""
        commands = super().list_commands(ctx)
        return sorted(commands)


class DocBroApp:
    """Main DocBro application."""

    def __init__(self, config: Optional[DocBroConfig] = None):
        """Initialize DocBro application."""
        self.config = config or DocBroConfig()
        self.console = Console()
        self.logger = None

        # Services
        self.db_manager: Optional[DatabaseManager] = None
        self.vector_store: Optional[VectorStoreService] = None
        self.embedding_service: Optional[EmbeddingService] = None
        self.rag_service: Optional[RAGSearchService] = None
        self.crawler: Optional[DocumentationCrawler] = None

        self._initialized = False

    async def initialize(self, debug: bool = False) -> None:
        """Initialize all services."""
        if self._initialized:
            return

        try:
            # Setup logging with debug override
            if debug:
                self.config.debug = True
                self.config.log_level = "DEBUG"
            setup_logging(self.config)
            self.logger = get_component_logger("cli")

            # Initialize services
            self.db_manager = DatabaseManager(self.config)
            await self.db_manager.initialize()

            # Use factory to create appropriate vector store based on settings
            from src.services.vector_store_factory import VectorStoreFactory
            try:
                self.vector_store = VectorStoreFactory.create_vector_store(self.config)
                await self.vector_store.initialize()
            except Exception as e:
                # Get current provider and provide helpful suggestion
                current_provider = VectorStoreFactory.get_current_provider()
                suggestion = VectorStoreFactory.get_fallback_suggestion(current_provider)

                error_msg = f"Failed to initialize {current_provider.value} vector store: {e}\n\n{suggestion}"
                self.logger.error("Vector store initialization failed", extra={
                    "provider": current_provider.value,
                    "error": str(e)
                })
                raise RuntimeError(error_msg)

            self.embedding_service = EmbeddingService(self.config)
            await self.embedding_service.initialize()

            self.rag_service = RAGSearchService(
                self.vector_store,
                self.embedding_service,
                self.config
            )

            self.crawler = DocumentationCrawler(self.db_manager, self.config)
            await self.crawler.initialize()

            self._initialized = True
            self.logger.info("DocBro application initialized")

        except Exception as e:
            self.console.print(f"[red]Failed to initialize DocBro: {e}[/red]")
            if self.logger:
                self.logger.error("Initialization failed", extra={"error": str(e)})
            raise

    async def cleanup(self) -> None:
        """Clean up all services."""
        if self.crawler:
            await self.crawler.cleanup()
        if self.embedding_service:
            await self.embedding_service.cleanup()
        if self.vector_store:
            await self.vector_store.cleanup()
        if self.db_manager:
            await self.db_manager.cleanup()

        self._initialized = False
        if self.logger:
            self.logger.info("DocBro application cleaned up")


# Global app instance for CLI
app: Optional[DocBroApp] = None


def get_app() -> DocBroApp:
    """Get or create global app instance."""
    global app
    if app is None:
        app = DocBroApp()
    return app


def run_async(coro):
    """Run async coroutine in sync context."""
    if UVLOOP_AVAILABLE:
        try:
            uvloop.install()
        except Exception:
            pass

    return asyncio.run(coro)


def _is_first_time_installation() -> bool:
    """Check if this is a first-time installation."""
    try:
        from src.services.config import ConfigService
        config_service = ConfigService()

        # Check for existing installation context
        context = config_service.load_installation_context()
        if context:
            return False

        # Check for any existing configuration
        config_dir = config_service.config_dir
        if config_dir.exists():
            # Look for any configuration files
            config_files = list(config_dir.glob("*.json"))
            if config_files:
                return False

        return True
    except Exception:
        # If we can't determine, assume first time for safety
        return True


def _detect_uv_installation() -> bool:
    """Detect if this is running from a UV tool installation."""
    import os
    import sys
    from pathlib import Path

    # Check for UV environment variables
    if "UV_TOOL_DIR" in os.environ or "UVX_ROOT" in os.environ:
        return True

    # Check if running from UV virtual environment
    current_executable = Path(sys.executable)
    if "uv" in str(current_executable).lower():
        return True

    # Check if docbro is in a UV-managed location
    try:
        import shutil
        docbro_path = shutil.which("docbro")
        if docbro_path:
            path_str = str(Path(docbro_path))
            if ".local" in path_str and "uv" in path_str.lower():
                return True
    except Exception:
        pass

    return False


def _should_run_auto_setup() -> bool:
    """Determine if auto-setup should run."""
    import os
    # Check if explicitly disabled
    if os.environ.get("DOCBRO_SKIP_AUTO_SETUP", "").lower() in ["1", "true"]:
        return False

    return _is_first_time_installation() and _detect_uv_installation()


@click.group(cls=AliasedGroup, invoke_without_command=True)
@click.version_option(__version__, "--version", "-v", help="Show version and exit")
@click.option("--config-file", type=click.Path(exists=True), help="Configuration file path")
@click.option("--debug", is_flag=True, help="Enable debug output")
@click.option("--quiet", "-q", is_flag=True, help="Suppress non-essential output")
@click.option("--json", is_flag=True, help="Output in JSON format")
@click.option("--no-color", is_flag=True, help="Disable colored output")
@click.option("--no-progress", is_flag=True, help="Disable progress indicators")
@click.option("--skip-auto-setup", is_flag=True, help="Skip automatic setup for first-time installations")
@click.pass_context
def main(ctx: click.Context, config_file: Optional[str], debug: bool, quiet: bool,
         json: bool, no_color: bool, no_progress: bool, skip_auto_setup: bool):
    """DocBro - Local documentation crawler and search tool with RAG capabilities.

    DocBro crawls documentation websites, stores them locally, and provides
    semantic search through an MCP server for AI assistants like Claude.

    Quick start:
      docbro create myproject -u "https://docs.example.com"
      docbro crawl myproject
      docbro serve

    For interactive setup:
      docbro setup

    Command aliases:
      create: add, new
      remove: delete, erase, rm
      list: ls
    """
    # Store context for commands
    ctx.ensure_object(dict)
    ctx.obj["debug"] = debug
    ctx.obj["quiet"] = quiet
    ctx.obj["json"] = json
    ctx.obj["no_color"] = no_color
    ctx.obj["no_progress"] = no_progress

    # Initialize app with config
    global app
    config = DocBroConfig()
    if config_file:
        # Load config from file if needed
        pass

    # Apply debug flag to config
    if debug:
        config.debug = True
        config.log_level = "DEBUG"

    app = DocBroApp(config)

    # If no command specified, show help or run auto-setup
    if ctx.invoked_subcommand is None:
        console = Console()

        # Check for auto-setup on first installation
        if not skip_auto_setup and _should_run_auto_setup():
            console.print("🚀 [bold cyan]Welcome to DocBro![/bold cyan]")
            console.print("This appears to be your first time running DocBro.")
            console.print("Starting automatic setup...\n")

            async def run_auto_setup():
                from src.services.installation_wizard import InstallationWizardService
                from src.models.installation import InstallationRequest

                wizard_service = InstallationWizardService()
                request = InstallationRequest(
                    auto_mode=True,
                    force_reinstall=False
                )

                try:
                    result = await wizard_service.run_installation(request)
                    if result.success:
                        console.print(f"\n✅ [bold green]Setup completed successfully![/bold green]")
                        console.print("\n[cyan]Quick start:[/cyan]")
                        console.print("  1. Create project: [cyan]docbro create myproject -u \"URL\"[/cyan]")
                        console.print("  2. Crawl docs:    [cyan]docbro crawl myproject[/cyan]")
                        console.print("  3. Start server:  [cyan]docbro serve[/cyan]")
                        console.print("\n[dim]For more options: docbro --help[/dim]")
                    else:
                        console.print(f"\n❌ Setup failed: {result.error}")
                        console.print("💡 Try running: [cyan]docbro setup[/cyan] for manual setup")
                except Exception as e:
                    console.print(f"\n❌ Setup error: {e}")
                    console.print("💡 Try running: [cyan]docbro setup[/cyan] for manual setup")

            run_async(run_auto_setup())
            ctx.exit(0)

        # Show concise help
        console.print(f"DocBro v{__version__} - Documentation Crawler & Search Tool\n")
        console.print("[cyan]Common commands:[/cyan]")
        console.print("  docbro setup                  Interactive setup wizard")
        console.print("  docbro create <name> -u URL   Create a project")
        console.print("  docbro crawl <name>           Crawl documentation")
        console.print("  docbro serve                  Start MCP server")
        console.print("  docbro list                   List all projects")
        console.print("  docbro health                 Check service health")
        console.print("  docbro --help                 Show all commands")
        ctx.exit(0)


# Import and register all commands
from src.cli.commands.create import create
from src.cli.commands.list import list_command
from src.cli.commands.crawl import crawl
from src.cli.commands.remove import remove
from src.cli.commands.serve import serve
from src.cli.commands.health import health
from src.cli.commands.setup import setup
from src.cli.commands.system_check import system_check
from src.cli.commands.services import services_group

# Add commands to main group
main.add_command(create)
main.add_command(list_command, name="list")
main.add_command(crawl)
main.add_command(remove)
main.add_command(serve)
main.add_command(health)
main.add_command(setup)
main.add_command(system_check, name="system-check")
main.add_command(services_group, name="services")

# Create an alias for backward compatibility with tests
cli = main

if __name__ == "__main__":
    main()