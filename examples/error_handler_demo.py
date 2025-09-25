#!/usr/bin/env python3
"""Demo of the comprehensive error handling service integration."""

import asyncio
from pathlib import Path
import sys

# Add the src directory to Python path for demo purposes
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from services.error_handler import (
    ErrorHandlerService,
    ErrorCategory,
    ErrorSeverity,
    SystemRequirementsError,
    NetworkConnectivityError,
    PermissionDeniedError,
)
from services.installation_wizard import InstallationWizardService
from models.installation import InstallationRequest


async def demo_error_categorization():
    """Demo error categorization capabilities."""
    print("=== Error Categorization Demo ===")

    error_handler = ErrorHandlerService()

    # Test different error types
    test_errors = [
        TimeoutError("Operation timed out after 30 seconds"),
        ConnectionError("Unable to connect to service"),
        PermissionError("Access denied to /usr/local/bin"),
        ValueError("Invalid configuration format"),
        SystemRequirementsError("Python 3.13+ required"),
    ]

    for error in test_errors:
        category = error_handler.categorize_error(error)
        severity = error_handler.determine_severity(category)
        actions = error_handler.suggest_recovery_actions(category, severity, {})
        message = error_handler.create_user_friendly_message(category, str(error))

        print(f"\nError: {error}")
        print(f"Category: {category.value}")
        print(f"Severity: {severity.value}")
        print(f"Suggested Actions: {[a.value for a in actions]}")
        print(f"User Message: {message[:100]}...")


async def demo_error_handling():
    """Demo comprehensive error handling."""
    print("\n=== Error Handling Demo ===")

    error_handler = ErrorHandlerService()

    # Add progress callback
    def progress_callback(data):
        print(f"Progress: {data}")

    error_handler.set_progress_callback(progress_callback)

    # Test error handling
    network_error = NetworkConnectivityError("Failed to connect to Docker service")

    context = {
        "phase": "service_setup",
        "step": "docker_detection",
        "component": "service_detector",
        "operation": "check_docker_status"
    }

    error_context = await error_handler.handle_error(network_error, context)

    print(f"\nError handled:")
    print(f"  ID: {error_context.error_id}")
    print(f"  Category: {error_context.category.value}")
    print(f"  Severity: {error_context.severity.value}")
    print(f"  Phase: {error_context.phase}")
    print(f"  User Message: {error_context.user_message}")
    print(f"  Suggested Actions: {[a.value for a in error_context.suggested_actions]}")


async def demo_snapshot_and_rollback():
    """Demo snapshot creation and rollback capabilities."""
    print("\n=== Snapshot and Rollback Demo ===")

    error_handler = ErrorHandlerService()

    # Create snapshots
    snapshot1_id = await error_handler.create_snapshot(
        "system_check",
        "validate_python",
        "Before Python validation"
    )
    print(f"Created snapshot 1: {snapshot1_id}")

    snapshot2_id = await error_handler.create_snapshot(
        "service_setup",
        "detect_services",
        "Before service detection"
    )
    print(f"Created snapshot 2: {snapshot2_id}")

    # Show active snapshots
    active_snapshots = error_handler.get_active_snapshots()
    print(f"Active snapshots: {active_snapshots}")

    # Simulate rollback
    print(f"\nAttempting rollback to snapshot 1...")
    success = await error_handler.rollback_to_snapshot(snapshot1_id, partial_ok=True)
    print(f"Rollback successful: {success}")


async def demo_integration_with_wizard():
    """Demo integration with installation wizard."""
    print("\n=== Wizard Integration Demo ===")

    error_handler = ErrorHandlerService()
    wizard = InstallationWizardService()

    # Create installation request
    request = InstallationRequest(
        install_method="uvx",
        version="1.0.0",
        user_preferences={"verbose": True}
    )

    try:
        # Start installation (this will likely fail in demo environment)
        response = await wizard.start_installation(request)
        print(f"Installation started: {response.installation_id}")

    except Exception as e:
        print(f"Installation failed: {e}")

        # Handle the error with the error handler
        context = {
            "phase": "initialization",
            "component": "installation_wizard",
            "operation": "start_installation"
        }

        error_context = await error_handler.handle_error(e, context, wizard)

        print(f"\nError handled by error handler:")
        print(f"  Category: {error_context.category.value}")
        print(f"  Severity: {error_context.severity.value}")
        print(f"  User Message: {error_context.user_message}")

        # Handle cleanup
        print("\nPerforming cleanup...")
        await error_handler.cleanup_partial_installation(wizard)
        print("Cleanup completed")


async def demo_cancellation_handling():
    """Demo cancellation handling."""
    print("\n=== Cancellation Handling Demo ===")

    error_handler = ErrorHandlerService()
    wizard = InstallationWizardService()

    # Add cleanup callback
    def custom_cleanup():
        print("Custom cleanup callback executed")

    error_handler.add_cleanup_callback(custom_cleanup)

    # Simulate cancellation
    await error_handler.handle_cancellation(
        "User requested cancellation during service setup",
        wizard
    )

    print("Cancellation handled successfully")


async def demo_error_history():
    """Demo error history tracking."""
    print("\n=== Error History Demo ===")

    error_handler = ErrorHandlerService()

    # Generate some test errors
    test_errors = [
        ("Network issue", NetworkConnectivityError("Connection timeout")),
        ("Permission issue", PermissionDeniedError("Cannot write to directory")),
        ("System issue", SystemRequirementsError("Insufficient memory")),
    ]

    for description, error in test_errors:
        context = {"operation": description}
        await error_handler.handle_error(error, context)

    # Get error history
    history = error_handler.get_error_history()

    print(f"\nError history ({len(history)} errors):")
    for i, error_context in enumerate(history, 1):
        print(f"  {i}. {error_context.category.value}: {error_context.error_message}")

    # Get limited history
    recent = error_handler.get_error_history(limit=2)
    print(f"\nRecent errors ({len(recent)} errors):")
    for i, error_context in enumerate(recent, 1):
        print(f"  {i}. {error_context.category.value}: {error_context.error_message}")


async def main():
    """Run all demos."""
    print("DocBro Error Handler Service Demo")
    print("=" * 50)

    try:
        await demo_error_categorization()
        await demo_error_handling()
        await demo_snapshot_and_rollback()
        await demo_integration_with_wizard()
        await demo_cancellation_handling()
        await demo_error_history()

        print("\n" + "=" * 50)
        print("Demo completed successfully!")

    except Exception as e:
        print(f"\nDemo failed with error: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())