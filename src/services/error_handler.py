"""Comprehensive error handling and rollback service for DocBro installations.

This service provides a centralized error handling system with rollback capabilities,
error categorization, and recovery mechanisms for installation failures.
"""

import asyncio
import json
import shutil
import traceback
import uuid
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable, Union, Type
import logging

from pydantic import BaseModel, Field, ConfigDict

from .config import ConfigService
from .installation_wizard import InstallationWizardService
from src.models.installation import InstallationContext, ServiceStatus
from src.models.installation_state import InstallationState
from src.models.installation_profile import InstallationProfile
from src.core.lib_logger import get_component_logger


class ErrorCategory(str, Enum):
    """Categories of installation errors for better classification."""

    SYSTEM_REQUIREMENTS = "system_requirements"
    NETWORK_CONNECTIVITY = "network_connectivity"
    PERMISSION_DENIED = "permission_denied"
    SERVICE_UNAVAILABLE = "service_unavailable"
    CONFIGURATION = "configuration"
    DISK_SPACE = "disk_space"
    DEPENDENCY_MISSING = "dependency_missing"
    TIMEOUT = "timeout"
    CANCELLATION = "cancellation"
    DATA_CORRUPTION = "data_corruption"
    VERSION_CONFLICT = "version_conflict"
    UNKNOWN = "unknown"


class ErrorSeverity(str, Enum):
    """Severity levels for errors."""

    CRITICAL = "critical"      # Installation cannot proceed
    HIGH = "high"             # Major functionality affected
    MEDIUM = "medium"         # Some functionality affected
    LOW = "low"              # Minor issues
    INFO = "info"            # Informational warnings


class RecoveryAction(str, Enum):
    """Types of recovery actions available."""

    RETRY = "retry"
    ROLLBACK = "rollback"
    SKIP = "skip"
    MANUAL = "manual"
    ABORT = "abort"
    CLEANUP = "cleanup"


class ErrorContext(BaseModel):
    """Context information for an error occurrence."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            Path: str
        }
    )

    error_id: str = Field(default_factory=lambda: f"err_{uuid.uuid4().hex[:8]}")
    timestamp: datetime = Field(default_factory=datetime.now)
    category: ErrorCategory = Field(...)
    severity: ErrorSeverity = Field(...)
    phase: Optional[str] = Field(None, description="Installation phase when error occurred")
    step: Optional[str] = Field(None, description="Installation step when error occurred")
    component: Optional[str] = Field(None, description="Component that caused the error")
    operation: Optional[str] = Field(None, description="Operation being performed")

    # Error details
    error_message: str = Field(...)
    user_message: str = Field(..., description="User-friendly error message")
    technical_details: Optional[str] = Field(None, description="Technical details for debugging")
    stack_trace: Optional[str] = Field(None)

    # Context
    environment_info: Dict[str, Any] = Field(default_factory=dict)
    system_state: Dict[str, Any] = Field(default_factory=dict)

    # Recovery
    suggested_actions: List[RecoveryAction] = Field(default_factory=list)
    can_retry: bool = Field(default=True)
    retry_count: int = Field(default=0)
    max_retries: int = Field(default=3)


class InstallationSnapshot(BaseModel):
    """Snapshot of installation state for rollback purposes."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_encoders={
            datetime: lambda v: v.isoformat(),
            Path: str
        }
    )

    snapshot_id: str = Field(default_factory=lambda: f"snap_{uuid.uuid4().hex[:8]}")
    timestamp: datetime = Field(default_factory=datetime.now)
    phase: str = Field(...)
    step: str = Field(...)

    # File system state
    created_directories: List[Path] = Field(default_factory=list)
    created_files: List[Path] = Field(default_factory=list)
    modified_files: Dict[str, str] = Field(default_factory=dict)  # path -> backup_path

    # System state
    installation_state: Optional[Dict[str, Any]] = Field(None)
    installation_profile: Optional[Dict[str, Any]] = Field(None)
    service_statuses: Dict[str, Dict[str, Any]] = Field(default_factory=dict)

    # Configuration state
    config_backups: Dict[str, str] = Field(default_factory=dict)  # config_path -> backup_content

    description: str = Field(default="Installation snapshot")


class RollbackOperation(BaseModel):
    """Represents a rollback operation to be performed."""

    operation_type: str = Field(...)  # "delete_file", "restore_file", "delete_directory", etc.
    target_path: Path = Field(...)
    backup_path: Optional[Path] = Field(None)
    description: str = Field(...)
    critical: bool = Field(default=False)  # If true, rollback fails if this operation fails


class ErrorHandlingError(Exception):
    """Base exception for error handling service errors."""
    pass


class RollbackError(ErrorHandlingError):
    """Exception raised when rollback operations fail."""
    pass


class ErrorHandlerService:
    """Comprehensive error handling and rollback service for DocBro installations.

    This service provides:
    - Custom exception hierarchy for installation errors
    - Rollback logic for failed installations
    - Service setup failure recovery
    - Error categorization and user-friendly messages
    - Partial installation cleanup
    - Timeout and cancellation handling
    - Structured error logging
    - Integration with InstallationWizardService
    """

    def __init__(self):
        """Initialize error handler service."""
        self.config_service = ConfigService()
        self.logger = get_component_logger("error_handler")

        # State management
        self.active_snapshots: Dict[str, InstallationSnapshot] = {}
        self.error_history: List[ErrorContext] = []
        self.rollback_operations: List[RollbackOperation] = []

        # Callbacks for integration
        self.progress_callback: Optional[Callable[[Dict[str, Any]], None]] = None
        self.cleanup_callbacks: List[Callable[[], None]] = []

        # Error categorization rules
        self._setup_error_categorization()

    def _setup_error_categorization(self) -> None:
        """Setup error categorization rules."""
        # Separate exception types and text patterns for better control
        self.exception_rules = {
            # Timeout errors (specific - check first)
            TimeoutError: ErrorCategory.TIMEOUT,

            # Network errors
            ConnectionError: ErrorCategory.NETWORK_CONNECTIVITY,
            ConnectionRefusedError: ErrorCategory.NETWORK_CONNECTIVITY,

            # Permission errors (more general)
            PermissionError: ErrorCategory.PERMISSION_DENIED,
        }

        self.text_patterns = {
            # Timeout patterns
            ("timeout", "timed out", "deadline"): ErrorCategory.TIMEOUT,

            # Network patterns
            ("connection", "network", "unreachable"): ErrorCategory.NETWORK_CONNECTIVITY,

            # Permission patterns
            ("permission", "access denied", "forbidden"): ErrorCategory.PERMISSION_DENIED,

            # System requirements
            ("python version", "uv version", "memory", "disk space"): ErrorCategory.SYSTEM_REQUIREMENTS,

            # Service errors
            ("docker", "qdrant", "ollama", "redis", "service"): ErrorCategory.SERVICE_UNAVAILABLE,

            # Configuration errors
            ("config", "configuration", "invalid format"): ErrorCategory.CONFIGURATION,

            # Disk space errors
            ("disk", "space", "storage", "no space"): ErrorCategory.DISK_SPACE,

            # Dependency errors
            ("dependency", "package", "import", "module"): ErrorCategory.DEPENDENCY_MISSING,

            # Cancellation
            ("cancelled", "canceled", "interrupted", "abort"): ErrorCategory.CANCELLATION,

            # Data corruption
            ("corrupt", "malformed", "invalid json", "decode"): ErrorCategory.DATA_CORRUPTION,

            # Version conflicts
            ("version", "conflict", "incompatible"): ErrorCategory.VERSION_CONFLICT,
        }

    def categorize_error(self, error: Exception, context: Optional[str] = None) -> ErrorCategory:
        """Categorize an error based on its type and message.

        Args:
            error: The exception that occurred
            context: Additional context string

        Returns:
            ErrorCategory for the error
        """
        error_text = str(error).lower()
        if context:
            error_text += f" {context.lower()}"

        # Check exception types first (specific types take precedence)
        for exception_type, category in self.exception_rules.items():
            if isinstance(error, exception_type):
                return category

        # Check text patterns
        for keywords, category in self.text_patterns.items():
            if any(keyword in error_text for keyword in keywords):
                return category

        return ErrorCategory.UNKNOWN

    def determine_severity(self, category: ErrorCategory, phase: Optional[str] = None) -> ErrorSeverity:
        """Determine error severity based on category and phase.

        Args:
            category: Error category
            phase: Installation phase when error occurred

        Returns:
            ErrorSeverity level
        """
        # Critical errors that prevent installation
        if category in [
            ErrorCategory.SYSTEM_REQUIREMENTS,
            ErrorCategory.PERMISSION_DENIED,
            ErrorCategory.DISK_SPACE
        ]:
            return ErrorSeverity.CRITICAL

        # High severity during critical phases
        if phase in ["system_check", "finalization"] and category in [
            ErrorCategory.NETWORK_CONNECTIVITY,
            ErrorCategory.CONFIGURATION,
            ErrorCategory.DATA_CORRUPTION
        ]:
            return ErrorSeverity.HIGH

        # Medium severity for service issues (can often be skipped)
        if category == ErrorCategory.SERVICE_UNAVAILABLE:
            return ErrorSeverity.MEDIUM

        # High severity for timeouts and cancellations
        if category in [ErrorCategory.TIMEOUT, ErrorCategory.CANCELLATION]:
            return ErrorSeverity.HIGH

        # Default to medium
        return ErrorSeverity.MEDIUM

    def suggest_recovery_actions(
        self,
        category: ErrorCategory,
        severity: ErrorSeverity,
        context: Dict[str, Any]
    ) -> List[RecoveryAction]:
        """Suggest recovery actions based on error characteristics.

        Args:
            category: Error category
            severity: Error severity
            context: Additional context information

        Returns:
            List of suggested recovery actions
        """
        actions = []

        # Critical system errors usually require manual intervention
        if severity == ErrorSeverity.CRITICAL:
            if category == ErrorCategory.SYSTEM_REQUIREMENTS:
                actions.extend([RecoveryAction.MANUAL, RecoveryAction.ABORT])
            elif category == ErrorCategory.PERMISSION_DENIED:
                actions.extend([RecoveryAction.MANUAL, RecoveryAction.RETRY])
            elif category == ErrorCategory.DISK_SPACE:
                actions.extend([RecoveryAction.CLEANUP, RecoveryAction.MANUAL])
            else:
                actions.extend([RecoveryAction.ROLLBACK, RecoveryAction.ABORT])

        # Network and service errors can often be retried
        elif category in [ErrorCategory.NETWORK_CONNECTIVITY, ErrorCategory.SERVICE_UNAVAILABLE]:
            actions.extend([RecoveryAction.RETRY, RecoveryAction.SKIP])

        # Timeout errors should be retried with different parameters
        elif category == ErrorCategory.TIMEOUT:
            actions.extend([RecoveryAction.RETRY, RecoveryAction.ROLLBACK])

        # Configuration errors might be recoverable
        elif category == ErrorCategory.CONFIGURATION:
            actions.extend([RecoveryAction.RETRY, RecoveryAction.ROLLBACK])

        # Cancellation should clean up
        elif category == ErrorCategory.CANCELLATION:
            actions.extend([RecoveryAction.CLEANUP, RecoveryAction.ROLLBACK])

        # Data corruption needs rollback
        elif category == ErrorCategory.DATA_CORRUPTION:
            actions.extend([RecoveryAction.ROLLBACK, RecoveryAction.CLEANUP])

        # Default actions
        else:
            actions.extend([RecoveryAction.RETRY, RecoveryAction.ROLLBACK])

        return actions

    def create_user_friendly_message(self, category: ErrorCategory, error_message: str) -> str:
        """Create user-friendly error messages.

        Args:
            category: Error category
            error_message: Technical error message

        Returns:
            User-friendly error message
        """
        messages = {
            ErrorCategory.SYSTEM_REQUIREMENTS: {
                "message": "Your system doesn't meet the minimum requirements for DocBro.",
                "suggestions": [
                    "Ensure you have Python 3.13+ installed",
                    "Install the UV package manager",
                    "Check available disk space and memory"
                ]
            },
            ErrorCategory.NETWORK_CONNECTIVITY: {
                "message": "Unable to connect to required services or download dependencies.",
                "suggestions": [
                    "Check your internet connection",
                    "Verify firewall settings",
                    "Try again in a few moments"
                ]
            },
            ErrorCategory.PERMISSION_DENIED: {
                "message": "DocBro doesn't have permission to access required files or directories.",
                "suggestions": [
                    "Run the installation with appropriate permissions",
                    "Check file and directory ownership",
                    "Ensure write access to the installation directory"
                ]
            },
            ErrorCategory.SERVICE_UNAVAILABLE: {
                "message": "One or more external services are not available.",
                "suggestions": [
                    "Start Docker if you want to use vector search features",
                    "Install Ollama for local embeddings",
                    "Some features may work without all services"
                ]
            },
            ErrorCategory.CONFIGURATION: {
                "message": "There's an issue with the configuration setup.",
                "suggestions": [
                    "Check configuration file format",
                    "Reset to default configuration if needed",
                    "Remove conflicting configuration files"
                ]
            },
            ErrorCategory.DISK_SPACE: {
                "message": "Not enough disk space available for installation.",
                "suggestions": [
                    "Free up disk space",
                    "Clean up temporary files",
                    "Choose a different installation location"
                ]
            },
            ErrorCategory.DEPENDENCY_MISSING: {
                "message": "Required dependencies are missing or incompatible.",
                "suggestions": [
                    "Update your package manager",
                    "Install missing system dependencies",
                    "Check Python environment compatibility"
                ]
            },
            ErrorCategory.TIMEOUT: {
                "message": "The installation process timed out.",
                "suggestions": [
                    "Check your internet connection",
                    "Try the installation again",
                    "Increase timeout settings if available"
                ]
            },
            ErrorCategory.CANCELLATION: {
                "message": "The installation was cancelled or interrupted.",
                "suggestions": [
                    "Restart the installation if desired",
                    "Clean up any partial installation files",
                    "Check system resources before retrying"
                ]
            },
            ErrorCategory.DATA_CORRUPTION: {
                "message": "Installation data appears to be corrupted.",
                "suggestions": [
                    "Remove corrupted files and retry",
                    "Check disk integrity",
                    "Restart the installation process"
                ]
            },
            ErrorCategory.VERSION_CONFLICT: {
                "message": "Version compatibility issues detected.",
                "suggestions": [
                    "Update to a compatible version",
                    "Remove conflicting installations",
                    "Check version requirements"
                ]
            }
        }

        error_info = messages.get(category, {
            "message": f"An unexpected error occurred: {error_message}",
            "suggestions": ["Try the installation again", "Check the logs for more details"]
        })

        message = error_info["message"]
        if error_info.get("suggestions"):
            message += "\n\nSuggested actions:\n"
            for suggestion in error_info["suggestions"]:
                message += f"• {suggestion}\n"

        return message.strip()

    async def handle_error(
        self,
        error: Exception,
        context: Optional[Dict[str, Any]] = None,
        installation_wizard: Optional[InstallationWizardService] = None
    ) -> ErrorContext:
        """Handle an error with comprehensive analysis and recovery options.

        Args:
            error: The exception that occurred
            context: Additional context information
            installation_wizard: Reference to installation wizard for state recovery

        Returns:
            ErrorContext with analysis and recovery options
        """
        context = context or {}

        # Categorize and analyze the error
        category = self.categorize_error(error, context.get("operation"))
        severity = self.determine_severity(category, context.get("phase"))
        suggested_actions = self.suggest_recovery_actions(category, severity, context)

        # Create user-friendly message
        user_message = self.create_user_friendly_message(category, str(error))

        # Gather system state
        system_state = await self._gather_system_state()
        environment_info = self._gather_environment_info()

        # Create error context
        error_context = ErrorContext(
            category=category,
            severity=severity,
            phase=context.get("phase"),
            step=context.get("step"),
            component=context.get("component"),
            operation=context.get("operation"),
            error_message=str(error),
            user_message=user_message,
            technical_details=context.get("technical_details"),
            stack_trace=traceback.format_exc(),
            environment_info=environment_info,
            system_state=system_state,
            suggested_actions=suggested_actions
        )

        # Log the error
        await self._log_error(error_context)

        # Add to error history
        self.error_history.append(error_context)

        # Notify progress callback
        if self.progress_callback:
            self.progress_callback({
                "type": "error",
                "error_id": error_context.error_id,
                "category": category.value,
                "severity": severity.value,
                "message": user_message
            })

        # Update installation wizard state if available
        if installation_wizard and installation_wizard.installation_state:
            installation_wizard.installation_state.mark_error(
                error_context.user_message,
                error_context.error_id
            )

        return error_context

    async def create_snapshot(
        self,
        phase: str,
        step: str,
        description: Optional[str] = None,
        installation_wizard: Optional[InstallationWizardService] = None
    ) -> str:
        """Create a snapshot of the current installation state for rollback.

        Args:
            phase: Current installation phase
            step: Current installation step
            description: Optional description of the snapshot
            installation_wizard: Reference to installation wizard

        Returns:
            Snapshot ID
        """
        try:
            snapshot = InstallationSnapshot(
                phase=phase,
                step=step,
                description=description or f"Snapshot at {phase}:{step}"
            )

            # Capture file system state
            await self._capture_filesystem_state(snapshot)

            # Capture installation state
            if installation_wizard:
                if installation_wizard.installation_state:
                    snapshot.installation_state = installation_wizard.installation_state.model_dump()
                if installation_wizard.installation_profile:
                    snapshot.installation_profile = installation_wizard.installation_profile.model_dump()

            # Capture service statuses
            snapshot.service_statuses = await self._capture_service_state()

            # Store snapshot
            self.active_snapshots[snapshot.snapshot_id] = snapshot

            # Persist snapshot to disk
            await self._persist_snapshot(snapshot)

            self.logger.info(
                f"Created installation snapshot: {snapshot.snapshot_id}",
                extra={"snapshot_id": snapshot.snapshot_id, "phase": phase, "step": step}
            )

            return snapshot.snapshot_id

        except Exception as e:
            self.logger.error(f"Failed to create snapshot: {e}")
            raise ErrorHandlingError(f"Cannot create installation snapshot: {str(e)}")

    async def rollback_to_snapshot(
        self,
        snapshot_id: str,
        installation_wizard: Optional[InstallationWizardService] = None,
        partial_ok: bool = True
    ) -> bool:
        """Rollback installation to a previous snapshot.

        Args:
            snapshot_id: ID of the snapshot to rollback to
            installation_wizard: Reference to installation wizard
            partial_ok: Whether partial rollback is acceptable

        Returns:
            True if rollback was successful (or partially successful with partial_ok=True)

        Raises:
            RollbackError: If rollback fails and partial_ok=False
        """
        try:
            # Load snapshot
            snapshot = self.active_snapshots.get(snapshot_id)
            if not snapshot:
                snapshot = await self._load_snapshot(snapshot_id)

            if not snapshot:
                raise RollbackError(f"Snapshot {snapshot_id} not found")

            self.logger.info(
                f"Starting rollback to snapshot: {snapshot_id}",
                extra={"snapshot_id": snapshot_id, "phase": snapshot.phase}
            )

            # Notify progress callback
            if self.progress_callback:
                self.progress_callback({
                    "type": "rollback_start",
                    "snapshot_id": snapshot_id,
                    "description": snapshot.description
                })

            rollback_success = True
            failed_operations = []

            # Rollback file system changes
            try:
                await self._rollback_filesystem(snapshot, partial_ok)
            except Exception as e:
                self.logger.error(f"Filesystem rollback failed: {e}")
                failed_operations.append(f"Filesystem rollback: {e}")
                if not partial_ok:
                    rollback_success = False

            # Rollback configuration changes
            try:
                await self._rollback_configuration(snapshot)
            except Exception as e:
                self.logger.error(f"Configuration rollback failed: {e}")
                failed_operations.append(f"Configuration rollback: {e}")
                if not partial_ok:
                    rollback_success = False

            # Rollback installation wizard state
            if installation_wizard:
                try:
                    await self._rollback_wizard_state(snapshot, installation_wizard)
                except Exception as e:
                    self.logger.error(f"Wizard state rollback failed: {e}")
                    failed_operations.append(f"Wizard state rollback: {e}")
                    if not partial_ok:
                        rollback_success = False

            # Run cleanup callbacks
            for callback in self.cleanup_callbacks:
                try:
                    callback()
                except Exception as e:
                    self.logger.warning(f"Cleanup callback failed: {e}")

            # Update status
            if rollback_success or (partial_ok and len(failed_operations) < 3):
                self.logger.info(
                    f"Rollback to snapshot {snapshot_id} completed",
                    extra={
                        "snapshot_id": snapshot_id,
                        "success": rollback_success,
                        "failed_operations": failed_operations
                    }
                )

                if self.progress_callback:
                    self.progress_callback({
                        "type": "rollback_complete",
                        "snapshot_id": snapshot_id,
                        "success": rollback_success,
                        "failed_operations": failed_operations
                    })

                return True
            else:
                error_msg = f"Rollback failed: {'; '.join(failed_operations)}"
                self.logger.error(error_msg)

                if self.progress_callback:
                    self.progress_callback({
                        "type": "rollback_failed",
                        "snapshot_id": snapshot_id,
                        "error": error_msg
                    })

                if not partial_ok:
                    raise RollbackError(error_msg)

                return False

        except Exception as e:
            error_msg = f"Rollback to snapshot {snapshot_id} failed: {str(e)}"
            self.logger.error(error_msg)

            if self.progress_callback:
                self.progress_callback({
                    "type": "rollback_failed",
                    "snapshot_id": snapshot_id,
                    "error": error_msg
                })

            if not partial_ok:
                raise RollbackError(error_msg)

            return False

    async def cleanup_partial_installation(
        self,
        installation_wizard: Optional[InstallationWizardService] = None
    ) -> None:
        """Clean up partial installation artifacts.

        Args:
            installation_wizard: Reference to installation wizard
        """
        try:
            self.logger.info("Starting partial installation cleanup")

            # Clean up installation state files
            if installation_wizard:
                try:
                    await installation_wizard.rollback_installation()
                except Exception as e:
                    self.logger.warning(f"Wizard rollback failed during cleanup: {e}")

            # Clean up configuration files
            config_files = [
                self.config_service.installation_config_path,
                self.config_service.config_dir / "installation_state.json",
                self.config_service.config_dir / "installation_profile.json",
            ]

            for config_file in config_files:
                try:
                    if config_file.exists():
                        config_file.unlink()
                        self.logger.debug(f"Removed config file: {config_file}")
                except Exception as e:
                    self.logger.warning(f"Failed to remove config file {config_file}: {e}")

            # Clean up snapshots
            for snapshot_id in list(self.active_snapshots.keys()):
                try:
                    await self._cleanup_snapshot(snapshot_id)
                except Exception as e:
                    self.logger.warning(f"Failed to cleanup snapshot {snapshot_id}: {e}")

            # Run cleanup callbacks
            for callback in self.cleanup_callbacks:
                try:
                    callback()
                except Exception as e:
                    self.logger.warning(f"Cleanup callback failed: {e}")

            self.logger.info("Partial installation cleanup completed")

        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            # Don't raise exception for cleanup failures

    async def handle_timeout(
        self,
        operation: str,
        timeout_seconds: float,
        installation_wizard: Optional[InstallationWizardService] = None
    ) -> ErrorContext:
        """Handle timeout scenarios during installation.

        Args:
            operation: Description of the operation that timed out
            timeout_seconds: Timeout duration in seconds
            installation_wizard: Reference to installation wizard

        Returns:
            ErrorContext for the timeout
        """
        timeout_error = TimeoutError(f"Operation '{operation}' timed out after {timeout_seconds} seconds")

        context = {
            "operation": operation,
            "timeout_seconds": timeout_seconds,
            "phase": installation_wizard.installation_state.current_phase if installation_wizard and installation_wizard.installation_state else None,
            "step": installation_wizard.installation_state.current_step if installation_wizard and installation_wizard.installation_state else None,
            "component": "timeout_handler",
            "technical_details": f"Timeout occurred in {operation} after {timeout_seconds}s"
        }

        return await self.handle_error(timeout_error, context, installation_wizard)

    async def handle_cancellation(
        self,
        reason: str = "User cancellation",
        installation_wizard: Optional[InstallationWizardService] = None
    ) -> None:
        """Handle installation cancellation scenarios.

        Args:
            reason: Reason for cancellation
            installation_wizard: Reference to installation wizard
        """
        self.logger.info(f"Handling installation cancellation: {reason}")

        try:
            # Create error context for cancellation
            cancellation_error = InterruptedError(f"Installation cancelled: {reason}")

            context = {
                "operation": "installation",
                "phase": installation_wizard.installation_state.current_phase if installation_wizard and installation_wizard.installation_state else None,
                "step": installation_wizard.installation_state.current_step if installation_wizard and installation_wizard.installation_state else None,
                "component": "cancellation_handler",
                "technical_details": f"Installation cancelled: {reason}"
            }

            error_context = await self.handle_error(cancellation_error, context, installation_wizard)

            # Perform cleanup
            await self.cleanup_partial_installation(installation_wizard)

            self.logger.info("Installation cancellation handled successfully")

        except Exception as e:
            self.logger.error(f"Failed to handle cancellation: {e}")
            # Still try to cleanup even if error handling fails
            try:
                await self.cleanup_partial_installation(installation_wizard)
            except Exception:
                pass

    def add_cleanup_callback(self, callback: Callable[[], None]) -> None:
        """Add a cleanup callback to be called during rollback/cleanup.

        Args:
            callback: Function to call during cleanup
        """
        self.cleanup_callbacks.append(callback)

    def set_progress_callback(self, callback: Callable[[Dict[str, Any]], None]) -> None:
        """Set callback for progress updates.

        Args:
            callback: Function to call with progress updates
        """
        self.progress_callback = callback

    def get_error_history(self, limit: Optional[int] = None) -> List[ErrorContext]:
        """Get error history for debugging.

        Args:
            limit: Maximum number of errors to return

        Returns:
            List of error contexts
        """
        if limit:
            return self.error_history[-limit:]
        return self.error_history.copy()

    def get_active_snapshots(self) -> List[str]:
        """Get list of active snapshot IDs.

        Returns:
            List of snapshot IDs
        """
        return list(self.active_snapshots.keys())

    async def _capture_filesystem_state(self, snapshot: InstallationSnapshot) -> None:
        """Capture current filesystem state for rollback."""
        # This would capture created files/directories
        # For now, we'll implement basic tracking

        # Track configuration directory state
        if self.config_service.config_dir.exists():
            for file_path in self.config_service.config_dir.rglob("*"):
                if file_path.is_file():
                    snapshot.created_files.append(file_path)

        # Track data directory state
        if self.config_service.data_dir.exists():
            for file_path in self.config_service.data_dir.rglob("*"):
                if file_path.is_file():
                    snapshot.created_files.append(file_path)

    async def _capture_service_state(self) -> Dict[str, Dict[str, Any]]:
        """Capture current service state."""
        # This would capture service configurations and states
        return {}

    async def _persist_snapshot(self, snapshot: InstallationSnapshot) -> None:
        """Persist snapshot to disk."""
        snapshot_dir = self.config_service.cache_dir / "snapshots"
        snapshot_dir.mkdir(parents=True, exist_ok=True)

        snapshot_file = snapshot_dir / f"{snapshot.snapshot_id}.json"

        with open(snapshot_file, 'w') as f:
            json.dump(snapshot.model_dump(mode='json'), f, indent=2)

    async def _load_snapshot(self, snapshot_id: str) -> Optional[InstallationSnapshot]:
        """Load snapshot from disk."""
        snapshot_file = self.config_service.cache_dir / "snapshots" / f"{snapshot_id}.json"

        if not snapshot_file.exists():
            return None

        try:
            with open(snapshot_file, 'r') as f:
                data = json.load(f)
                return InstallationSnapshot.model_validate(data)
        except Exception as e:
            self.logger.error(f"Failed to load snapshot {snapshot_id}: {e}")
            return None

    async def _rollback_filesystem(self, snapshot: InstallationSnapshot, partial_ok: bool) -> None:
        """Rollback filesystem changes."""
        errors = []

        # Remove created files
        for file_path in snapshot.created_files:
            try:
                if file_path.exists():
                    file_path.unlink()
            except Exception as e:
                errors.append(f"Failed to remove {file_path}: {e}")
                if not partial_ok:
                    raise

        # Remove created directories (in reverse order)
        for dir_path in reversed(snapshot.created_directories):
            try:
                if dir_path.exists() and dir_path.is_dir():
                    # Only remove if empty
                    try:
                        dir_path.rmdir()
                    except OSError:
                        # Directory not empty, that's okay
                        pass
            except Exception as e:
                errors.append(f"Failed to remove directory {dir_path}: {e}")
                if not partial_ok:
                    raise

        # Restore modified files
        for file_path_str, backup_path_str in snapshot.modified_files.items():
            try:
                file_path = Path(file_path_str)
                backup_path = Path(backup_path_str)
                if backup_path.exists():
                    shutil.copy2(backup_path, file_path)
                    backup_path.unlink()  # Clean up backup
            except Exception as e:
                errors.append(f"Failed to restore {file_path_str}: {e}")
                if not partial_ok:
                    raise

        if errors and not partial_ok:
            raise RollbackError(f"Filesystem rollback failed: {'; '.join(errors)}")

    async def _rollback_configuration(self, snapshot: InstallationSnapshot) -> None:
        """Rollback configuration changes."""
        for config_path, backup_content in snapshot.config_backups.items():
            try:
                config_file = Path(config_path)
                with open(config_file, 'w') as f:
                    f.write(backup_content)
            except Exception as e:
                self.logger.error(f"Failed to restore config {config_path}: {e}")
                raise

    async def _rollback_wizard_state(
        self,
        snapshot: InstallationSnapshot,
        installation_wizard: InstallationWizardService
    ) -> None:
        """Rollback installation wizard state."""
        if snapshot.installation_state:
            try:
                installation_wizard.installation_state = InstallationState.model_validate(snapshot.installation_state)
            except Exception as e:
                self.logger.error(f"Failed to restore installation state: {e}")
                raise

        if snapshot.installation_profile:
            try:
                installation_wizard.installation_profile = InstallationProfile.model_validate(snapshot.installation_profile)
            except Exception as e:
                self.logger.error(f"Failed to restore installation profile: {e}")
                raise

    async def _cleanup_snapshot(self, snapshot_id: str) -> None:
        """Clean up snapshot files."""
        # Remove from active snapshots
        self.active_snapshots.pop(snapshot_id, None)

        # Remove snapshot file
        snapshot_file = self.config_service.cache_dir / "snapshots" / f"{snapshot_id}.json"
        if snapshot_file.exists():
            snapshot_file.unlink()

    async def _gather_system_state(self) -> Dict[str, Any]:
        """Gather current system state for error context."""
        import platform
        import psutil

        try:
            return {
                "platform": platform.platform(),
                "python_version": platform.python_version(),
                "available_memory": psutil.virtual_memory().available,
                "disk_usage": psutil.disk_usage('/').free,
                "cpu_count": psutil.cpu_count(),
                "load_average": psutil.getloadavg() if hasattr(psutil, 'getloadavg') else None
            }
        except Exception as e:
            return {"error": f"Failed to gather system state: {e}"}

    def _gather_environment_info(self) -> Dict[str, Any]:
        """Gather environment information."""
        import os

        return {
            "config_dir": str(self.config_service.config_dir),
            "data_dir": str(self.config_service.data_dir),
            "cache_dir": str(self.config_service.cache_dir),
            "environment_vars": {
                k: v for k, v in os.environ.items()
                if k.startswith(('DOCBRO_', 'UV', 'PYTHON'))
            }
        }

    async def _log_error(self, error_context: ErrorContext) -> None:
        """Log error with structured information."""
        log_data = {
            "error_id": error_context.error_id,
            "category": error_context.category.value,
            "severity": error_context.severity.value,
            "phase": error_context.phase,
            "step": error_context.step,
            "component": error_context.component,
            "operation": error_context.operation,
            "suggested_actions": [action.value for action in error_context.suggested_actions],
            "can_retry": error_context.can_retry,
            "retry_count": error_context.retry_count
        }

        if error_context.severity == ErrorSeverity.CRITICAL:
            self.logger.critical(
                error_context.error_message,
                extra=log_data
            )
        elif error_context.severity == ErrorSeverity.HIGH:
            self.logger.error(
                error_context.error_message,
                extra=log_data
            )
        elif error_context.severity == ErrorSeverity.MEDIUM:
            self.logger.warning(
                error_context.error_message,
                extra=log_data
            )
        else:
            self.logger.info(
                error_context.error_message,
                extra=log_data
            )


# Custom exceptions for different error categories

class SystemRequirementsError(ErrorHandlingError):
    """Exception for system requirement failures."""
    pass


class NetworkConnectivityError(ErrorHandlingError):
    """Exception for network connectivity issues."""
    pass


class PermissionDeniedError(ErrorHandlingError):
    """Exception for permission denied errors."""
    pass


class ServiceUnavailableError(ErrorHandlingError):
    """Exception for service availability issues."""
    pass


class ConfigurationError(ErrorHandlingError):
    """Exception for configuration issues."""
    pass


class DiskSpaceError(ErrorHandlingError):
    """Exception for disk space issues."""
    pass


class DependencyMissingError(ErrorHandlingError):
    """Exception for missing dependencies."""
    pass


class InstallationTimeoutError(ErrorHandlingError):
    """Exception for installation timeouts."""
    pass


class InstallationCancellationError(ErrorHandlingError):
    """Exception for installation cancellations."""
    pass


class DataCorruptionError(ErrorHandlingError):
    """Exception for data corruption issues."""
    pass


class VersionConflictError(ErrorHandlingError):
    """Exception for version conflicts."""
    pass