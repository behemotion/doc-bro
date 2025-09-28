"""Upload command for DocBro CLI."""

import asyncio
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

# Optional uvloop for better performance
try:
    import uvloop
    UVLOOP_AVAILABLE = True
except ImportError:
    UVLOOP_AVAILABLE = False

import logging

from src.cli.utils.navigation import ArrowNavigator, NavigationChoice
from src.logic.projects.models.upload import UploadSource, UploadSourceType

logger = logging.getLogger(__name__)


def run_async(coro):
    """Run async coroutine in sync context."""
    if UVLOOP_AVAILABLE:
        try:
            uvloop.install()
        except Exception:
            pass

    return asyncio.run(coro)


def get_app():
    """Get or create global app instance."""
    from src.cli.main import get_app as main_get_app
    return main_get_app()


# CLI Error Messages
CLI_ERROR_MESSAGES = {
    "project_not_found": "Project '{name}' not found.",
    "invalid_source_type": "Invalid source type '{type}'. Must be one of: {valid_types}",
    "authentication_failed": "Authentication failed for {source}. Please check credentials.",
    "network_timeout": "Network timeout while connecting to {source}. Retrying ({attempt}/3)...",
    "file_too_large": "File '{filename}' ({size}) exceeds maximum size limit ({limit}).",
    "invalid_format": "File '{filename}' has unsupported format '{format}' for {project_type} projects.",
    "permission_denied": "Permission denied accessing '{path}'. Check file permissions.",
    "disk_space_low": "Insufficient disk space. Need {required}, have {available}."
}


@click.group(name="upload", invoke_without_command=True)
@click.pass_context
def upload(ctx: click.Context):
    """Upload files to documentation projects.

    Run without arguments to launch interactive menu:
    docbro upload

    Or use the command directly:
    docbro upload files --project my-docs --source /path/to/files --type local
    """
    if ctx.invoked_subcommand is None:
        # Launch interactive menu
        run_async(interactive_upload_menu())


@upload.command(name="files")
@click.option("--project", "-p", required=True, help="Target project name")
@click.option("--source", "-sr", required=True, help="Source path/URL")
@click.option("--type", "-t", "source_type",
              type=click.Choice(['local', 'ftp', 'sftp', 'smb', 'http', 'https'], case_sensitive=False),
              required=True, help="Source type")
@click.option("--username", "-u", help="Authentication username")
@click.option("--recursive", "-r", is_flag=True, help="Recursive directory upload")
@click.option("--exclude", "-e", multiple=True, help="Exclude patterns")
@click.option("--dry-run", "-dr", is_flag=True, help="Show what would be uploaded")
@click.option("--overwrite", "-o",
              type=click.Choice(['ask', 'skip', 'overwrite'], case_sensitive=False),
              default='ask', help="Conflict resolution strategy")
@click.option("--progress", "-pr", is_flag=True, default=True, help="Show progress bar")
def upload_files(project: str, source: str, source_type: str, username: str | None,
                 recursive: bool, exclude: list[str], dry_run: bool, overwrite: str, progress: bool):
    """Upload files to a project from various sources."""
    run_async(_upload_files_impl(project, source, source_type, username, recursive,
                                 list(exclude), dry_run, overwrite, progress))


@upload.command(name="status")
@click.option("--project", "-p", help="Filter by project")
@click.option("--operation", "-op", help="Specific operation ID")
@click.option("--active", "-a", is_flag=True, help="Show only active uploads")
def upload_status(project: str | None, operation: str | None, active: bool):
    """Show upload operation status."""
    run_async(_upload_status_impl(project, operation, active))


# Interactive menu functions

async def interactive_upload_menu(project_name: str | None = None):
    """Show interactive upload menu with source type selection."""
    console = Console()
    navigator = ArrowNavigator()

    try:
        app = get_app()
        project_manager = app.project_manager

        # Get target project
        if not project_name:
            # Select project interactively
            projects = await project_manager.list_projects()
            if not projects:
                console.print("[yellow]No projects found. Create a project first.[/yellow]")
                return

            project_choices = [
                NavigationChoice(
                    p.name,
                    f"{p.name} ({p.type.value})",
                    f"Status: {p.status.value}"
                )
                for p in projects
            ]

            project_name = await navigator.navigate_menu(
                "Select target project:",
                project_choices
            )

            if not project_name:
                return

        # Get project details
        project = await project_manager.get_project(project_name)
        if not project:
            console.print(f"[red]Project '{project_name}' not found[/red]")
            return

        console.clear()
        console.print(Panel.fit(
            f"[bold blue]Upload Files to Project[/bold blue]\n"
            f"Project: {project.name} ({project.type.value})",
            border_style="blue"
        ))

        # Select upload source type
        source_choices = [
            NavigationChoice("local", "Local Files", "Upload files from local filesystem"),
            NavigationChoice("http", "HTTP/HTTPS", "Download files from web URLs"),
            NavigationChoice("ftp", "FTP", "Upload from FTP server"),
            NavigationChoice("sftp", "SFTP/SSH", "Upload from SFTP server"),
            NavigationChoice("smb", "SMB/CIFS", "Upload from Windows network share")
        ]

        source_type = await navigator.navigate_menu(
            "Select upload source type:",
            source_choices
        )

        if not source_type:
            return

        # Handle source type specific configuration
        if source_type == "local":
            await _interactive_local_upload(project)
        elif source_type in ["http", "https"]:
            await _interactive_http_upload(project)
        elif source_type == "ftp":
            await _interactive_ftp_upload(project)
        elif source_type == "sftp":
            await _interactive_sftp_upload(project)
        elif source_type == "smb":
            await _interactive_smb_upload(project)

    except KeyboardInterrupt:
        console.print("\n[yellow]Upload cancelled by user[/yellow]")
    except Exception as e:
        logger.error(f"Error in interactive upload menu: {e}")
        console.print(f"[red]Error: {str(e)}[/red]")


async def _interactive_local_upload(project):
    """Interactive local file upload."""
    console = Console()
    navigator = ArrowNavigator()

    try:
        # Get source path
        console.print("\n[cyan]Local File Upload[/cyan]")
        source_path = console.input("Source path (file or directory): ").strip()

        if not source_path:
            console.print("[red]Source path is required[/red]")
            return

        # Check if path exists
        path = Path(source_path)
        if not path.exists():
            console.print(f"[red]Path not found: {source_path}[/red]")
            return

        # Configure options
        recursive = False
        if path.is_dir():
            recursive = await navigator.confirm_choice(
                "Upload directory contents recursively?",
                default=True
            )

        exclude_patterns = []
        add_exclusions = await navigator.confirm_choice(
            "Add exclusion patterns?",
            default=False
        )

        if add_exclusions:
            console.print("Enter exclusion patterns (one per line, empty line to finish):")
            while True:
                pattern = console.input("Pattern: ").strip()
                if not pattern:
                    break
                exclude_patterns.append(pattern)

        # Dry run option
        dry_run = await navigator.confirm_choice(
            "Perform dry run first (show what would be uploaded)?",
            default=True
        )

        # Execute upload
        await _upload_files_impl(
            project.name, source_path, "local", None,
            recursive, exclude_patterns, dry_run, "ask", True
        )

        if dry_run:
            proceed = await navigator.confirm_choice(
                "Proceed with actual upload?",
                default=True
            )
            if proceed:
                await _upload_files_impl(
                    project.name, source_path, "local", None,
                    recursive, exclude_patterns, False, "ask", True
                )

    except Exception as e:
        logger.error(f"Error in local upload: {e}")
        console.print(f"[red]Error: {str(e)}[/red]")


async def _interactive_http_upload(project):
    """Interactive HTTP/HTTPS download."""
    console = Console()

    try:
        console.print("\n[cyan]HTTP/HTTPS Download[/cyan]")
        url = console.input("URL to download: ").strip()

        if not url:
            console.print("[red]URL is required[/red]")
            return

        # Determine source type based on URL
        source_type = "https" if url.startswith("https://") else "http"

        # Execute download
        await _upload_files_impl(
            project.name, url, source_type, None,
            False, [], False, "ask", True
        )

    except Exception as e:
        logger.error(f"Error in HTTP upload: {e}")
        console.print(f"[red]Error: {str(e)}[/red]")


async def _interactive_ftp_upload(project):
    """Interactive FTP upload."""
    console = Console()

    try:
        console.print("\n[cyan]FTP Upload[/cyan]")
        host = console.input("FTP host: ").strip()
        if not host:
            console.print("[red]FTP host is required[/red]")
            return

        username = console.input("Username: ").strip()
        from getpass import getpass
        password = getpass("Password: ")

        path = console.input("Remote path: ").strip() or "/"

        # Construct FTP URL
        if username and password:
            source_url = f"ftp://{username}:{password}@{host}{path}"
        else:
            source_url = f"ftp://{host}{path}"

        await _upload_files_impl(
            project.name, source_url, "ftp", username,
            True, [], False, "ask", True
        )

    except Exception as e:
        logger.error(f"Error in FTP upload: {e}")
        console.print(f"[red]Error: {str(e)}[/red]")


async def _interactive_sftp_upload(project):
    """Interactive SFTP upload."""
    console = Console()
    navigator = ArrowNavigator()

    try:
        console.print("\n[cyan]SFTP Upload[/cyan]")
        host = console.input("SFTP host: ").strip()
        if not host:
            console.print("[red]SFTP host is required[/red]")
            return

        username = console.input("Username: ").strip()

        # Authentication method
        auth_choices = [
            NavigationChoice("password", "Password", "Use password authentication"),
            NavigationChoice("key", "SSH Key", "Use SSH key authentication")
        ]

        auth_method = await navigator.navigate_menu(
            "Select authentication method:",
            auth_choices
        )

        if auth_method == "password":
            from getpass import getpass
            password = getpass("Password: ")
        else:
            key_path = console.input("SSH key path (default: ~/.ssh/id_rsa): ").strip()
            if not key_path:
                key_path = "~/.ssh/id_rsa"

        path = console.input("Remote path: ").strip() or "/"

        # Construct SFTP URL
        source_url = f"sftp://{username}@{host}{path}"

        await _upload_files_impl(
            project.name, source_url, "sftp", username,
            True, [], False, "ask", True
        )

    except Exception as e:
        logger.error(f"Error in SFTP upload: {e}")
        console.print(f"[red]Error: {str(e)}[/red]")


async def _interactive_smb_upload(project):
    """Interactive SMB upload."""
    console = Console()

    try:
        console.print("\n[cyan]SMB/CIFS Upload[/cyan]")
        host = console.input("SMB host: ").strip()
        if not host:
            console.print("[red]SMB host is required[/red]")
            return

        share = console.input("Share name: ").strip()
        if not share:
            console.print("[red]Share name is required[/red]")
            return

        username = console.input("Username: ").strip()
        from getpass import getpass
        password = getpass("Password: ")

        path = console.input("Remote path: ").strip() or "/"

        # Construct SMB URL
        source_url = f"smb://{username}:{password}@{host}/{share}{path}"

        await _upload_files_impl(
            project.name, source_url, "smb", username,
            True, [], False, "ask", True
        )

    except Exception as e:
        logger.error(f"Error in SMB upload: {e}")
        console.print(f"[red]Error: {str(e)}[/red]")


# Implementation functions

async def _upload_files_impl(project: str, source: str, source_type: str,
                             username: str | None, recursive: bool,
                             exclude: list[str], dry_run: bool, overwrite: str, progress: bool):
    """Implementation of file upload."""
    console = Console()

    try:
        app = get_app()
        project_manager = app.project_manager
        upload_manager = app.upload_manager

        # Get project
        proj = await project_manager.get_project(project)
        if not proj:
            error_msg = CLI_ERROR_MESSAGES["project_not_found"].format(name=project)
            console.print(f"[red]Error: {error_msg}[/red]")
            return

        # Validate source type
        try:
            upload_source_type = UploadSourceType(source_type.lower())
        except ValueError:
            valid_types = [t.value for t in UploadSourceType]
            error_msg = CLI_ERROR_MESSAGES["invalid_source_type"].format(
                type=source_type, valid_types=", ".join(valid_types)
            )
            console.print(f"[red]Error: {error_msg}[/red]")
            return

        # Create upload source
        upload_source = UploadSource(
            type=upload_source_type,
            location=source,
            credentials={"username": username} if username else None,
            connection_params={
                "recursive": recursive,
                "exclude_patterns": exclude,
                "overwrite_policy": overwrite
            }
        )

        # Validate upload before proceeding
        if not dry_run:
            console.print("Validating upload source...")
            validation = await upload_manager.validate_upload(proj, upload_source)
            if not validation.valid:
                console.print("[red]Upload validation failed:[/red]")
                for error in validation.errors:
                    console.print(f"  • {error}")
                return

            if validation.warnings:
                console.print("[yellow]Warnings:[/yellow]")
                for warning in validation.warnings:
                    console.print(f"  • {warning}")

        # Set up progress callback if enabled
        progress_callback = None
        if progress:
            from src.logic.projects.utils.progress_reporter import (
                UploadProgressReporter,
            )
            progress_reporter = UploadProgressReporter(console)

            async def progress_callback(update):
                await progress_reporter.update_progress(update)

        # Execute upload
        operation_id = f"upload_{project}_{int(asyncio.get_event_loop().time())}"

        if dry_run:
            console.print("\n[yellow]DRY RUN - Upload Preview[/yellow]")
            console.print(f"Project: {project}")
            console.print(f"Source: {source}")
            console.print(f"Type: {source_type}")
            console.print(f"Recursive: {recursive}")
            if exclude:
                console.print(f"Exclusions: {', '.join(exclude)}")
            console.print("\n[yellow]Files that would be uploaded:[/yellow]")

            # This would be implemented in the upload manager to show file list
            # For now, just show the configuration
            console.print("  (File list would be shown here)")
        else:
            with console.status(f"Uploading files to project '{project}'..."):
                result = await upload_manager.upload_files(
                    proj, upload_source, progress_callback
                )

            if result.success:
                console.print("[green]✓[/green] Upload completed successfully!")
                console.print(f"  Files processed: {result.files_processed}/{result.files_total}")
                console.print(f"  Data transferred: {_format_bytes(result.bytes_processed)}")
            else:
                console.print("[red]✗[/red] Upload failed!")
                for error in result.errors:
                    console.print(f"  Error: {error}")

            if result.warnings:
                console.print("[yellow]Warnings:[/yellow]")
                for warning in result.warnings:
                    console.print(f"  • {warning}")

    except Exception as e:
        logger.error(f"Error uploading files: {e}")
        console.print(f"[red]Error uploading files: {str(e)}[/red]")


async def _upload_status_impl(project: str | None, operation: str | None, active: bool):
    """Implementation of upload status."""
    console = Console()

    try:
        app = get_app()
        upload_manager = app.upload_manager

        if operation:
            # Show specific operation status
            status = await upload_manager.get_upload_status(operation)
            if status:
                console.print(f"\n[bold cyan]Upload Operation: {operation}[/bold cyan]")
                console.print(f"Stage: {status.stage}")
                console.print(f"Files: {status.files_processed}/{status.files_total}")
                console.print(f"Data: {_format_bytes(status.bytes_processed)}/{_format_bytes(status.bytes_total)}")
                if status.current_file:
                    console.print(f"Current: {status.current_file}")
            else:
                console.print(f"[yellow]Operation '{operation}' not found[/yellow]")
        else:
            # Show all operations (this would be implemented in upload manager)
            console.print("[yellow]Upload status tracking not fully implemented yet[/yellow]")

    except Exception as e:
        logger.error(f"Error getting upload status: {e}")
        console.print(f"[red]Error getting upload status: {str(e)}[/red]")


def _format_bytes(bytes_count: int) -> str:
    """Format bytes for human-readable display."""
    if bytes_count == 0:
        return "0 B"

    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_count < 1024.0:
            return f"{bytes_count:.1f} {unit}"
        bytes_count /= 1024.0
    return f"{bytes_count:.1f} PB"
