"""Integration test for UV tool management commands."""

import pytest
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, Mock, MagicMock
from datetime import datetime

from src.services.config import ConfigService
from src.models.installation import InstallationContext


@pytest.mark.integration
class TestUVToolManagementIntegration:
    """Test UV tool management integration according to quickstart scenario #6."""

    @pytest.fixture
    def temp_home(self):
        """Create temporary home directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_platformdirs(self, temp_home):
        """Mock platformdirs to use temp directory."""
        with patch('platformdirs.user_config_dir') as mock_config, \
             patch('platformdirs.user_data_dir') as mock_data, \
             patch('platformdirs.user_cache_dir') as mock_cache:

            mock_config.return_value = str(temp_home / ".config" / "docbro")
            mock_data.return_value = str(temp_home / ".local" / "share" / "docbro")
            mock_cache.return_value = str(temp_home / ".cache" / "docbro")
            yield

    @pytest.fixture
    def mock_uv_commands(self):
        """Mock UV command execution for tool management testing."""
        with patch('subprocess.run') as mock_run, \
             patch('shutil.which') as mock_which:

            # Mock UV available
            mock_which.side_effect = lambda cmd: {
                'uv': '/home/user/.local/bin/uv',
                'docbro': '/home/user/.local/bin/docbro'
            }.get(cmd)

            # Store commands to track what was called
            commands_called = []

            def mock_subprocess_run(*args, **kwargs):
                """Track subprocess calls and return appropriate responses."""
                cmd = args[0] if args else kwargs.get('args', [])
                commands_called.append(' '.join(cmd))

                # Mock uv tool list
                if 'uv tool list' in ' '.join(cmd):
                    return Mock(
                        returncode=0,
                        stdout="docbro v1.0.0\n  - docbro\n",
                        stderr=""
                    )

                # Mock uv tool update
                elif 'uv tool update docbro' in ' '.join(cmd):
                    return Mock(
                        returncode=0,
                        stdout="Updated docbro v1.0.0 -> v1.1.0\n",
                        stderr=""
                    )

                # Mock uv tool uninstall
                elif 'uv tool uninstall docbro' in ' '.join(cmd):
                    return Mock(
                        returncode=0,
                        stdout="Uninstalled docbro\n",
                        stderr=""
                    )

                # Mock docbro --version before update
                elif 'docbro --version' in ' '.join(cmd) and len(commands_called) <= 2:
                    return Mock(
                        returncode=0,
                        stdout="docbro 1.0.0 (installed via uvx)\n",
                        stderr=""
                    )

                # Mock docbro --version after update
                elif 'docbro --version' in ' '.join(cmd):
                    return Mock(
                        returncode=0,
                        stdout="docbro 1.1.0 (installed via uvx)\n",
                        stderr=""
                    )

                # Mock which docbro after uninstall
                elif 'which docbro' in ' '.join(cmd):
                    if 'uv tool uninstall docbro' in '\n'.join(commands_called):
                        return Mock(
                            returncode=1,
                            stdout="",
                            stderr="docbro: command not found"
                        )
                    else:
                        return Mock(
                            returncode=0,
                            stdout="/home/user/.local/bin/docbro\n",
                            stderr=""
                        )

                # Default: command not found or error
                return Mock(returncode=1, stdout="", stderr="Command not found")

            mock_run.side_effect = mock_subprocess_run

            yield {
                'mock_run': mock_run,
                'mock_which': mock_which,
                'commands_called': commands_called
            }

    def test_uv_tool_list_shows_docbro(self, mock_platformdirs, temp_home, mock_uv_commands):
        """Test that 'uv tool list' shows docbro in the list."""
        from src.services.uv_tool_management import UVToolManagementService

        # This should fail initially since UVToolManagementService doesn't exist yet
        service = UVToolManagementService()

        # Step 1: List installed tools
        result = service.list_tools()

        # Expected: Shows docbro in list
        assert result.returncode == 0
        assert "docbro" in result.stdout
        assert "uv tool list" in ' '.join(mock_uv_commands['commands_called'])

    def test_uv_tool_update_docbro_works(self, mock_platformdirs, temp_home, mock_uv_commands):
        """Test that 'uv tool update docbro' updates to latest version."""
        from src.services.uv_tool_management import UVToolManagementService

        # This should fail initially since UVToolManagementService doesn't exist yet
        service = UVToolManagementService()

        # Step 2: Update tool
        result = service.update_tool("docbro")

        # Expected: Updates to latest version
        assert result.returncode == 0
        assert "Updated docbro" in result.stdout
        assert "uv tool update docbro" in ' '.join(mock_uv_commands['commands_called'])

    def test_docbro_version_shows_updated_version(self, mock_platformdirs, temp_home, mock_uv_commands):
        """Test that 'docbro --version' shows updated version after update."""
        from src.services.uv_tool_management import UVToolManagementService

        # This should fail initially since UVToolManagementService doesn't exist yet
        service = UVToolManagementService()

        # Step 1: Check version before update
        version_before = service.get_docbro_version()
        assert "1.0.0" in version_before.stdout

        # Step 2: Update tool
        update_result = service.update_tool("docbro")
        assert update_result.returncode == 0

        # Step 3: Verify update - check version after update
        version_after = service.get_docbro_version()
        assert "1.1.0" in version_after.stdout

        # Verify commands were called
        commands = ' '.join(mock_uv_commands['commands_called'])
        assert "docbro --version" in commands
        assert "uv tool update docbro" in commands

    def test_uv_tool_uninstall_removes_command(self, mock_platformdirs, temp_home, mock_uv_commands):
        """Test that 'uv tool uninstall docbro' removes docbro command from PATH."""
        from src.services.uv_tool_management import UVToolManagementService

        # This should fail initially since UVToolManagementService doesn't exist yet
        service = UVToolManagementService()

        # Step 4: Uninstall
        result = service.uninstall_tool("docbro")

        # Expected: Removes docbro command from PATH
        assert result.returncode == 0
        assert "Uninstalled docbro" in result.stdout
        assert "uv tool uninstall docbro" in ' '.join(mock_uv_commands['commands_called'])

    def test_which_docbro_returns_not_found_after_uninstall(self, mock_platformdirs, temp_home, mock_uv_commands):
        """Test that 'which docbro' returns command not found after uninstall."""
        from src.services.uv_tool_management import UVToolManagementService

        # This should fail initially since UVToolManagementService doesn't exist yet
        service = UVToolManagementService()

        # Step 1: Verify docbro is available before uninstall
        which_before = service.which_docbro()
        assert which_before.returncode == 0
        assert "/home/user/.local/bin/docbro" in which_before.stdout

        # Step 2: Uninstall docbro
        uninstall_result = service.uninstall_tool("docbro")
        assert uninstall_result.returncode == 0

        # Step 5: Verify removal - which docbro should return command not found
        which_after = service.which_docbro()
        assert which_after.returncode == 1
        assert "command not found" in which_after.stderr

        # Verify commands were called
        commands = ' '.join(mock_uv_commands['commands_called'])
        assert "which docbro" in commands
        assert "uv tool uninstall docbro" in commands

    def test_full_uv_tool_management_workflow(self, mock_platformdirs, temp_home, mock_uv_commands):
        """Test complete UV tool management workflow from quickstart scenario #6."""
        from src.services.uv_tool_management import UVToolManagementService

        # This should fail initially since UVToolManagementService doesn't exist yet
        service = UVToolManagementService()

        # Step 1: List installed tools - should show docbro
        list_result = service.list_tools()
        assert list_result.returncode == 0
        assert "docbro" in list_result.stdout

        # Step 2: Update tool - should update to latest version
        update_result = service.update_tool("docbro")
        assert update_result.returncode == 0
        assert "Updated docbro" in update_result.stdout

        # Step 3: Verify update - should show updated version
        version_result = service.get_docbro_version()
        assert version_result.returncode == 0
        assert "1.1.0" in version_result.stdout  # After update

        # Step 4: Uninstall - should remove command from PATH
        uninstall_result = service.uninstall_tool("docbro")
        assert uninstall_result.returncode == 0
        assert "Uninstalled docbro" in uninstall_result.stdout

        # Step 5: Verify removal - command should not be found
        which_result = service.which_docbro()
        assert which_result.returncode == 1
        assert "command not found" in which_result.stderr

        # Verify all expected commands were called
        all_commands = ' '.join(mock_uv_commands['commands_called'])
        assert "uv tool list" in all_commands
        assert "uv tool update docbro" in all_commands
        assert "docbro --version" in all_commands
        assert "uv tool uninstall docbro" in all_commands
        assert "which docbro" in all_commands

    def test_uv_tool_integration_with_installation_context(self, mock_platformdirs, temp_home, mock_uv_commands):
        """Test that UV tool management integrates with installation context tracking."""
        from src.services.uv_tool_management import UVToolManagementService

        # This should fail initially since integration doesn't exist yet
        service = UVToolManagementService()
        config_service = ConfigService()

        # Create initial installation context
        context = config_service.create_installation_context(
            install_method="uvx",
            version="1.0.0",
            python_version="3.13.1",
            uv_version="0.4.0"
        )

        # Perform update via UV tool management
        update_result = service.update_tool("docbro")
        assert update_result.returncode == 0

        # Verify installation context is updated after tool update
        updated_context = config_service.load_installation_context()

        # The integration should update the context to reflect the new version
        # This will fail initially since the integration doesn't exist
        assert updated_context.version == "1.1.0"  # Should be updated
        assert updated_context.install_method == "uvx"  # Should remain the same
        assert updated_context.last_update_check is not None  # Should be set

    @pytest.mark.skipif(True, reason="TDD: UV tool management integration not implemented yet")
    def test_uv_tool_error_handling(self, mock_platformdirs, temp_home):
        """Test error handling when UV commands fail."""
        # This test documents expected behavior but is skipped until implementation
        pass

    @pytest.mark.skipif(True, reason="TDD: UV tool management integration not implemented yet")
    def test_uv_tool_permissions_handling(self, mock_platformdirs, temp_home):
        """Test handling of permission errors during UV tool operations."""
        # This test documents expected behavior but is skipped until implementation
        pass