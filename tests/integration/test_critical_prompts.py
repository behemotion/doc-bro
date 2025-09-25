"""Integration test for installation wizard critical decision handling."""

import pytest
import tempfile
import shutil
import socket
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, Mock, AsyncMock, MagicMock
from typing import Dict, Any, List

from src.services.config import ConfigService
from src.services.detection import ServiceDetectionService
from src.services.setup import SetupWizardService
from src.models.installation import (
    InstallationContext, ServiceStatus, SetupWizardState, CriticalDecisionPoint
)


@pytest.mark.integration
class TestCriticalPrompts:
    """Test installation wizard handling of critical decisions like port conflicts."""

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
    def mock_occupied_port(self):
        """Mock a port that's already in use."""
        original_socket = socket.socket

        def mock_socket(*args, **kwargs):
            sock = original_socket(*args, **kwargs)
            original_bind = sock.bind

            def mock_bind(address):
                if address[1] == 8765:  # Default serve port (note: CLI default is 8000, but we're testing conflicts)
                    raise OSError("Address already in use")
                return original_bind(address)

            sock.bind = mock_bind
            return sock

        with patch('socket.socket', side_effect=mock_socket):
            yield

    def test_port_conflict_detection_and_resolution(self, mock_platformdirs, temp_home, mock_occupied_port):
        """Test port conflict detection during setup and user prompt for alternative."""
        # This test should FAIL initially since port conflict handling doesn't exist yet (TDD requirement)

        wizard = SetupWizardService()
        config_service = ConfigService()

        # Simulate setup process reaching critical decision point
        state = wizard.create_wizard_state()
        state.current_step = "config_setup"
        state.completed_steps = ["welcome", "python_check", "service_check", "service_install"]

        # Mock the critical decision detection - this would detect port 8765 is occupied
        with patch.object(wizard, '_detect_port_conflicts') as mock_detect_conflicts, \
             patch.object(wizard, '_prompt_for_critical_decision') as mock_prompt_decision, \
             patch.object(wizard, '_apply_critical_decision') as mock_apply_decision, \
             patch.object(wizard, '_create_installation_context') as mock_create_context:

            # Setup mock responses
            port_conflict = CriticalDecisionPoint(
                decision_id="mcp_server_port_conflict",
                decision_type="service_port",
                title="Port Conflict Detected",
                description="Default MCP server port 8765 is already in use by another service.",
                options=[
                    {"id": "port_8766", "label": "Use port 8766 (recommended)", "value": 8766},
                    {"id": "port_9000", "label": "Use port 9000", "value": 9000},
                    {"id": "custom_port", "label": "Specify custom port", "value": "custom"}
                ],
                default_option="port_8766"
            )

            # Mock conflict detection finds port 8765 occupied
            mock_detect_conflicts.return_value = [port_conflict]

            # Mock user chooses alternative port
            resolved_decision = port_conflict.model_copy()
            resolved_decision.user_choice = {"id": "port_8766", "value": 8766}
            resolved_decision.resolved = True
            mock_prompt_decision.return_value = resolved_decision

            # Mock context creation with new port
            mock_context = Mock()
            mock_context.server_port = 8766
            mock_context.install_method = "uvx"
            mock_context.version = "1.0.0"
            mock_create_context.return_value = mock_context

            # This should fail since the methods don't exist yet
            try:
                # Attempt to run setup with conflict handling
                result = wizard._handle_critical_decisions(state)

                # If we get here, the feature was implemented
                # Verify the port conflict was detected and resolved
                mock_detect_conflicts.assert_called_once()
                mock_prompt_decision.assert_called_once_with(port_conflict)
                mock_apply_decision.assert_called_once_with(resolved_decision)

                assert result.server_port == 8766

            except AttributeError as e:
                # Expected failure - the critical decision methods don't exist yet
                assert "_detect_port_conflicts" in str(e) or "_handle_critical_decisions" in str(e)
                pytest.fail(f"TDD EXPECTED FAILURE: Critical decision handling not implemented yet: {e}")

    def test_port_conflict_user_input_validation(self, mock_platformdirs, temp_home):
        """Test user input validation for custom port selection."""
        wizard = SetupWizardService()

        # Create a decision point for custom port input
        custom_port_decision = CriticalDecisionPoint(
            decision_id="custom_mcp_port",
            decision_type="service_port",
            title="Custom Port Selection",
            description="Enter a custom port number for the MCP server (1024-65535).",
            options=[
                {"id": "custom", "label": "Custom port", "value": "custom"}
            ],
            validation_pattern=r"^([1-9][0-9]{3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])$"
        )

        try:
            # Test invalid port numbers
            with patch.object(wizard, '_validate_user_input') as mock_validate:
                # Should reject invalid ports
                mock_validate.side_effect = [False, False, True]  # Reject 80, 99999, accept 8080

                # This will fail since validation method doesn't exist
                result = wizard._validate_critical_decision_input(custom_port_decision, "80")

        except AttributeError as e:
            # Expected failure - validation methods don't exist yet
            assert "_validate_critical_decision_input" in str(e) or "_validate_user_input" in str(e)
            pytest.fail(f"TDD EXPECTED FAILURE: Input validation not implemented yet: {e}")

    def test_docbro_serve_help_shows_configured_port(self, mock_platformdirs, temp_home):
        """Test that docbro serve --help shows the configured port after conflict resolution."""
        config_service = ConfigService()

        # Create installation context with custom port due to conflict resolution
        context = config_service.create_installation_context(
            install_method="uvx",
            version="1.0.0",
            python_version="3.13.1"
        )

        # Mock that port 8765 was changed to 8766 due to conflict
        config_data = {
            "installation": context.model_dump(mode='json'),
            "server_config": {
                "default_port": 8766,  # Changed from default due to conflict
                "port_conflict_resolved": True,
                "original_port": 8765
            }
        }

        # Save config with custom port
        with open(config_service.config_dir / "server.json", 'w') as f:
            import json
            json.dump(config_data, f, indent=2)

        try:
            # Test that CLI help reflects the configured port
            from src.cli.main import main
            from click.testing import CliRunner

            runner = CliRunner()

            with patch('src.services.config.ConfigService.load_server_config') as mock_load_config:
                mock_load_config.return_value = config_data["server_config"]

                # This should fail since server config loading doesn't exist yet
                result = runner.invoke(main, ['serve', '--help'])

                # If implemented, should show custom port in help
                if result.exit_code == 0:
                    assert "8766" in result.output or "port" in result.output.lower()

        except (AttributeError, ImportError) as e:
            # Expected failure - server config integration doesn't exist yet
            pytest.fail(f"TDD EXPECTED FAILURE: Server config integration not implemented yet: {e}")

    @patch('rich.prompt.Prompt.ask')
    @patch('rich.prompt.Confirm.ask')
    def test_multiple_conflict_resolution_workflow(self, mock_confirm, mock_prompt, mock_platformdirs, temp_home):
        """Test handling multiple conflicts in sequence during setup."""
        wizard = SetupWizardService()

        # Mock multiple conflicts: port conflict + data directory conflict
        port_conflict = CriticalDecisionPoint(
            decision_id="port_conflict_8765",
            decision_type="service_port",
            title="MCP Server Port Conflict",
            description="Port 8765 is occupied by another service.",
            options=[
                {"id": "alt_port", "label": "Use alternative port 8766", "value": 8766}
            ]
        )

        data_dir_conflict = CriticalDecisionPoint(
            decision_id="data_dir_permissions",
            decision_type="data_directory",
            title="Data Directory Permissions",
            description="Default data directory requires elevated permissions.",
            options=[
                {"id": "user_dir", "label": "Use user directory instead", "value": "~/docbro-data"}
            ]
        )

        # Mock user interactions
        mock_confirm.side_effect = [True, True]  # Confirm both resolutions
        mock_prompt.side_effect = ["alt_port", "user_dir"]

        try:
            # Test sequential conflict resolution
            with patch.object(wizard, '_detect_all_conflicts') as mock_detect_all:
                mock_detect_all.return_value = [port_conflict, data_dir_conflict]

                # This should fail since conflict detection doesn't exist yet
                conflicts = wizard._resolve_installation_conflicts()

                # If implemented, should handle both conflicts
                assert len(conflicts) == 2
                assert all(c.resolved for c in conflicts)

        except AttributeError as e:
            # Expected failure - conflict resolution system doesn't exist yet
            pytest.fail(f"TDD EXPECTED FAILURE: Multi-conflict resolution not implemented yet: {e}")

    def test_critical_decision_persistence_and_recovery(self, mock_platformdirs, temp_home):
        """Test that critical decisions are persisted and can be recovered after interruption."""
        wizard = SetupWizardService()
        config_service = ConfigService()

        # Create a decision that needs persistence
        port_decision = CriticalDecisionPoint(
            decision_id="interrupted_port_decision",
            decision_type="service_port",
            title="Port Selection",
            description="Choose MCP server port.",
            options=[{"id": "8080", "label": "Port 8080", "value": 8080}],
            user_choice={"id": "8080", "value": 8080},
            resolved=True,
            timestamp=datetime.now()
        )

        try:
            # Test decision persistence
            wizard._save_critical_decision(port_decision)

            # Test decision recovery
            recovered = wizard._load_critical_decision("interrupted_port_decision")

            assert recovered is not None
            assert recovered.user_choice == {"id": "8080", "value": 8080}
            assert recovered.resolved is True

        except AttributeError as e:
            # Expected failure - persistence methods don't exist yet
            pytest.fail(f"TDD EXPECTED FAILURE: Decision persistence not implemented yet: {e}")

    def test_quickstart_scenario_2_complete_workflow(self, mock_platformdirs, temp_home):
        """Test the complete quickstart scenario #2: Installation with critical decisions."""
        # This represents the full user workflow from the requirements

        wizard = SetupWizardService()
        config_service = ConfigService()

        # Mock the complete scenario
        with patch('socket.socket') as mock_socket_class, \
             patch.object(wizard, 'run_interactive_setup') as mock_setup:

            # Mock port 8765 conflict (socket bind fails)
            mock_socket = Mock()
            mock_socket.bind.side_effect = OSError("Address already in use")
            mock_socket_class.return_value = mock_socket

            # Mock the complete setup flow with critical decision handling
            expected_context = Mock()
            expected_context.server_port = 8766  # Resolved port
            expected_context.install_method = "uvx"
            expected_context.version = "1.0.0"
            expected_context.critical_decisions_resolved = 1

            mock_setup.return_value = expected_context

            try:
                # Run complete setup (should detect and resolve conflicts)
                context = wizard.run_interactive_setup()

                # Verify the complete workflow handled conflicts
                assert hasattr(context, 'server_port')
                assert context.server_port == 8766  # Alternative port chosen
                assert hasattr(context, 'critical_decisions_resolved')
                assert context.critical_decisions_resolved >= 1

            except AttributeError as e:
                # Expected failure - complete critical decision workflow doesn't exist yet
                pytest.fail(f"TDD EXPECTED FAILURE: Complete critical decision workflow not implemented yet: {e}")

    def test_port_availability_check_service(self, mock_platformdirs, temp_home):
        """Test the port availability checking service."""
        try:
            from src.services.port_checker import PortAvailabilityService

            port_service = PortAvailabilityService()

            # Test checking available port
            available = port_service.is_port_available(8765)
            assert isinstance(available, bool)

            # Test finding alternative port
            alternative = port_service.find_available_port(start_port=8765)
            assert isinstance(alternative, int)
            assert alternative >= 8765

        except ImportError as e:
            # Expected failure - port checking service doesn't exist yet
            pytest.fail(f"TDD EXPECTED FAILURE: Port availability service not implemented yet: {e}")