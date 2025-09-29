"""Integration test for MCP server setup wizard workflow.

This test validates the complete MCP server setup process including
wizard configuration and server startup.
"""

import asyncio
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from click.testing import CliRunner

# These imports will fail until the enhanced CLI commands are implemented
try:
    from src.cli.commands.serve import serve_command
    from src.logic.wizard.mcp_wizard import McpWizard
    from src.logic.mcp.core.mcp_read_only_server import McpReadOnlyServer
    from src.logic.mcp.core.mcp_admin_server import McpAdminServer
    CLI_ENHANCED = True
except ImportError:
    CLI_ENHANCED = False
    serve_command = None
    McpWizard = None
    McpReadOnlyServer = None
    McpAdminServer = None


class TestMcpServerSetupWizard:
    """Integration test for MCP server setup with wizard."""

    @pytest.mark.integration
    def test_imports_available(self):
        """Test that enhanced serve command can be imported."""
        assert CLI_ENHANCED, "Enhanced serve command not implemented yet"

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_serve_with_init_flag(self):
        """Test serve command with --init flag launches wizard."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced serve command not implemented yet")

        runner = CliRunner()

        # Mock wizard to simulate user choices
        with patch('src.logic.wizard.mcp_wizard.McpWizard') as mock_wizard_class:
            mock_wizard = AsyncMock()
            mock_wizard_class.return_value = mock_wizard

            # Mock wizard configuration result
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.configuration = {
                "enable_read_only": True,
                "read_only_port": 9383,
                "enable_admin": True,
                "admin_port": 9384,
                "auto_start": False
            }
            mock_wizard.run.return_value = mock_result

            with patch('src.cli.commands.serve.start_mcp_servers') as mock_start:
                result = runner.invoke(serve_command, ['--init'])

                # Should run wizard
                mock_wizard.run.assert_called_once()
                # Should start servers with wizard config
                mock_start.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_mcp_wizard_step_flow(self):
        """Test complete MCP wizard step progression."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced MCP wizard not implemented yet")

        # Mock wizard orchestrator for step-by-step flow
        with patch('src.logic.wizard.orchestrator.WizardOrchestrator') as mock_orchestrator_class:
            mock_orchestrator = AsyncMock()
            mock_orchestrator_class.return_value = mock_orchestrator

            # Mock wizard steps
            steps = [
                {
                    "number": 1,
                    "title": "Read-Only Server",
                    "prompt": "Enable read-only server?",
                    "input_type": "boolean",
                    "response": True
                },
                {
                    "number": 2,
                    "title": "Read-Only Port",
                    "prompt": "Read-only server port [9383]:",
                    "input_type": "integer",
                    "response": 9383
                },
                {
                    "number": 3,
                    "title": "Admin Server",
                    "prompt": "Enable admin server?",
                    "input_type": "boolean",
                    "response": True
                },
                {
                    "number": 4,
                    "title": "Admin Port",
                    "prompt": "Admin server port [9384]:",
                    "input_type": "integer",
                    "response": 9384
                },
                {
                    "number": 5,
                    "title": "Auto Start",
                    "prompt": "Auto-start with system?",
                    "input_type": "boolean",
                    "response": False
                }
            ]

            mock_orchestrator.get_steps.return_value = steps

            # Test wizard progression
            wizard = McpWizard()
            result = await wizard.run("mcp-server")

            # Should process all steps
            assert mock_orchestrator.get_steps.call_count >= 1

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_read_only_server_only_configuration(self):
        """Test configuration with only read-only server enabled."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced MCP setup not implemented yet")

        # Mock wizard result with read-only only
        wizard_config = {
            "enable_read_only": True,
            "read_only_port": 9383,
            "enable_admin": False,
            "admin_port": None,
            "auto_start": False
        }

        with patch('src.logic.mcp.core.mcp_read_only_server.McpReadOnlyServer') as mock_readonly:
            mock_server = MagicMock()
            mock_readonly.return_value = mock_server

            with patch('src.cli.commands.serve.apply_mcp_configuration') as mock_apply:
                mock_apply.return_value = wizard_config

                runner = CliRunner()
                with patch('src.cli.commands.serve.start_read_only_server') as mock_start_readonly:
                    result = runner.invoke(serve_command, ['--init'])

                    # Should only start read-only server
                    mock_start_readonly.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_dual_server_configuration(self):
        """Test configuration with both read-only and admin servers."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced MCP setup not implemented yet")

        # Mock wizard result with both servers
        wizard_config = {
            "enable_read_only": True,
            "read_only_port": 9383,
            "enable_admin": True,
            "admin_port": 9384,
            "auto_start": False
        }

        with patch('src.logic.mcp.core.mcp_read_only_server.McpReadOnlyServer') as mock_readonly:
            with patch('src.logic.mcp.core.mcp_admin_server.McpAdminServer') as mock_admin:
                mock_readonly_server = MagicMock()
                mock_admin_server = MagicMock()
                mock_readonly.return_value = mock_readonly_server
                mock_admin.return_value = mock_admin_server

                with patch('src.cli.commands.serve.apply_mcp_configuration') as mock_apply:
                    mock_apply.return_value = wizard_config

                    runner = CliRunner()
                    with patch('src.cli.commands.serve.start_dual_servers') as mock_start_dual:
                        result = runner.invoke(serve_command, ['--init'])

                        # Should start both servers
                        mock_start_dual.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_port_configuration_validation(self):
        """Test that port configuration is validated during wizard."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced MCP wizard not implemented yet")

        # Test port conflict detection
        with patch('src.logic.wizard.mcp_wizard.check_port_available') as mock_check_port:
            mock_check_port.side_effect = [False, True]  # First port busy, second available

            with patch('src.logic.wizard.mcp_wizard.McpWizard') as mock_wizard_class:
                mock_wizard = AsyncMock()
                mock_wizard_class.return_value = mock_wizard

                # Should detect port conflict and retry
                mock_wizard.validate_port.return_value = False
                mock_wizard.suggest_alternative_port.return_value = 9385

                wizard = McpWizard()
                await wizard.validate_configuration({
                    "read_only_port": 9383,
                    "admin_port": 9383  # Conflict
                })

                # Should suggest alternative port
                mock_wizard.suggest_alternative_port.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_server_startup_verification(self):
        """Test that servers start correctly after wizard configuration."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced MCP setup not implemented yet")

        # Mock successful server startup
        with patch('src.logic.mcp.core.mcp_read_only_server.McpReadOnlyServer') as mock_readonly:
            mock_server = MagicMock()
            mock_server.start.return_value = True
            mock_server.is_running.return_value = True
            mock_server.port = 9383
            mock_readonly.return_value = mock_server

            runner = CliRunner()
            with patch('src.cli.commands.serve.verify_server_startup') as mock_verify:
                mock_verify.return_value = True

                result = runner.invoke(serve_command, ['--init'])

                # Should verify server started
                mock_verify.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_connection_info_display(self):
        """Test that connection info is displayed after successful setup."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced MCP setup not implemented yet")

        runner = CliRunner()

        # Mock successful setup
        with patch('src.cli.commands.serve.run_mcp_wizard') as mock_wizard:
            mock_wizard.return_value = {
                "enable_read_only": True,
                "read_only_port": 9383,
                "enable_admin": True,
                "admin_port": 9384
            }

            with patch('src.cli.commands.serve.start_servers') as mock_start:
                mock_start.return_value = True

                with patch('src.cli.commands.serve.display_connection_info') as mock_display:
                    result = runner.invoke(serve_command, ['--init'])

                    # Should display connection information
                    mock_display.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_configuration_persistence(self):
        """Test that wizard configuration is persisted for future use."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced MCP setup not implemented yet")

        wizard_config = {
            "enable_read_only": True,
            "read_only_port": 9383,
            "enable_admin": False,
            "auto_start": False
        }

        # Test configuration saving
        with patch('src.cli.commands.serve.save_mcp_configuration') as mock_save:
            with patch('src.cli.commands.serve.run_mcp_wizard') as mock_wizard:
                mock_wizard.return_value = wizard_config

                runner = CliRunner()
                result = runner.invoke(serve_command, ['--init'])

                # Should save configuration
                mock_save.assert_called_once_with(wizard_config)

        # Test configuration loading on subsequent runs
        with patch('src.cli.commands.serve.load_mcp_configuration') as mock_load:
            mock_load.return_value = wizard_config

            result = runner.invoke(serve_command)

            # Should load saved configuration
            mock_load.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_wizard_cancellation_handling(self):
        """Test graceful handling of wizard cancellation."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced MCP wizard not implemented yet")

        runner = CliRunner()

        # Mock wizard cancellation
        with patch('src.logic.wizard.mcp_wizard.McpWizard') as mock_wizard_class:
            mock_wizard = AsyncMock()
            mock_wizard_class.return_value = mock_wizard

            # Simulate user cancellation
            mock_wizard.run.side_effect = KeyboardInterrupt()

            with patch('src.cli.commands.serve.handle_wizard_cancellation') as mock_handle:
                try:
                    result = runner.invoke(serve_command, ['--init'])
                except KeyboardInterrupt:
                    pass

                # Should handle cancellation gracefully
                mock_handle.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_existing_configuration_detection(self):
        """Test detection and handling of existing MCP configuration."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced MCP setup not implemented yet")

        runner = CliRunner()

        # Mock existing configuration
        existing_config = {
            "enable_read_only": True,
            "read_only_port": 9383,
            "enable_admin": False
        }

        with patch('src.cli.commands.serve.check_existing_configuration') as mock_check:
            mock_check.return_value = existing_config

            with patch('click.confirm') as mock_confirm:
                mock_confirm.return_value = False  # Don't reconfigure

                with patch('src.cli.commands.serve.start_with_existing_config') as mock_start:
                    result = runner.invoke(serve_command, ['--init'])

                    # Should use existing configuration
                    mock_start.assert_called_once_with(existing_config)

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_server_health_check(self):
        """Test server health check after startup."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced MCP setup not implemented yet")

        # Mock server health check
        with patch('src.logic.mcp.core.mcp_read_only_server.McpReadOnlyServer') as mock_readonly:
            mock_server = MagicMock()
            mock_server.health_check.return_value = {
                "status": "healthy",
                "port": 9383,
                "uptime": "00:00:01"
            }
            mock_readonly.return_value = mock_server

            runner = CliRunner()
            with patch('src.cli.commands.serve.perform_health_check') as mock_health:
                mock_health.return_value = True

                result = runner.invoke(serve_command, ['--init'])

                # Should perform health check
                mock_health.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_ai_assistant_integration_info(self):
        """Test display of AI assistant integration information."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced MCP setup not implemented yet")

        runner = CliRunner()

        # Mock successful server setup
        with patch('src.cli.commands.serve.run_mcp_wizard') as mock_wizard:
            mock_wizard.return_value = {
                "enable_read_only": True,
                "read_only_port": 9383
            }

            with patch('src.cli.commands.serve.start_servers') as mock_start:
                mock_start.return_value = True

                with patch('src.cli.commands.serve.display_ai_assistant_info') as mock_ai_info:
                    result = runner.invoke(serve_command, ['--init'])

                    # Should display AI assistant integration info
                    mock_ai_info.assert_called_once()

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_setup_performance_timing(self):
        """Test that MCP setup meets performance requirements."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced MCP setup not implemented yet")

        import time

        start_time = time.time()

        # Mock fast setup process
        with patch('src.cli.commands.serve.run_mcp_wizard') as mock_wizard:
            mock_wizard.return_value = {
                "enable_read_only": True,
                "read_only_port": 9383
            }

            with patch('src.cli.commands.serve.start_servers') as mock_start:
                mock_start.return_value = True

                runner = CliRunner()
                result = runner.invoke(serve_command, ['--init'])

                end_time = time.time()
                setup_time = end_time - start_time

                # Setup should be fast (within reasonable bounds for mocked operations)
                assert setup_time < 5, f"MCP setup took {setup_time}s, should be <5s"

    @pytest.mark.integration
    def test_serve_help_includes_wizard_info(self):
        """Test that serve command help mentions wizard functionality."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced serve command not implemented yet")

        runner = CliRunner()
        result = runner.invoke(serve_command, ['--help'])

        if result.exit_code == 0:
            help_text = result.output.lower()

            # Should mention wizard/init functionality
            assert any(keyword in help_text for keyword in [
                "init", "wizard", "setup", "configure"
            ])

            # Should mention both server types
            assert "read-only" in help_text or "admin" in help_text

    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_error_recovery_during_setup(self):
        """Test error recovery during MCP server setup."""
        if not CLI_ENHANCED:
            pytest.skip("Enhanced MCP setup not implemented yet")

        runner = CliRunner()

        # Mock server startup failure
        with patch('src.cli.commands.serve.start_servers') as mock_start:
            mock_start.side_effect = Exception("Port already in use")

            with patch('src.cli.commands.serve.handle_startup_error') as mock_error_handler:
                mock_error_handler.return_value = {
                    "retry": True,
                    "alternative_port": 9385
                }

                result = runner.invoke(serve_command, ['--init'])

                # Should handle error and suggest recovery
                mock_error_handler.assert_called_once()