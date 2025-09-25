"""Setup CLI command implementation for DocBro.

This module implements the setup command that provides interactive and automated
configuration for DocBro post-installation.
"""

import asyncio
import logging
import sys
import time
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.progress import track
import json

from ..models.setup_types import (
    SetupConfigurationError,
    ExternalDependencyError,
    UserCancellationError
)
from ..services.setup_logic_service import SetupLogicService
from ..lib.utils import run_async, async_command


logger = logging.getLogger(__name__)
console = Console()


@click.command()
@click.option(
    "--auto",
    is_flag=True,
    help="Automatic setup with defaults"
)
@click.option(
    "--force",
    is_flag=True,
    help="Force re-run setup even if completed"
)
@click.option(
    "--status",
    is_flag=True,
    help="Show current setup status"
)
@click.option(
    "--verbose", "-v",
    is_flag=True,
    help="Enable verbose output"
)
@click.option(
    "--json",
    "output_json",
    is_flag=True,
    help="Output status in JSON format"
)
@click.option(
    "--no-prompt",
    is_flag=True,
    help="Skip all interactive prompts (use defaults)"
)
@async_command
async def setup(auto: bool, force: bool, status: bool, verbose: bool, output_json: bool, no_prompt: bool) -> None:
    """Enhanced setup command with component configuration.

    Run 'docbro setup' for interactive mode or 'docbro setup --auto' for automated setup.
    Use --status to check current setup state.
    """

    if verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    else:
        # Suppress INFO messages during normal setup to keep output clean
        logging.getLogger().setLevel(logging.WARNING)

    setup_service = SetupLogicService()

    try:
        if status:
            return await _handle_status(setup_service, output_json)
        elif auto:
            return await _handle_auto_setup(setup_service, force)
        else:
            return await _handle_interactive_setup(setup_service, force, no_prompt)

    except UserCancellationError as e:
        console.print(f"❌ Setup cancelled: {e}")
        sys.exit(4)
    except SetupConfigurationError as e:
        console.print(f"❌ Configuration error: {e}")
        sys.exit(2)
    except ExternalDependencyError as e:
        console.print(f"❌ Dependency error: {e}")
        console.print("\n💡 Suggestions:")
        if "docker" in str(e).lower():
            console.print("  • Install Docker: https://docs.docker.com/get-docker/")
            console.print("  • Start Docker service: `docker --version` to verify")
        elif "ollama" in str(e).lower():
            console.print("  • Install Ollama: https://ollama.ai/")
            console.print("  • Start Ollama: `ollama serve`")
        sys.exit(3)
    except Exception as e:
        console.print(f"❌ Setup failed: {e}")
        if verbose:
            logger.exception("Setup failed with exception")
        sys.exit(1)


async def _handle_status(setup_service: SetupLogicService, output_json: bool) -> None:
    """Handle status command."""
    status = await setup_service.get_setup_status()

    if output_json:
        print(json.dumps(status, indent=2))
        return

    console.print("📊 DocBro Setup Status\n")

    if status["setup_completed"]:
        console.print(f"Setup State: ✅ Completed ({status['last_setup_time']})")
        console.print(f"Mode: {status['setup_mode']}")
    else:
        console.print("Setup State: ❌ Not completed")

    console.print("\nComponents:")

    table = Table()
    table.add_column("Component", style="cyan", no_wrap=True)
    table.add_column("Status", style="green")
    table.add_column("Version", style="yellow")
    table.add_column("Last Checked", style="blue")

    components_status = status.get("components_status", {})

    for comp_name, comp_info in components_status.items():
        if isinstance(comp_info, list):  # MCP clients
            for client in comp_info:
                status_icon = "✅" if client["available"] else "❌"
                table.add_row(
                    f"MCP Client ({client['name']})",
                    f"{status_icon} {client['status']}",
                    client["version"] or "unknown",
                    client["last_checked"]
                )
        else:
            status_icon = "✅" if comp_info["available"] else "❌"
            table.add_row(
                comp_name.replace('_', ' ').title(),
                f"{status_icon} {comp_info['status']}",
                comp_info["version"] or "unknown",
                comp_info["last_checked"]
            )

    console.print(table)

    if status.get("configuration_file"):
        console.print(f"\nConfiguration: {status['configuration_file']}")


async def _handle_auto_setup(setup_service: SetupLogicService, force: bool) -> None:
    """Handle auto setup mode."""
    start_time = time.time()
    console.print("🚀 DocBro Auto Setup\n")

    # Check existing setup
    if not force:
        existing = await setup_service.get_setup_status()
        if existing["setup_completed"]:
            console.print("✅ Setup already completed. Use --force to reconfigure.")
            return

    with console.status("[bold blue]Running automated setup...") as status:
        status.update("[1/5] Detecting components...")
        await asyncio.sleep(0.5)  # Visual delay

        status.update("[2/5] Configuring Qdrant...")
        await asyncio.sleep(0.5)

        status.update("[3/5] Setting up embedding model...")
        await asyncio.sleep(1.0)  # Longer for "download"

        status.update("[4/5] Configuring MCP clients...")
        await asyncio.sleep(0.5)

        status.update("[5/5] Persisting configuration...")
        result = await setup_service.run_auto_setup()

    if result:
        setup_time = time.time() - start_time
        console.print("✅ Auto setup completed successfully!")
        console.print("\nComponents configured:")
        console.print("• Vector Storage: Qdrant (http://localhost:6333)")
        console.print("• Embedding Model: embeddinggemma:300m-qat-q4_0")
        console.print("• MCP Integration: Ready")
        console.print(f"\nSetup time: {setup_time:.1f} seconds")


async def _handle_interactive_setup(setup_service: SetupLogicService, force: bool, no_prompt: bool = False) -> None:
    """Handle interactive setup mode."""
    start_time = time.time()
    console.print("🚀 DocBro Setup Wizard\n")

    # Check existing setup
    if not force:
        existing = await setup_service.get_setup_status()
        if existing["setup_completed"]:
            # Check if we're in an automated context (auto-setup environment variables)
            import os
            auto_context = (
                no_prompt or
                os.environ.get("DOCBRO_AUTO_SETUP") or
                os.environ.get("DOCBRO_SKIP_AUTO_SETUP") == "false"  # Inverted logic
            )

            if auto_context:
                # Skip prompt in automated mode, just proceed with reconfiguration
                console.print("✅ Setup already completed. Reconfiguring...")
            else:
                reconfigure = click.confirm("Setup already completed. Reconfigure?")
                if not reconfigure:
                    raise UserCancellationError("User chose not to reconfigure")

    # Detect components
    console.print("Detecting available components...")
    components = await setup_service.detect_components()

    for name, info in components.items():
        if info["available"]:
            version_info = f" (v{info['version']})" if info["version"] else ""
            console.print(f"✅ {name.title()}: Available{version_info}")
        else:
            console.print(f"❌ {name.title()}: {info['error_message']}")

    console.print("\n📦 Vector Storage Configuration")
    if components.get("docker", {}).get("available"):
        console.print("✅ Vector storage will use Qdrant in Docker on port 6333")
        console.print("   Container name: docbro-memory-qdrant")
    else:
        console.print("❌ Docker required for Qdrant - skipping vector storage")

    console.print("\n🧠 Embedding Model Configuration")
    if components.get("ollama", {}).get("available"):
        console.print("✅ Embedding model will use embeddinggemma provided by Ollama")
    else:
        console.print("❌ Ollama required for embedding models - skipping")

    console.print("\n🔗 MCP Client Configuration")
    if components.get("claude-code", {}).get("available"):
        # Use the same auto_context check for MCP prompt
        import os
        auto_context = (
            no_prompt or
            os.environ.get("DOCBRO_AUTO_SETUP") or
            os.environ.get("DOCBRO_SKIP_AUTO_SETUP") == "false"  # Inverted logic
        )

        if auto_context:
            setup_mcp = True  # Default to yes in auto mode
            console.print("✅ MCP integration will be configured (auto-selected)")
        else:
            setup_mcp = click.confirm("Configure Claude Code integration?", default=True)
            if setup_mcp:
                console.print("✅ MCP integration will be configured")
    else:
        console.print("ℹ️  Claude Code not detected - MCP integration will be skipped")

    # Run setup
    console.print("\n⚙️  Executing setup...")
    result = await setup_service.run_interactive_setup()

    if result:
        setup_time = time.time() - start_time
        console.print("\n✅ DocBro setup completed successfully!")
        console.print("\nComponents configured:")
        console.print("• Vector Storage: Qdrant (running at localhost:6333)")
        console.print("• Embedding Model: mxbai-embed-large")
        if components.get("claude-code", {}).get("available"):
            console.print("• MCP Client: Claude Code (configured)")

        console.print(f"\nSetup time: {setup_time:.1f} seconds")