"""Uninstall command for DocBro CLI."""

import sys
import asyncio
from pathlib import Path
from typing import Optional
import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TaskProgressColumn
from rich.panel import Panel
from rich.prompt import Confirm
from src.models.uninstall_config import UninstallConfig
from src.services.component_detection import ComponentDetectionService
from src.services.uninstall_service import UninstallService
from src.services.backup_service import BackupService
from src.core.lib_logger import get_logger

logger = get_logger(__name__)
console = Console()


def is_docbro_installed() -> bool:
    """Check if DocBro is installed on the system."""
    # Check for any DocBro directories or Docker containers
    paths_to_check = [
        Path.home() / '.config' / 'docbro',
        Path.home() / '.local' / 'share' / 'docbro',
    ]

    for path in paths_to_check:
        if path.exists():
            return True

    # Check if package is installed
    try:
        import subprocess
        result = subprocess.run(
            ['uv', 'tool', 'list'],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and 'docbro' in result.stdout.lower():
            return True
    except:
        pass

    return False


async def detect_components():
    """Detect all DocBro components on the system."""
    service = ComponentDetectionService()
    return await service.detect_all_components()


async def create_backup(components, path: Optional[Path] = None):
    """Create a backup of DocBro data."""
    service = BackupService()
    return await service.create_backup(components, path)


async def execute_removal(config: UninstallConfig, components):
    """Execute the uninstall process."""
    service = UninstallService()
    return await service.execute(config, components)


def display_components(components):
    """Display components that will be removed."""
    table = Table(title="Components to be removed", show_header=True, header_style="bold magenta")
    table.add_column("Type", style="cyan", no_wrap=True)
    table.add_column("Name", style="yellow")
    table.add_column("Status", style="green")

    # Add containers
    for container in components.get('containers', []):
        if hasattr(container, 'component_name'):
            name = container.component_name
        else:
            name = container.get('Names', ['/unknown'])[0].lstrip('/')
        table.add_row("Container", name, "Will be removed")

    # Add volumes
    for volume in components.get('volumes', []):
        if hasattr(volume, '__dict__'):
            name = volume.component_name
            status = "Preserved (external)" if volume.is_external else "Will be removed"
        else:
            name = volume.get('Name', 'unknown')
            status = "Will be removed"
        table.add_row("Volume", name, status)

    # Add directories
    for directory in components.get('directories', []):
        if hasattr(directory, 'component_path'):
            name = str(directory.component_path)
        else:
            name = str(directory)
        table.add_row("Directory", name, "Will be removed")

    # Add package
    if components.get('package'):
        table.add_row("Package", "docbro", "Will be uninstalled")

    console.print(table)

    # Calculate totals
    total_containers = len(components.get('containers', []))
    total_volumes = len([v for v in components.get('volumes', [])
                         if not (hasattr(v, 'is_external') and v.is_external)])
    total_dirs = len(components.get('directories', []))

    console.print(f"\nSummary: {total_containers} containers, {total_volumes} volumes, {total_dirs} directories")


@click.command()
@click.option(
    '--force',
    is_flag=True,
    help='Skip all confirmation prompts'
)
@click.option(
    '--backup',
    is_flag=True,
    help='Create backup before removal'
)
@click.option(
    '--backup-path',
    type=click.Path(path_type=Path),
    help='Path where backup will be created'
)
@click.option(
    '--dry-run',
    is_flag=True,
    help='Show what would be removed without removing'
)
@click.option(
    '--verbose',
    is_flag=True,
    help='Show detailed progress information'
)
@click.pass_context
def uninstall(
    ctx,
    force: bool,
    backup: bool,
    backup_path: Optional[Path],
    dry_run: bool,
    verbose: bool
):
    """Completely remove DocBro and all associated data from the system.

    This command will remove:
    - All DocBro Docker containers
    - All DocBro Docker volumes (preserves external volumes)
    - All DocBro data directories
    - The DocBro package installation

    WARNING: This action is IRREVERSIBLE!
    """
    # Store interactive mode in context
    ctx.obj = ctx.obj or {}
    ctx.obj['interactive'] = sys.stdin.isatty() and not force

    # Check if DocBro is installed
    if not is_docbro_installed():
        console.print("[red]DocBro is not installed on this system.[/red]")
        sys.exit(4)

    # Create configuration
    config = UninstallConfig(
        force=force,
        backup=backup,
        backup_path=backup_path,
        dry_run=dry_run,
        verbose=verbose
    )

    # Run async operations
    asyncio.run(run_uninstall(config))


async def run_uninstall(config: UninstallConfig):
    """Run the uninstall process asynchronously."""
    try:
        # Detect components
        with console.status("[bold green]Detecting DocBro components...", spinner="dots"):
            components = await detect_components()

        if not any([
            components.get('containers'),
            components.get('volumes'),
            components.get('directories'),
            components.get('package')
        ]):
            console.print("[yellow]No DocBro components found to remove.[/yellow]")
            sys.exit(4)

        # Display what will be removed
        console.print("\n[bold red]  WARNING: This action is IRREVERSIBLE![/bold red]\n")
        console.print("The following will be permanently removed:\n")
        display_components(components)

        # Dry run mode
        if config.dry_run:
            console.print("\n[cyan]DRY RUN: No changes will be made.[/cyan]")
            console.print("\nThe above components [italic]would be[/italic] removed.")
            sys.exit(0)

        # Confirmation prompt (unless --force)
        if not config.force:
            console.print()
            if not Confirm.ask(
                "[bold yellow]Are you sure you want to proceed?[/bold yellow]",
                default=False
            ):
                console.print("[red]Uninstall aborted by user.[/red]")
                sys.exit(2)

        # Create backup if requested
        if config.backup:
            console.print("\n[bold cyan]Creating backup...[/bold cyan]")
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                transient=True
            ) as progress:
                task = progress.add_task("Creating backup archive...", total=None)
                backup_info = await create_backup(components, config.backup_path)
                progress.update(task, completed=True)

            if backup_info:
                console.print(f"[green][/green] Backup created at: {backup_info['path']}")
                console.print(f"  Size: {backup_info['manifest']['size']['compressed']}")
            else:
                console.print("[yellow] Backup creation failed, continuing anyway...[/yellow]")

        # Execute uninstall
        console.print("\n[bold red]Removing DocBro components...[/bold red]")

        if config.verbose:
            # Verbose mode - show each operation
            service = UninstallService()
            result = await service.execute(config, components)
        else:
            # Progress bar mode
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                BarColumn(),
                TaskProgressColumn(),
            ) as progress:
                # Calculate total operations
                total = sum([
                    len(components.get('containers', [])) * 2,  # stop + remove
                    len(components.get('volumes', [])),
                    len(components.get('directories', [])),
                    len(components.get('configs', [])),
                    1 if components.get('package') else 0
                ])

                task = progress.add_task("Uninstalling...", total=total)

                # Custom progress callback
                original_execute = UninstallService.execute

                async def execute_with_progress(self, config, components, **kwargs):
                    # Hook into progress updates
                    original_increment_removed = self.progress.increment_removed
                    original_increment_failed = self.progress.increment_failed
                    original_increment_skipped = self.progress.increment_skipped

                    def increment_removed_with_ui():
                        original_increment_removed()
                        progress.update(task, advance=1)

                    def increment_failed_with_ui():
                        original_increment_failed()
                        progress.update(task, advance=1)

                    def increment_skipped_with_ui():
                        original_increment_skipped()
                        progress.update(task, advance=1)

                    # Replace methods temporarily
                    self.progress.increment_removed = increment_removed_with_ui
                    self.progress.increment_failed = increment_failed_with_ui
                    self.progress.increment_skipped = increment_skipped_with_ui

                    try:
                        return await original_execute(self, config, components, **kwargs)
                    finally:
                        # Restore original methods
                        self.progress.increment_removed = original_increment_removed
                        self.progress.increment_failed = original_increment_failed
                        self.progress.increment_skipped = original_increment_skipped

                UninstallService.execute = execute_with_progress
                service = UninstallService()
                result = await service.execute(config, components)

        # Display results
        console.print()
        if result['success']:
            console.print("[bold green] Uninstall completed successfully![/bold green]")
        elif result['removed'] > 0:
            console.print("[bold yellow] Uninstall partially completed[/bold yellow]")
        else:
            console.print("[bold red] Uninstall failed[/bold red]")

        # Summary
        summary_panel = Panel(
            f"[green]Removed:[/green] {result['removed']} components\n"
            f"[red]Failed:[/red] {result['failed']} components\n"
            f"[yellow]Skipped:[/yellow] {result['skipped']} components",
            title="Summary",
            border_style="cyan"
        )
        console.print(summary_panel)

        # Exit with appropriate code
        if result['success']:
            sys.exit(0)
        elif result['removed'] > 0:
            sys.exit(1)  # Partial success
        else:
            sys.exit(3)  # Complete failure

    except KeyboardInterrupt:
        console.print("\n[red]Uninstall aborted by user.[/red]")
        sys.exit(2)
    except Exception as e:
        logger.error(f"Uninstall failed: {e}")
        console.print(f"\n[bold red]Error:[/bold red] {e}")
        sys.exit(3)


# Make functions available for import in tests
__all__ = ['uninstall', 'is_docbro_installed', 'detect_components', 'create_backup', 'execute_removal']