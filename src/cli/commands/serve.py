"""Serve command for DocBro CLI."""

import os
import signal
import subprocess
from typing import Optional

import click
from rich.console import Console

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
@click.option("--host", default="0.0.0.0", help="Server host")
@click.option("--port", default=9382, type=int, help="Server port")
@click.option("--foreground", "-f", is_flag=True, help="Run server in foreground")
@click.option("--status", is_flag=True, help="Check server status")
@click.pass_context
def serve(ctx: click.Context, host: str, port: int, foreground: bool, status: bool):
    """Start the MCP server for AI assistant integration.

    The MCP (Model Context Protocol) server provides documentation access
    to AI assistants like Claude.

    Examples:
      docbro serve                   # Start server in background
      docbro serve --foreground      # Run in foreground (for debugging)
      docbro serve --port 8080       # Use custom port
      docbro serve --status          # Check if server is running
    """
    from src.services.mcp_server import run_mcp_server
    import subprocess
    import os
    import signal
    import socket

    app = get_app()

    # Check server status if requested
    if status:
        try:
            # Try to connect to the server
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(1)
                result = sock.connect_ex((host, port))
                if result == 0:
                    app.console.print(f"[green]✓[/green] MCP server is running on {host}:{port}")

                    # Try to get server info via health endpoint
                    try:
                        import httpx
                        response = httpx.get(f"http://{host}:{port}/health", timeout=2)
                        if response.status_code == 200:
                            data = response.json()
                            app.console.print(f"  Status: {data.get('status', 'Unknown')}")
                            if 'projects' in data:
                                app.console.print(f"  Projects: {data['projects']}")
                    except Exception:
                        pass
                else:
                    app.console.print(f"[yellow]⚠[/yellow] MCP server is not running on {host}:{port}")
                    app.console.print("[dim]Start it with: docbro serve[/dim]")
        except Exception as e:
            app.console.print(f"[red]✗[/red] Error checking server status: {e}")
        return

    if foreground:
        # Run in foreground (original behavior)
        app.console.print(f"[green]Starting MCP server on {host}:{port}...[/green]")
        app.console.print("[dim]Press Ctrl+C to stop[/dim]\n")
        app.console.print("[cyan]Server endpoints:[/cyan]")
        app.console.print(f"  REST API: http://{host}:{port}")
        app.console.print(f"  Health:   http://{host}:{port}/health")
        app.console.print(f"  Search:   http://{host}:{port}/search")
        app.console.print("")

        try:
            run_mcp_server(host=host, port=port, config=app.config)
        except KeyboardInterrupt:
            app.console.print("\n[yellow]Server stopped[/yellow]")
        except Exception as e:
            app.console.print(f"[red]✗ Server error: {e}[/red]")
            raise click.ClickException(str(e))
    else:
        # Check if server is already running
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
                sock.settimeout(0.5)
                result = sock.connect_ex((host, port))
                if result == 0:
                    app.console.print(f"[yellow]⚠[/yellow] Server already running on {host}:{port}")
                    app.console.print("[dim]Use 'docbro serve --status' to check status[/dim]")
                    return
        except Exception:
            pass

        # Run in background (default behavior)
        app.console.print(f"[green]✅ Starting MCP server on {host}:{port}[/green]")

        # Fork the process to run in background
        pid = os.fork()
        if pid == 0:
            # Child process - redirect stdout/stderr to suppress INFO messages
            with open(os.devnull, 'w') as devnull:
                os.dup2(devnull.fileno(), 1)  # stdout
                os.dup2(devnull.fileno(), 2)  # stderr

            try:
                run_mcp_server(host=host, port=port, config=app.config)
            except Exception:
                pass
        else:
            # Parent process - show status and helpful info
            app.console.print(f"[dim]Process ID: {pid}[/dim]")
            app.console.print("")
            app.console.print("[cyan]Server management:[/cyan]")
            app.console.print(f"  Stop server:   kill {pid}")
            app.console.print(f"  Check status:  docbro serve --status")
            app.console.print(f"  View logs:     tail -f ~/.local/share/docbro/mcp_server.log")
            app.console.print("")
            app.console.print("[cyan]Connect from Claude:[/cyan]")
            app.console.print(f"  Server URL: http://{host}:{port}")
            app.console.print("  Add to Claude's MCP settings for documentation access")