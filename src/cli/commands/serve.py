"""Serve command for DocBro CLI."""

import os

import click

# Optional uvloop for better performance
try:
    import uvloop
    UVLOOP_AVAILABLE = True
except ImportError:
    UVLOOP_AVAILABLE = False


def get_app():
    """Get or create global app instance."""
    from src.cli.main import get_app as main_get_app
    return main_get_app()


@click.command(name="serve")
@click.option("--host", default=None, help="Server host (auto-detected based on server type)")
@click.option("--port", default=None, type=int, help="Server port (auto-detected based on server type)")
@click.option("--foreground", "-f", is_flag=True, help="Run server in foreground")
@click.option("--status", is_flag=True, help="Check server status")
@click.option("--admin", is_flag=True, help="Start admin MCP server instead of read-only")
@click.pass_context
def serve(ctx: click.Context, host: str, port: int, foreground: bool, status: bool, admin: bool):
    """Start the MCP server for AI assistant integration.

    The MCP (Model Context Protocol) server exposes your documentation
    to AI assistants like Claude, enabling context-aware responses.

    \b
    SERVER TYPES:
      docbro serve                   # Read-only server (port 9383, all interfaces)
      docbro serve --admin           # Admin server (port 9384, localhost only)

    \b
    SERVER MODES:
      docbro serve                   # Start in background (recommended)
      docbro serve --foreground      # Run in foreground (for debugging)
      docbro serve --status          # Check if server is running

    \b
    CONFIGURATION:
      --admin          Start admin server instead of read-only
      --host HOST      Server bind address (auto-detected by server type)
      --port PORT      Server port (auto-detected by server type)
      -f, --foreground Run in foreground instead of background

    \b
    MCP INTEGRATION:
      READ-ONLY SERVER (default):
      - Project listing and search across documentation
      - Safe read-only access for AI assistants
      - Runs on port 9383, accessible from any interface

      ADMIN SERVER (--admin flag):
      - Full DocBro command execution capabilities
      - Project creation, removal, crawling operations
      - Runs on port 9384, localhost only for security

    \b
    EXAMPLES:
      docbro serve                   # Start read-only server (background)
      docbro serve --admin           # Start admin server (background)
      docbro serve -f                # Read-only server in foreground
      docbro serve --admin -f        # Admin server in foreground
      docbro serve --status          # Check server status
      docbro serve --port 8080       # Custom port (overrides default)

    \b
    CLIENT SETUP:
      Read-only server: http://localhost:9383
      Admin server: http://127.0.0.1:9384 (localhost only)
      Protocol: MCP (Model Context Protocol)

    \b
    SECURITY NOTES:
      - Admin server restricted to localhost (127.0.0.1) for security
      - Read-only server prevents any write operations
      - Use admin server only for trusted local AI assistants

    \b
    TROUBLESHOOTING:
      - Use --foreground to see real-time server logs
      - Check --status to verify server is responding
      - Ensure no other service is using the port
      - Run 'docbro health' to verify system components
    """
    import socket
    import asyncio

    from src.logic.mcp.models.server_type import McpServerType
    from src.logic.mcp.models.config import McpServerConfig
    from src.logic.mcp.core.orchestrator import ServerOrchestrator
    from src.logic.mcp.utils.port_manager import PortManager

    app = get_app()

    # Determine server type and configuration
    server_type = McpServerType.ADMIN if admin else McpServerType.READ_ONLY

    # Set host and port based on server type if not provided
    if host is None:
        host = server_type.default_host
    if port is None:
        port = server_type.default_port

    # Create server configuration
    try:
        server_config = McpServerConfig(
            server_type=server_type,
            host=host,
            port=port,
            enabled=True
        )
    except Exception as e:
        app.console.print(f"[red]✗[/red] Invalid configuration: {e}")
        raise click.ClickException(str(e))

    # Check server status if requested
    if status:
        try:
            # Try to connect to the server
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                if result == 0:
                    app.console.print(f"[green]✓[/green] {server_type.value.title()} MCP server is running on {host}:{port}")

                    # Try to get server info via health endpoint
                    try:
                        import httpx
                        response = httpx.get(f"http://{host}:{port}/mcp/v1/health", timeout=2)
                        if response.status_code == 200:
                            data = response.json()
                            if data.get('success'):
                                server_data = data.get('data', {})
                                app.console.print(f"  Server Type: {server_data.get('server_type', 'Unknown')}")
                                app.console.print(f"  Status: {server_data.get('status', 'Unknown')}")
                    except Exception:
                        pass
                else:
                    app.console.print(f"[yellow]⚠[/yellow] {server_type.value.title()} MCP server is not running on {host}:{port}")
                    cmd_hint = "docbro serve --admin" if admin else "docbro serve"
                    app.console.print(f"[dim]Start it with: {cmd_hint}[/dim]")
        except Exception as e:
            app.console.print(f"[red]✗[/red] Error checking server status: {e}")
        return

    # Initialize port manager and orchestrator
    port_manager = PortManager()
    orchestrator = ServerOrchestrator(port_manager)

    if foreground:
        # Run in foreground
        app.console.print(f"[green]Starting {server_type.value} MCP server on {host}:{port}...[/green]")
        app.console.print("[dim]Press Ctrl+C to stop[/dim]\n")
        app.console.print("[cyan]Server endpoints:[/cyan]")
        app.console.print(f"  MCP API:  {server_config.url}/mcp/v1/")
        app.console.print(f"  Health:   {server_config.url}/mcp/v1/health")
        if server_type == McpServerType.ADMIN:
            app.console.print("[yellow]  ⚠ Admin server - localhost only for security[/yellow]")
        app.console.print("")

        async def run_server():
            """Run server asynchronously."""
            try:
                success = await orchestrator.start_single_server(server_config)
                if not success:
                    raise RuntimeError("Failed to start server")

                # Keep running until interrupted
                while True:
                    await asyncio.sleep(1)
            except KeyboardInterrupt:
                app.console.print("\n[yellow]Server stopped[/yellow]")
            except Exception as e:
                app.console.print(f"[red]✗ Server error: {e}[/red]")
                raise
            finally:
                await orchestrator.stop_all_servers()

        try:
            if UVLOOP_AVAILABLE:
                uvloop.install()
            asyncio.run(run_server())
        except KeyboardInterrupt:
            pass
        except Exception as e:
            raise click.ClickException(str(e))
    else:
        # Check if server is already running
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.5)
                result = sock.connect_ex((host, port))
                if result == 0:
                    app.console.print(f"[yellow]⚠[/yellow] {server_type.value.title()} server already running on {host}:{port}")
                    cmd_hint = "docbro serve --admin --status" if admin else "docbro serve --status"
                    app.console.print(f"[dim]Use '{cmd_hint}' to check status[/dim]")
                    return
        except Exception:
            pass

        # Run in background
        app.console.print(f"[green]✅ Starting {server_type.value} MCP server on {host}:{port}[/green]")

        # Fork the process to run in background
        pid = os.fork()
        if pid == 0:
            # Child process - redirect stdout/stderr to suppress INFO messages
            with open(os.devnull, 'w') as devnull:
                os.dup2(devnull.fileno(), 1)  # stdout
                os.dup2(devnull.fileno(), 2)  # stderr

            async def run_background_server():
                """Run server in background."""
                try:
                    success = await orchestrator.start_single_server(server_config)
                    if success:
                        # Keep running until the process is killed
                        while True:
                            await asyncio.sleep(1)
                except Exception:
                    pass

            try:
                if UVLOOP_AVAILABLE:
                    uvloop.install()
                asyncio.run(run_background_server())
            except Exception:
                pass
        else:
            # Parent process - show status and helpful info
            app.console.print(f"[dim]Process ID: {pid}[/dim]")
            app.console.print("")
            app.console.print("[cyan]Server management:[/cyan]")
            app.console.print(f"  Stop server:   kill {pid}")
            status_cmd = "docbro serve --admin --status" if admin else "docbro serve --status"
            app.console.print(f"  Check status:  {status_cmd}")
            app.console.print("  View logs:     tail -f ~/.local/share/docbro/mcp_server.log")
            app.console.print("")
            app.console.print("[cyan]Connect from AI Assistant:[/cyan]")
            app.console.print(f"  Server URL: {server_config.url}")
            if server_type == McpServerType.ADMIN:
                app.console.print("  [yellow]⚠ Admin server - use only with trusted local assistants[/yellow]")
            app.console.print("  Add to your AI assistant's MCP settings for documentation access")
