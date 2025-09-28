"""Health check command for DocBro CLI - Unified Implementation."""

import asyncio
import sys

import click
from rich.console import Console

# Optional uvloop for better performance
try:
    import uvloop
    UVLOOP_AVAILABLE = True
except ImportError:
    UVLOOP_AVAILABLE = False


def run_async(coro):
    """Run async coroutine in sync context."""
    if UVLOOP_AVAILABLE:
        try:
            uvloop.install()
        except Exception:
            pass

    return asyncio.run(coro)


@click.command(name="health")
@click.option("--system", "-s", is_flag=True, help="Check only system requirements")
@click.option("--services", "-e", is_flag=True, help="Check only external services")
@click.option("--config", "-c", is_flag=True, help="Check only configuration validity")
@click.option("--projects", "-p", is_flag=True, help="Check project-specific health")
@click.option("--format", "-f", "format_type", default="table",
              type=click.Choice(["table", "json", "yaml"], case_sensitive=False),
              help="Output format")
@click.option("--verbose", "-v", is_flag=True, help="Include detailed diagnostic information")
@click.option("--quiet", "-q", is_flag=True, help="Suppress progress indicators, show only results")
@click.option("--timeout", "-t", default=15, type=click.IntRange(1, 60),
              help="Maximum execution timeout in seconds")
@click.option("--parallel", "-P", default=4, type=click.IntRange(1, 8),
              help="Maximum parallel health checks")
@click.pass_context
def health(ctx: click.Context, system: bool, services: bool, config: bool, projects: bool,
           format_type: str, verbose: bool, quiet: bool, timeout: int, parallel: int):
    """Check health status of DocBro components with comprehensive validation.

    This unified health command provides comprehensive validation of:
    - System requirements (Python version, memory, disk space)
    - External services (Docker, Qdrant, Ollama, Git)
    - Configuration files (settings, projects, vector store)
    - Project-specific health (when projects exist)

    \b
    Category Options:
      --system      System requirements only
      --services    External services only
      --config      Configuration files only
      --projects    Project health only
      (default)     All categories except projects

    \b
    Output Formats:
      table         Formatted table with status indicators (default)
      json          Machine-readable JSON for automation
      yaml          YAML format for configuration tools

    \b
    Examples:
      docbro health                    # Complete health check
      docbro health --system           # System requirements only
      docbro health --format json     # JSON output for scripts
      docbro health --timeout 30      # Extended timeout
    """
    async def _unified_health_check():
        try:
            # Import health orchestration components
            from src.logic.health.core.orchestrator import HealthOrchestrator
            from src.logic.health.core.router import HealthCommandRouter

            # Initialize components
            router = HealthCommandRouter()

            # Parse and validate flags
            try:
                categories, options = router.parse_flags(
                    system=system,
                    services=services,
                    config=config,
                    projects=projects,
                    format_type=format_type,
                    verbose=verbose,
                    quiet=quiet,
                    timeout=timeout,
                    parallel=parallel
                )
            except ValueError as e:
                console = Console()
                console.print(f"[red]Error: {e}[/red]")
                console.print("Use [cyan]docbro health --help[/cyan] for usage information")
                sys.exit(4)  # Invalid arguments exit code

            # Initialize orchestrator with validated options
            orchestrator = HealthOrchestrator(
                timeout=options['timeout'],
                max_parallel=options['parallel']
            )

            # Show progress if not in quiet mode
            console = Console()
            if not options['suppress_progress']:
                category_names = [cat.display_name for cat in categories]
                console.print(f"🔍 Running health checks for: {', '.join(category_names)}")

            # Execute health checks
            try:
                report = await orchestrator.run_comprehensive_health_check(categories)
            except KeyboardInterrupt:
                console.print("[yellow]Health check interrupted by user[/yellow]")
                sys.exit(5)  # Interrupted exit code

            # Generate output title
            title = router.get_title_for_categories(categories)

            # Format and display results
            output = orchestrator.health_reporter.format_output(
                report=report,
                format_type=options['format'].value,
                detailed=options['show_detailed'],
                title=title
            )

            # Print output
            print(output.rstrip())  # Remove trailing newlines

            # Show resolution guidance if needed
            if router.should_show_resolution_guidance(options, report.has_issues):
                suggestions = orchestrator.health_reporter.get_resolution_suggestions(report)
                if suggestions and not options['quiet']:
                    console.print("\n[cyan]Resolution Guidance:[/cyan]")
                    for suggestion in suggestions[:3]:  # Limit to top 3 suggestions
                        console.print(f"  • {suggestion}")

            # Exit with appropriate code
            sys.exit(report.exit_code)

        except Exception as e:
            console = Console()
            if not quiet:
                console.print(f"[red]Health check failed: {e}[/red]")
                if verbose:
                    import traceback
                    console.print(f"[dim]{traceback.format_exc()}[/dim]")

            # Check for import errors (likely missing dependencies)
            if "No module named" in str(e):
                console.print("[yellow]Tip: Try running 'docbro setup' to fix installation issues[/yellow]")

            sys.exit(3)  # Unavailable exit code

    run_async(_unified_health_check())