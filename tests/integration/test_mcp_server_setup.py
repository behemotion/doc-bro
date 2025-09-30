"""Integration test for MCP server setup architecture validation.

This test validates that the MCP server components are properly integrated
and have the expected structure, rather than testing detailed workflows.
"""

import pytest
from click.testing import CliRunner


class TestMcpServerSetupArchitecture:
    """Integration tests validating MCP server architecture."""

    @pytest.mark.integration
    def test_serve_command_imports(self):
        """Test that serve command can be imported."""
        from src.cli.commands.serve import serve
        assert serve is not None
        assert callable(serve)

    @pytest.mark.integration
    def test_serve_command_has_init_flag(self):
        """Test that serve command has --init flag."""
        from src.cli.commands.serve import serve

        # Check that --init flag is defined
        init_param = None
        for param in serve.params:
            if param.name == "init":
                init_param = param
                break

        assert init_param is not None, "serve command should have --init flag"
        assert init_param.is_flag, "--init should be a boolean flag"

    @pytest.mark.integration
    def test_serve_command_has_admin_flag(self):
        """Test that serve command has --admin flag."""
        from src.cli.commands.serve import serve

        # Check that --admin flag is defined
        admin_param = None
        for param in serve.params:
            if param.name == "admin":
                admin_param = param
                break

        assert admin_param is not None, "serve command should have --admin flag"
        assert admin_param.is_flag, "--admin should be a boolean flag"

    @pytest.mark.integration
    def test_serve_command_has_foreground_flag(self):
        """Test that serve command has --foreground flag."""
        from src.cli.commands.serve import serve

        # Check that --foreground flag is defined
        foreground_param = None
        for param in serve.params:
            if param.name == "foreground":
                foreground_param = param
                break

        assert foreground_param is not None, "serve command should have --foreground flag"
        assert foreground_param.is_flag, "--foreground should be a boolean flag"

    @pytest.mark.integration
    def test_serve_command_has_host_and_port_options(self):
        """Test that serve command has --host and --port options."""
        from src.cli.commands.serve import serve

        # Check parameters
        param_names = [param.name for param in serve.params]
        assert "host" in param_names, "serve command should have --host option"
        assert "port" in param_names, "serve command should have --port option"

    @pytest.mark.integration
    def test_serve_help_output(self):
        """Test that serve command help is accessible."""
        from src.cli.commands.serve import serve

        runner = CliRunner()
        result = runner.invoke(serve, ['--help'])

        assert result.exit_code == 0
        assert "MCP" in result.output or "server" in result.output

    @pytest.mark.integration
    def test_mcp_wizard_can_be_imported(self):
        """Test that McpWizard class can be imported."""
        from src.logic.wizard.mcp_wizard import McpWizard
        assert McpWizard is not None

    @pytest.mark.integration
    def test_mcp_wizard_instantiation(self):
        """Test that McpWizard can be instantiated."""
        from src.logic.wizard.mcp_wizard import McpWizard

        wizard = McpWizard()
        assert wizard is not None

    @pytest.mark.integration
    def test_wizard_orchestrator_can_be_imported(self):
        """Test that WizardOrchestrator can be imported."""
        from src.logic.wizard.orchestrator import WizardOrchestrator
        assert WizardOrchestrator is not None

    @pytest.mark.integration
    def test_wizard_orchestrator_instantiation(self):
        """Test that WizardOrchestrator can be instantiated."""
        from src.logic.wizard.orchestrator import WizardOrchestrator

        orchestrator = WizardOrchestrator()
        assert orchestrator is not None

    @pytest.mark.integration
    def test_mcp_server_config_can_be_imported(self):
        """Test that MCP server config models can be imported."""
        from src.logic.mcp.models.config import McpServerConfig
        from src.logic.mcp.models.server_type import McpServerType

        assert McpServerConfig is not None
        assert McpServerType is not None

    @pytest.mark.integration
    def test_mcp_server_config_creation(self):
        """Test that MCP server config can be created."""
        from src.logic.mcp.models.config import McpServerConfig
        from src.logic.mcp.models.server_type import McpServerType

        config = McpServerConfig(
            server_type=McpServerType.READ_ONLY,
            host="localhost",
            port=9383,
            enabled=True
        )

        assert config.server_type == McpServerType.READ_ONLY
        assert config.host == "localhost"
        assert config.port == 9383
        assert config.enabled is True

    @pytest.mark.integration
    def test_server_orchestrator_can_be_imported(self):
        """Test that ServerOrchestrator can be imported."""
        from src.logic.mcp.core.orchestrator import ServerOrchestrator
        assert ServerOrchestrator is not None

    @pytest.mark.integration
    def test_server_orchestrator_instantiation(self):
        """Test that ServerOrchestrator can be instantiated."""
        from src.logic.mcp.core.orchestrator import ServerOrchestrator
        from src.logic.mcp.utils.port_manager import PortManager

        port_manager = PortManager()
        orchestrator = ServerOrchestrator(port_manager)
        assert orchestrator is not None

    @pytest.mark.integration
    def test_port_manager_can_be_imported(self):
        """Test that PortManager can be imported."""
        from src.logic.mcp.utils.port_manager import PortManager
        assert PortManager is not None

    @pytest.mark.integration
    def test_port_manager_instantiation(self):
        """Test that PortManager can be instantiated."""
        from src.logic.mcp.utils.port_manager import PortManager

        manager = PortManager()
        assert manager is not None

    @pytest.mark.integration
    def test_read_only_server_module_can_be_imported(self):
        """Test that read-only MCP server module can be imported."""
        from src.logic.mcp.core import read_only_server
        assert read_only_server is not None
        # The read-only server is a FastAPI app instance
        assert hasattr(read_only_server, 'app')

    @pytest.mark.integration
    def test_admin_server_module_can_be_imported(self):
        """Test that admin MCP server module can be imported."""
        from src.logic.mcp.core import admin_server
        assert admin_server is not None
        # The admin server is a FastAPI app instance
        assert hasattr(admin_server, 'app')

    @pytest.mark.integration
    def test_mcp_server_types_defined(self):
        """Test that both MCP server types are defined."""
        from src.logic.mcp.models.server_type import McpServerType

        assert hasattr(McpServerType, "READ_ONLY")
        assert hasattr(McpServerType, "ADMIN")

    @pytest.mark.integration
    def test_serve_command_performance(self):
        """Test that serve command help executes quickly (<500ms)."""
        import time
        from src.cli.commands.serve import serve

        runner = CliRunner()
        start = time.time()
        result = runner.invoke(serve, ['--help'])
        elapsed = time.time() - start

        assert result.exit_code == 0
        assert elapsed < 0.5, f"serve --help took {elapsed}s, should be <0.5s"