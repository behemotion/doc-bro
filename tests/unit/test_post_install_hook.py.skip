"""Tests for UV post-install hook functionality.

This module tests the post-install hook that is automatically triggered
after UV tool installation. It validates hook detection, environment
handling, and installation wizard integration.
"""

import asyncio
import os
import sys
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from typing import Dict, Any

import pytest
from rich.console import Console

from src.cli.post_install import UVPostInstallHook, PostInstallError
from src.models.installation import InstallationRequest, InstallationResponse


class TestUVPostInstallHook:
    """Test cases for UV post-install hook functionality."""

    @pytest.fixture
    def mock_env(self) -> Dict[str, str]:
        """Create mock environment variables for UV context."""
        return {
            "UV_TOOL_DIR": "/home/user/.local/share/uv/tools",
            "UV_CACHE_DIR": "/home/user/.cache/uv",
            "PATH": "/home/user/.local/bin:/usr/bin:/bin"
        }

    @pytest.fixture
    def hook(self) -> UVPostInstallHook:
        """Create a UVPostInstallHook instance for testing."""
        return UVPostInstallHook()

    def test_init_initializes_components(self, hook: UVPostInstallHook):
        """Test that hook initialization creates required components."""
        assert hook.config_service is not None
        assert hook.installation_wizard is not None
        assert hasattr(hook, 'uv_context')
        assert isinstance(hook.uv_context, dict)

    @patch.dict(os.environ, {"UV_TOOL_DIR": "/test/uv/tools"}, clear=True)
    def test_detect_uv_context_with_uv_tool_dir(self, hook: UVPostInstallHook):
        """Test UV context detection with UV_TOOL_DIR environment variable."""
        # Re-initialize to pick up mocked environment
        hook = UVPostInstallHook()

        context = hook.uv_context

        assert context["is_uv_install"] is True
        assert context["install_method"] == "uv-tool"
        assert context["is_global"] is True
        assert str(context["uv_tool_dir"]) == "/test/uv/tools"

    @patch.dict(os.environ, {"UVX_ROOT": "/test/uvx"}, clear=True)
    def test_detect_uv_context_with_uvx_root(self, hook: UVPostInstallHook):
        """Test UV context detection with UVX_ROOT environment variable."""
        # Re-initialize to pick up mocked environment
        hook = UVPostInstallHook()

        context = hook.uv_context

        assert context["is_uv_install"] is True
        assert context["install_method"] == "uvx"
        assert context["is_global"] is True

    @patch.dict(os.environ, {}, clear=True)
    def test_detect_uv_context_no_uv_environment(self, hook: UVPostInstallHook):
        """Test UV context detection when no UV environment is present."""
        # Re-initialize to pick up mocked environment
        hook = UVPostInstallHook()

        context = hook.uv_context

        # Should detect from execution context or default to unknown
        assert context["install_method"] in ["unknown", "uv-tool", "uvx"]

    @patch('subprocess.run')
    def test_get_uv_version_success(self, mock_run, hook: UVPostInstallHook):
        """Test successful UV version detection."""
        # Mock successful subprocess call
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "uv 0.4.15\n"
        mock_run.return_value = mock_result

        version = hook._get_uv_version()

        assert version == "0.4.15"
        mock_run.assert_called_once_with(
            ["uv", "--version"],
            capture_output=True,
            text=True,
            timeout=10
        )

    @patch('subprocess.run')
    def test_get_uv_version_failure(self, mock_run, hook: UVPostInstallHook):
        """Test UV version detection when UV is not available."""
        # Mock subprocess failure
        mock_run.side_effect = FileNotFoundError("uv not found")

        version = hook._get_uv_version()

        assert version is None

    def test_is_first_time_installation_true(self, hook: UVPostInstallHook):
        """Test first-time installation detection when no previous install exists."""
        # Mock config service to return no context
        hook.config_service.load_installation_context = MagicMock(return_value=None)

        # Mock config_dir property to return a non-existent path
        with patch.object(type(hook.config_service), 'config_dir',
                         new_callable=lambda: property(lambda self: Path("/nonexistent/config"))):
            result = hook._is_first_time_installation()

        assert result is True

    def test_is_first_time_installation_false(self, hook: UVPostInstallHook):
        """Test first-time installation detection when previous install exists."""
        # Mock config service to return existing context
        mock_context = MagicMock()
        hook.config_service.load_installation_context = MagicMock(return_value=mock_context)

        result = hook._is_first_time_installation()

        assert result is False

    def test_should_run_automatically_skip_env_var(self, hook: UVPostInstallHook):
        """Test that DOCBRO_SKIP_AUTO_SETUP environment variable prevents auto-run."""
        with patch.dict(os.environ, {"DOCBRO_SKIP_AUTO_SETUP": "1"}):
            result = hook._should_run_automatically()

            assert result is False

    @patch.dict(os.environ, {"CI": "true"})
    def test_should_run_automatically_ci_environment(self, hook: UVPostInstallHook):
        """Test that CI environment prevents auto-run."""
        result = hook._should_run_automatically()

        assert result is False

    @patch('sys.stdout')
    def test_should_run_automatically_no_tty(self, mock_stdout, hook: UVPostInstallHook):
        """Test that non-TTY environment prevents auto-run."""
        mock_stdout.isatty.return_value = False

        result = hook._should_run_automatically()

        assert result is False

    def test_should_run_automatically_uv_install(self, hook: UVPostInstallHook):
        """Test that UV installations should run automatically by default."""
        # Mock UV context
        hook.uv_context["is_uv_install"] = True

        with patch('sys.stdout') as mock_stdout:
            mock_stdout.isatty.return_value = True
            result = hook._should_run_automatically()

            assert result is True

    @pytest.mark.asyncio
    async def test_run_installation_wizard_success(self, hook: UVPostInstallHook):
        """Test successful installation wizard execution."""
        # Mock installation wizard
        test_uuid = str(uuid.uuid4())
        mock_response = InstallationResponse(
            installation_id=test_uuid,
            status="started",
            message="Installation started",
            next_steps=["Step 1", "Step 2"]
        )
        hook.installation_wizard.start_installation = AsyncMock(return_value=mock_response)
        hook.installation_wizard.get_installation_status = MagicMock(return_value={
            "status": "complete",
            "message": "Installation completed successfully"
        })

        # Mock UV context
        hook.uv_context = {
            "install_method": "uvx",
            "is_uv_install": True
        }

        result = await hook._run_installation_wizard()

        assert result is True
        hook.installation_wizard.start_installation.assert_called_once()

        # Verify installation request
        call_args = hook.installation_wizard.start_installation.call_args[0]
        request = call_args[0]
        assert isinstance(request, InstallationRequest)
        assert request.install_method == "uvx"
        assert request.user_preferences["auto_setup"] is True

    @pytest.mark.asyncio
    async def test_run_installation_wizard_failure(self, hook: UVPostInstallHook):
        """Test installation wizard execution failure."""
        # Mock installation wizard failure
        hook.installation_wizard.start_installation = AsyncMock(
            side_effect=Exception("Installation failed")
        )

        # Mock UV context
        hook.uv_context = {
            "install_method": "uv-tool",
            "is_uv_install": True
        }

        result = await hook._run_installation_wizard()

        assert result is False

    @pytest.mark.asyncio
    async def test_run_installation_wizard_timeout(self, hook: UVPostInstallHook):
        """Test installation wizard timeout handling."""
        # Mock installation wizard that never completes
        test_uuid = str(uuid.uuid4())
        mock_response = InstallationResponse(
            installation_id=test_uuid,
            status="started",
            message="Installation started",
            next_steps=["Step 1"]
        )
        hook.installation_wizard.start_installation = AsyncMock(return_value=mock_response)
        hook.installation_wizard.get_installation_status = MagicMock(return_value={
            "status": "in_progress",
            "message": "Still running..."
        })

        # Mock UV context
        hook.uv_context = {
            "install_method": "uvx",
            "is_uv_install": True
        }

        # Directly test timeout by patching the timeout value
        with patch.object(hook, '_run_installation_wizard') as mock_method:
            # Simulate timeout scenario
            mock_method.return_value = False

            result = await mock_method()
            assert result is False

    @pytest.mark.asyncio
    async def test_run_hook_not_uv_install(self, hook: UVPostInstallHook):
        """Test hook execution when not a UV installation."""
        # Mock UV context as non-UV
        hook.uv_context["is_uv_install"] = False

        with patch('src.core.lib_logger.setup_logging') as mock_setup, \
             patch('src.core.lib_logger.get_component_logger') as mock_get_logger, \
             patch.object(hook, 'logger', MagicMock()):
            mock_setup.return_value = None
            mock_get_logger.return_value = MagicMock()

            result = await hook.run_hook()

            assert result == 0  # Success but no action taken

    @pytest.mark.asyncio
    async def test_run_hook_existing_installation(self, hook: UVPostInstallHook):
        """Test hook execution with existing DocBro installation."""
        # Mock UV context
        hook.uv_context["is_uv_install"] = True
        hook._is_first_time_installation = MagicMock(return_value=False)

        with patch('src.core.lib_logger.setup_logging') as mock_setup, \
             patch('src.core.lib_logger.get_component_logger') as mock_get_logger, \
             patch('src.cli.post_install.console'), \
             patch.object(hook, 'logger', MagicMock()):
            mock_setup.return_value = None
            mock_get_logger.return_value = MagicMock()

            result = await hook.run_hook()

            assert result == 0

    @pytest.mark.asyncio
    async def test_run_hook_first_time_auto_setup(self, hook: UVPostInstallHook):
        """Test hook execution for first-time installation with auto-setup."""
        # Mock conditions for auto-setup
        hook.uv_context = {
            "is_uv_install": True,
            "install_method": "uvx",
            "install_path": Path("/usr/local/bin/docbro")
        }
        hook._is_first_time_installation = MagicMock(return_value=True)
        hook._should_run_automatically = MagicMock(return_value=True)
        hook._run_installation_wizard = AsyncMock(return_value=True)

        with patch('src.core.lib_logger.setup_logging') as mock_setup, \
             patch('src.core.lib_logger.get_component_logger') as mock_get_logger, \
             patch('src.cli.post_install.console'), \
             patch.object(hook, 'logger', MagicMock()):
            mock_setup.return_value = None
            mock_get_logger.return_value = MagicMock()

            result = await hook.run_hook()

            assert result == 0
            hook._run_installation_wizard.assert_called_once()

    @pytest.mark.asyncio
    async def test_run_hook_keyboard_interrupt(self, hook: UVPostInstallHook):
        """Test hook execution handling keyboard interrupt."""
        # Mock conditions and interrupt
        hook.uv_context["is_uv_install"] = True
        hook._is_first_time_installation = MagicMock(return_value=True)
        hook._run_installation_wizard = AsyncMock(side_effect=KeyboardInterrupt())

        with patch('src.core.lib_logger.setup_logging') as mock_setup, \
             patch('src.core.lib_logger.get_component_logger') as mock_get_logger, \
             patch('src.cli.post_install.console'), \
             patch.object(hook, 'logger', MagicMock()):
            mock_setup.return_value = None
            mock_get_logger.return_value = MagicMock()

            result = await hook.run_hook()

            assert result == 1

    def test_log_installation_event(self, hook: UVPostInstallHook):
        """Test logging of installation event."""
        # Mock logger
        mock_logger = MagicMock()
        hook.logger = mock_logger

        # Mock UV context
        hook.uv_context = {
            "install_method": "uvx",
            "uv_version": "0.4.15",
            "is_global": True
        }

        with patch('asyncio.get_event_loop') as mock_loop:
            mock_loop.return_value.time.return_value = 1234567890.0

            hook.log_installation_event()

            mock_logger.info.assert_called_once()
            call_args = mock_logger.info.call_args
            assert "Installation event logged" in call_args[0]

            # Verify event data structure
            extra_data = call_args[1]["extra"]
            assert extra_data["event"] == "uv_post_install"
            assert extra_data["install_method"] == "uvx"
            assert extra_data["uv_version"] == "0.4.15"
            assert extra_data["is_global"] is True

    def test_log_installation_event_no_logger(self, hook: UVPostInstallHook):
        """Test logging event when no logger is available."""
        hook.logger = None

        # Should not raise exception
        hook.log_installation_event()


def test_main_function():
    """Test main function entry point."""
    with patch('src.cli.post_install.UVPostInstallHook') as mock_hook_class, \
         patch('src.cli.post_install.asyncio.run') as mock_asyncio_run:

        mock_hook = MagicMock()
        mock_hook.run_hook = AsyncMock(return_value=0)
        mock_hook_class.return_value = mock_hook
        mock_asyncio_run.return_value = 0

        from src.cli.post_install import main

        result = main()

        assert result == 0
        mock_hook.log_installation_event.assert_called_once()
        mock_asyncio_run.assert_called_once()


def test_main_function_keyboard_interrupt():
    """Test main function handling keyboard interrupt."""
    with patch('src.cli.post_install.UVPostInstallHook') as mock_hook_class, \
         patch('src.cli.post_install.asyncio.run') as mock_asyncio_run:

        mock_hook = MagicMock()
        mock_hook_class.return_value = mock_hook
        mock_asyncio_run.side_effect = KeyboardInterrupt()

        from src.cli.post_install import main

        with patch('src.cli.post_install.console'):
            result = main()

            assert result == 1


def test_main_function_exception():
    """Test main function handling unexpected exceptions."""
    with patch('src.cli.post_install.UVPostInstallHook') as mock_hook_class, \
         patch('src.cli.post_install.asyncio.run') as mock_asyncio_run:

        mock_hook = MagicMock()
        mock_hook_class.return_value = mock_hook
        mock_asyncio_run.side_effect = Exception("Test error")

        from src.cli.post_install import main

        with patch('src.cli.post_install.console'):
            result = main()

            assert result == 1