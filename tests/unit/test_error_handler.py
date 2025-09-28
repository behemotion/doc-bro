"""Unit tests for the comprehensive error handling service."""

import pytest
import asyncio
import json
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, AsyncMock
from datetime import datetime

from src.services.error_handler import (
    ErrorHandlerService,
    ErrorCategory,
    ErrorSeverity,
    RecoveryAction,
    ErrorContext,
    InstallationSnapshot,
    SystemRequirementsError,
    NetworkConnectivityError,
    PermissionDeniedError,
    ServiceUnavailableError,
    ConfigurationError,
    DiskSpaceError,
    RollbackError
)
from src.services.config import ConfigService
from src.services.installation_wizard import InstallationWizardService


@pytest.fixture
def error_handler():
    """Create error handler service instance."""
    with patch('src.services.error_handler.ConfigService'):
        handler = ErrorHandlerService()
        return handler


@pytest.fixture
def mock_wizard():
    """Create mock installation wizard."""
    wizard = Mock(spec=InstallationWizardService)
    wizard.installation_state = Mock()
    wizard.installation_state.current_phase = "service_setup"
    wizard.installation_state.current_step = "detecting_services"
    wizard.installation_state.mark_error = Mock()
    wizard.installation_state.model_dump.return_value = {
        "current_phase": "service_setup",
        "current_step": "detecting_services",
        "progress_percentage": 50.0
    }
    wizard.installation_profile = Mock()
    wizard.installation_profile.model_dump.return_value = {
        "install_method": "uvx",
        "version": "1.0.0",
        "python_version": "3.13.0"
    }
    return wizard


class TestErrorCategorization:
    """Test error categorization logic."""

    def test_categorize_network_error(self, error_handler):
        """Test categorization of network errors."""
        error = ConnectionError("Connection refused")
        category = error_handler.categorize_error(error)
        assert category == ErrorCategory.NETWORK_CONNECTIVITY

    def test_categorize_permission_error(self, error_handler):
        """Test categorization of permission errors."""
        error = PermissionError("Access denied")
        category = error_handler.categorize_error(error)
        assert category == ErrorCategory.PERMISSION_DENIED

    def test_categorize_timeout_error(self, error_handler):
        """Test categorization of timeout errors."""
        error = TimeoutError("Operation timed out")
        category = error_handler.categorize_error(error)
        assert category == ErrorCategory.TIMEOUT

    def test_categorize_with_context(self, error_handler):
        """Test categorization with additional context."""
        error = ValueError("Invalid configuration")
        context = "config file parsing failed"
        category = error_handler.categorize_error(error, context)
        assert category == ErrorCategory.CONFIGURATION

    def test_categorize_unknown_error(self, error_handler):
        """Test categorization of unknown errors."""
        error = RuntimeError("Something weird happened")
        category = error_handler.categorize_error(error)
        assert category == ErrorCategory.UNKNOWN


class TestSeverityDetermination:
    """Test error severity determination."""

    def test_determine_critical_severity(self, error_handler):
        """Test critical severity determination."""
        severity = error_handler.determine_severity(ErrorCategory.SYSTEM_REQUIREMENTS)
        assert severity == ErrorSeverity.CRITICAL

        severity = error_handler.determine_severity(ErrorCategory.DISK_SPACE)
        assert severity == ErrorSeverity.CRITICAL

    def test_determine_high_severity_in_critical_phase(self, error_handler):
        """Test high severity in critical phases."""
        severity = error_handler.determine_severity(
            ErrorCategory.NETWORK_CONNECTIVITY,
            phase="system_check"
        )
        assert severity == ErrorSeverity.HIGH

    def test_determine_medium_severity_for_services(self, error_handler):
        """Test medium severity for service issues."""
        severity = error_handler.determine_severity(ErrorCategory.SERVICE_UNAVAILABLE)
        assert severity == ErrorSeverity.MEDIUM

    def test_determine_high_severity_for_timeouts(self, error_handler):
        """Test high severity for timeouts."""
        severity = error_handler.determine_severity(ErrorCategory.TIMEOUT)
        assert severity == ErrorSeverity.HIGH


class TestRecoveryActions:
    """Test recovery action suggestions."""

    def test_suggest_actions_for_critical_system_error(self, error_handler):
        """Test recovery actions for critical system errors."""
        actions = error_handler.suggest_recovery_actions(
            ErrorCategory.SYSTEM_REQUIREMENTS,
            ErrorSeverity.CRITICAL,
            {}
        )
        assert RecoveryAction.MANUAL in actions
        assert RecoveryAction.ABORT in actions

    def test_suggest_actions_for_network_error(self, error_handler):
        """Test recovery actions for network errors."""
        actions = error_handler.suggest_recovery_actions(
            ErrorCategory.NETWORK_CONNECTIVITY,
            ErrorSeverity.HIGH,
            {}
        )
        assert RecoveryAction.RETRY in actions
        assert RecoveryAction.SKIP in actions

    def test_suggest_actions_for_timeout(self, error_handler):
        """Test recovery actions for timeouts."""
        actions = error_handler.suggest_recovery_actions(
            ErrorCategory.TIMEOUT,
            ErrorSeverity.HIGH,
            {}
        )
        assert RecoveryAction.RETRY in actions
        assert RecoveryAction.ROLLBACK in actions

    def test_suggest_actions_for_data_corruption(self, error_handler):
        """Test recovery actions for data corruption."""
        actions = error_handler.suggest_recovery_actions(
            ErrorCategory.DATA_CORRUPTION,
            ErrorSeverity.HIGH,
            {}
        )
        assert RecoveryAction.ROLLBACK in actions
        assert RecoveryAction.CLEANUP in actions


class TestUserFriendlyMessages:
    """Test user-friendly message generation."""

    def test_create_system_requirements_message(self, error_handler):
        """Test system requirements error message."""
        message = error_handler.create_user_friendly_message(
            ErrorCategory.SYSTEM_REQUIREMENTS,
            "Python 3.12 not supported"
        )
        assert "system doesn't meet" in message.lower()
        assert "python 3.13+" in message.lower()
        assert "suggested actions" in message.lower()

    def test_create_network_message(self, error_handler):
        """Test network error message."""
        message = error_handler.create_user_friendly_message(
            ErrorCategory.NETWORK_CONNECTIVITY,
            "Connection refused"
        )
        assert "connect to required services" in message.lower()
        assert "internet connection" in message.lower()

    def test_create_permission_message(self, error_handler):
        """Test permission error message."""
        message = error_handler.create_user_friendly_message(
            ErrorCategory.PERMISSION_DENIED,
            "Access denied"
        )
        assert "permission" in message.lower()
        assert "access" in message.lower()

    def test_create_service_message(self, error_handler):
        """Test service unavailable message."""
        message = error_handler.create_user_friendly_message(
            ErrorCategory.SERVICE_UNAVAILABLE,
            "Docker not running"
        )
        assert "external services" in message.lower()
        assert "docker" in message.lower()


@pytest.mark.asyncio
class TestErrorHandling:
    """Test comprehensive error handling."""

    async def test_handle_error_basic(self, error_handler):
        """Test basic error handling."""
        error = ConnectionError("Network connection failed")
        context = {
            "phase": "system_check",
            "step": "validate_python",
            "component": "validator"
        }

        with patch.object(error_handler, '_gather_system_state', new_callable=AsyncMock) as mock_system, \
             patch.object(error_handler, '_log_error', new_callable=AsyncMock) as mock_log:

            mock_system.return_value = {"memory": "8GB"}

            error_context = await error_handler.handle_error(error, context)

            assert error_context.error_message == "Network connection failed"
            assert error_context.phase == "system_check"
            assert error_context.step == "validate_python"
            assert error_context.component == "validator"
            assert error_context.category == ErrorCategory.NETWORK_CONNECTIVITY
            assert len(error_context.suggested_actions) > 0
            assert mock_log.called

    async def test_handle_error_with_wizard(self, error_handler, mock_wizard):
        """Test error handling with installation wizard integration."""
        error = NetworkConnectivityError("Network unreachable")

        with patch.object(error_handler, '_gather_system_state', new_callable=AsyncMock) as mock_system, \
             patch.object(error_handler, '_log_error', new_callable=AsyncMock):

            mock_system.return_value = {}

            error_context = await error_handler.handle_error(error, {}, mock_wizard)

            assert error_context.category == ErrorCategory.NETWORK_CONNECTIVITY
            assert mock_wizard.installation_state.mark_error.called

    async def test_handle_error_with_progress_callback(self, error_handler):
        """Test error handling with progress callback."""
        callback = Mock()
        error_handler.set_progress_callback(callback)

        error = PermissionError("Access denied")

        with patch.object(error_handler, '_gather_system_state', new_callable=AsyncMock) as mock_system, \
             patch.object(error_handler, '_log_error', new_callable=AsyncMock):

            mock_system.return_value = {}

            await error_handler.handle_error(error)

            assert callback.called
            call_args = callback.call_args[0][0]
            assert call_args["type"] == "error"
            assert "error_id" in call_args


@pytest.mark.asyncio
class TestSnapshotCreation:
    """Test installation snapshot creation."""

    async def test_create_snapshot_basic(self, error_handler):
        """Test basic snapshot creation."""
        with patch.object(error_handler, '_capture_filesystem_state', new_callable=AsyncMock), \
             patch.object(error_handler, '_capture_service_state', new_callable=AsyncMock) as mock_services, \
             patch.object(error_handler, '_persist_snapshot', new_callable=AsyncMock):

            mock_services.return_value = {"docker": {"available": True}}

            snapshot_id = await error_handler.create_snapshot(
                "system_check",
                "validate_python",
                "Test snapshot"
            )

            assert snapshot_id.startswith("snap_")
            assert snapshot_id in error_handler.active_snapshots

            snapshot = error_handler.active_snapshots[snapshot_id]
            assert snapshot.phase == "system_check"
            assert snapshot.step == "validate_python"
            assert snapshot.description == "Test snapshot"

    async def test_create_snapshot_with_wizard(self, error_handler, mock_wizard):
        """Test snapshot creation with wizard state capture."""
        with patch.object(error_handler, '_capture_filesystem_state', new_callable=AsyncMock), \
             patch.object(error_handler, '_capture_service_state', new_callable=AsyncMock) as mock_services, \
             patch.object(error_handler, '_persist_snapshot', new_callable=AsyncMock):

            mock_services.return_value = {"docker": {"available": True}}

            snapshot_id = await error_handler.create_snapshot(
                "service_setup",
                "configure_services",
                installation_wizard=mock_wizard
            )

            snapshot = error_handler.active_snapshots[snapshot_id]
            assert snapshot.installation_state is not None
            assert snapshot.installation_profile is not None

    async def test_create_snapshot_filesystem_capture(self, error_handler):
        """Test filesystem state capture during snapshot."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir)

            # Mock config service to use temp directory
            error_handler.config_service.config_dir = temp_path / "config"
            error_handler.config_service.data_dir = temp_path / "data"
            error_handler.config_service.config_dir.mkdir(parents=True)
            error_handler.config_service.data_dir.mkdir(parents=True)

            # Create some test files
            (error_handler.config_service.config_dir / "test.json").write_text('{"test": true}')
            (error_handler.config_service.data_dir / "data.db").write_text("test data")

            snapshot = InstallationSnapshot(phase="test", step="capture")

            await error_handler._capture_filesystem_state(snapshot)

            assert len(snapshot.created_files) >= 2
            file_paths = [str(f) for f in snapshot.created_files]
            assert any("test.json" in path for path in file_paths)
            assert any("data.db" in path for path in file_paths)


@pytest.mark.asyncio
class TestRollback:
    """Test rollback functionality."""

    async def test_rollback_to_snapshot_success(self, error_handler):
        """Test successful rollback to snapshot."""
        # Create a test snapshot
        snapshot = InstallationSnapshot(
            phase="test_phase",
            step="test_step",
            description="Test rollback"
        )
        snapshot_id = snapshot.snapshot_id
        error_handler.active_snapshots[snapshot_id] = snapshot

        with patch.object(error_handler, '_rollback_filesystem', new_callable=AsyncMock), \
             patch.object(error_handler, '_rollback_configuration', new_callable=AsyncMock), \
             patch.object(error_handler, '_rollback_wizard_state', new_callable=AsyncMock):

            result = await error_handler.rollback_to_snapshot(snapshot_id)

            assert result is True

    async def test_rollback_partial_failure_ok(self, error_handler):
        """Test rollback with partial failure when partial_ok=True."""
        snapshot = InstallationSnapshot(
            phase="test_phase",
            step="test_step"
        )
        snapshot_id = snapshot.snapshot_id
        error_handler.active_snapshots[snapshot_id] = snapshot

        async def failing_rollback(*args):
            raise Exception("Rollback failed")

        with patch.object(error_handler, '_rollback_filesystem', new_callable=AsyncMock, side_effect=failing_rollback), \
             patch.object(error_handler, '_rollback_configuration', new_callable=AsyncMock), \
             patch.object(error_handler, '_rollback_wizard_state', new_callable=AsyncMock):

            result = await error_handler.rollback_to_snapshot(snapshot_id, partial_ok=True)

            assert result is True  # Should succeed with partial_ok=True

    async def test_rollback_failure_not_ok(self, error_handler):
        """Test rollback failure when partial_ok=False."""
        snapshot = InstallationSnapshot(
            phase="test_phase",
            step="test_step"
        )
        snapshot_id = snapshot.snapshot_id
        error_handler.active_snapshots[snapshot_id] = snapshot

        async def failing_rollback(*args):
            raise Exception("Rollback failed")

        with patch.object(error_handler, '_rollback_filesystem', new_callable=AsyncMock, side_effect=failing_rollback), \
             patch.object(error_handler, '_rollback_configuration', new_callable=AsyncMock), \
             patch.object(error_handler, '_rollback_wizard_state', new_callable=AsyncMock):

            with pytest.raises(RollbackError):
                await error_handler.rollback_to_snapshot(snapshot_id, partial_ok=False)

    async def test_rollback_nonexistent_snapshot(self, error_handler):
        """Test rollback to nonexistent snapshot."""
        with patch.object(error_handler, '_load_snapshot', new_callable=AsyncMock, return_value=None):
            with pytest.raises(RollbackError, match="Snapshot .* not found"):
                await error_handler.rollback_to_snapshot("nonexistent", partial_ok=False)


@pytest.mark.asyncio
class TestTimeoutHandling:
    """Test timeout handling."""

    async def test_handle_timeout(self, error_handler, mock_wizard):
        """Test timeout handling."""
        with patch.object(error_handler, '_gather_system_state', new_callable=AsyncMock) as mock_system, \
             patch.object(error_handler, '_log_error', new_callable=AsyncMock):

            mock_system.return_value = {}

            error_context = await error_handler.handle_timeout(
                "test_operation",
                30.0,
                mock_wizard
            )

            assert error_context.category == ErrorCategory.TIMEOUT
            assert "30" in error_context.error_message
            assert "test_operation" in error_context.error_message


@pytest.mark.asyncio
class TestCancellationHandling:
    """Test cancellation handling."""

    async def test_handle_cancellation(self, error_handler, mock_wizard):
        """Test cancellation handling."""
        with patch.object(error_handler, 'handle_error', new_callable=AsyncMock) as mock_handle, \
             patch.object(error_handler, 'cleanup_partial_installation', new_callable=AsyncMock) as mock_cleanup:

            mock_handle.return_value = Mock()

            await error_handler.handle_cancellation("User requested", mock_wizard)

            assert mock_handle.called
            assert mock_cleanup.called

            # Check that the error was categorized as cancellation
            call_args = mock_handle.call_args
            error = call_args[0][0]
            assert isinstance(error, InterruptedError)
            assert "cancelled" in str(error).lower()

    async def test_handle_cancellation_with_cleanup_failure(self, error_handler, mock_wizard):
        """Test cancellation handling when cleanup fails."""
        with patch.object(error_handler, 'handle_error', new_callable=AsyncMock) as mock_handle, \
             patch.object(error_handler, 'cleanup_partial_installation', new_callable=AsyncMock) as mock_cleanup:

            mock_handle.return_value = Mock()
            mock_cleanup.side_effect = Exception("Cleanup failed")

            # Should not raise exception even if cleanup fails
            await error_handler.handle_cancellation("User requested", mock_wizard)

            assert mock_handle.called
            assert mock_cleanup.called


@pytest.mark.asyncio
class TestPartialInstallationCleanup:
    """Test partial installation cleanup."""

    async def test_cleanup_partial_installation(self, error_handler, mock_wizard):
        """Test partial installation cleanup."""
        # Add some test snapshots
        snapshot1 = InstallationSnapshot(phase="test1", step="step1")
        snapshot2 = InstallationSnapshot(phase="test2", step="step2")
        error_handler.active_snapshots[snapshot1.snapshot_id] = snapshot1
        error_handler.active_snapshots[snapshot2.snapshot_id] = snapshot2

        with patch.object(error_handler, '_cleanup_snapshot', new_callable=AsyncMock) as mock_cleanup:
            await error_handler.cleanup_partial_installation(mock_wizard)

            # Should clean up all snapshots
            assert mock_cleanup.call_count == 2
            assert mock_wizard.rollback_installation.called

    async def test_cleanup_with_callback(self, error_handler):
        """Test cleanup with registered callbacks."""
        callback1 = Mock()
        callback2 = Mock()

        error_handler.add_cleanup_callback(callback1)
        error_handler.add_cleanup_callback(callback2)

        with patch.object(error_handler, '_cleanup_snapshot', new_callable=AsyncMock):
            await error_handler.cleanup_partial_installation()

            assert callback1.called
            assert callback2.called


class TestErrorHistory:
    """Test error history tracking."""

    def test_get_error_history(self, error_handler):
        """Test error history retrieval."""
        # Add some test errors
        error1 = ErrorContext(
            category=ErrorCategory.NETWORK_CONNECTIVITY,
            severity=ErrorSeverity.HIGH,
            error_message="Network error 1",
            user_message="Network problem 1"
        )
        error2 = ErrorContext(
            category=ErrorCategory.CONFIGURATION,
            severity=ErrorSeverity.MEDIUM,
            error_message="Config error 2",
            user_message="Config problem 2"
        )

        error_handler.error_history = [error1, error2]

        # Test getting all history
        history = error_handler.get_error_history()
        assert len(history) == 2
        assert history[0] == error1
        assert history[1] == error2

        # Test getting limited history
        history = error_handler.get_error_history(limit=1)
        assert len(history) == 1
        assert history[0] == error2  # Should get the last one

    def test_get_active_snapshots(self, error_handler):
        """Test active snapshots retrieval."""
        snapshot1 = InstallationSnapshot(phase="test1", step="step1")
        snapshot2 = InstallationSnapshot(phase="test2", step="step2")

        error_handler.active_snapshots[snapshot1.snapshot_id] = snapshot1
        error_handler.active_snapshots[snapshot2.snapshot_id] = snapshot2

        snapshot_ids = error_handler.get_active_snapshots()
        assert len(snapshot_ids) == 2
        assert snapshot1.snapshot_id in snapshot_ids
        assert snapshot2.snapshot_id in snapshot_ids


class TestCustomExceptions:
    """Test custom exception classes."""

    def test_custom_exception_inheritance(self):
        """Test that custom exceptions inherit from ErrorHandlingError."""
        from src.services.error_handler import (
            SystemRequirementsError, NetworkConnectivityError,
            PermissionDeniedError, ServiceUnavailableError,
            ConfigurationError, DiskSpaceError
        )

        exceptions = [
            SystemRequirementsError,
            NetworkConnectivityError,
            PermissionDeniedError,
            ServiceUnavailableError,
            ConfigurationError,
            DiskSpaceError
        ]

        for exc_class in exceptions:
            # Should be able to instantiate and raise
            exc = exc_class("Test message")
            assert str(exc) == "Test message"

            # Should inherit from ErrorHandlingError
            from src.services.error_handler import ErrorHandlingError
            assert issubclass(exc_class, ErrorHandlingError)

    def test_custom_exceptions_can_be_raised(self):
        """Test that custom exceptions can be raised and caught."""
        with pytest.raises(SystemRequirementsError) as exc_info:
            raise SystemRequirementsError("Python version incompatible")

        assert "Python version incompatible" in str(exc_info.value)


class TestIntegration:
    """Integration tests for error handler service."""

    def test_progress_callback_integration(self, error_handler):
        """Test progress callback integration."""
        callback_calls = []

        def test_callback(data):
            callback_calls.append(data)

        error_handler.set_progress_callback(test_callback)

        # Test that callbacks are called during various operations
        assert error_handler.progress_callback == test_callback

    def test_cleanup_callback_integration(self, error_handler):
        """Test cleanup callback integration."""
        cleanup_calls = []

        def cleanup_callback():
            cleanup_calls.append("cleaned")

        error_handler.add_cleanup_callback(cleanup_callback)

        assert cleanup_callback in error_handler.cleanup_callbacks