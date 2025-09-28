"""Unit tests for PortManager conflict detection."""

import pytest
import socket
from unittest.mock import Mock, patch, call
from contextlib import closing

from src.logic.mcp.utils.port_manager import PortManager
from src.logic.mcp.models.config import McpServerConfig
from src.logic.mcp.models.server_type import McpServerType


class TestPortManager:
    """Test cases for PortManager logic."""

    def setup_method(self):
        """Set up test fixtures."""
        self.port_manager = PortManager()

    def test_initialization(self):
        """Test PortManager initialization."""
        assert len(self.port_manager._allocated_ports) == 0

    @patch('src.logic.mcp.utils.port_manager.closing')
    @patch('socket.socket')
    def test_is_port_available_port_free(self, mock_socket, mock_closing):
        """Test port availability check when port is free."""
        mock_sock = Mock()
        mock_sock.connect_ex.return_value = 1  # Connection failed = port free
        mock_socket.return_value = mock_sock
        mock_closing.return_value.__enter__.return_value = mock_sock

        result = self.port_manager.is_port_available(8080, "localhost")

        assert result is True
        mock_sock.setsockopt.assert_called_once_with(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        mock_sock.connect_ex.assert_called_once_with(("localhost", 8080))

    @patch('src.logic.mcp.utils.port_manager.closing')
    @patch('socket.socket')
    def test_is_port_available_port_in_use(self, mock_socket, mock_closing):
        """Test port availability check when port is in use."""
        mock_sock = Mock()
        mock_sock.connect_ex.return_value = 0  # Connection succeeded = port in use
        mock_socket.return_value = mock_sock
        mock_closing.return_value.__enter__.return_value = mock_sock

        result = self.port_manager.is_port_available(8080, "localhost")

        assert result is False
        mock_sock.connect_ex.assert_called_once_with(("localhost", 8080))

    @patch('socket.socket')
    def test_is_port_available_exception_handling(self, mock_socket):
        """Test port availability check exception handling."""
        mock_socket.side_effect = Exception("Socket error")

        result = self.port_manager.is_port_available(8080, "localhost")

        assert result is False

    def test_find_available_port_preferred_available(self):
        """Test finding available port when preferred port is available."""
        with patch.object(self.port_manager, 'is_port_available', return_value=True):
            result = self.port_manager.find_available_port(9383)

            assert result == 9383

    def test_find_available_port_search_nearby(self):
        """Test finding available port when preferred port is not available."""
        def mock_is_available(port, host):
            # Port 9383 is not available, but 9384 is
            return port == 9384

        with patch.object(self.port_manager, 'is_port_available', side_effect=mock_is_available):
            result = self.port_manager.find_available_port(9383)

            assert result == 9384

    def test_find_available_port_search_full_range(self):
        """Test finding available port in full range when nearby ports are not available."""
        def mock_is_available(port, host):
            # Only port 2000 is available (outside nearby range)
            return port == 2000

        with patch.object(self.port_manager, 'is_port_available', side_effect=mock_is_available):
            result = self.port_manager.find_available_port(9383, port_range=(1024, 65535))

            assert result == 2000

    def test_find_available_port_no_ports_available(self):
        """Test finding available port when no ports are available."""
        with patch.object(self.port_manager, 'is_port_available', return_value=False):
            result = self.port_manager.find_available_port(9383)

            assert result is None

    def test_find_available_port_custom_range(self):
        """Test finding available port with custom port range."""
        def mock_is_available(port, host):
            # Only port 8080 is available
            return port == 8080

        with patch.object(self.port_manager, 'is_port_available', side_effect=mock_is_available):
            result = self.port_manager.find_available_port(9383, port_range=(8000, 8100))

            assert result == 8080

    def test_allocate_port_success(self):
        """Test successful port allocation."""
        result = self.port_manager.allocate_port(9383)

        assert result is True
        assert 9383 in self.port_manager._allocated_ports

    def test_allocate_port_already_allocated(self):
        """Test port allocation when port is already allocated."""
        # Allocate port first
        self.port_manager.allocate_port(9383)

        # Try to allocate the same port again
        result = self.port_manager.allocate_port(9383)

        assert result is False
        assert self.port_manager._allocated_ports == {9383}

    def test_release_port_success(self):
        """Test successful port release."""
        # Allocate port first
        self.port_manager.allocate_port(9383)

        # Release the port
        result = self.port_manager.release_port(9383)

        assert result is True
        assert 9383 not in self.port_manager._allocated_ports

    def test_release_port_not_allocated(self):
        """Test port release when port was not allocated."""
        result = self.port_manager.release_port(9383)

        assert result is False

    def test_check_port_conflicts_no_conflicts(self):
        """Test port conflict detection with no conflicts."""
        configs = [
            McpServerConfig(server_type=McpServerType.READ_ONLY, port=9383),
            McpServerConfig(server_type=McpServerType.ADMIN, port=9384)
        ]

        conflicts = self.port_manager.check_port_conflicts(configs)

        assert len(conflicts) == 0

    def test_check_port_conflicts_with_conflicts(self):
        """Test port conflict detection with conflicts."""
        configs = [
            McpServerConfig(server_type=McpServerType.READ_ONLY, port=9383),
            McpServerConfig(server_type=McpServerType.ADMIN, port=9383)  # Same port
        ]

        conflicts = self.port_manager.check_port_conflicts(configs)

        assert len(conflicts) == 1
        assert "Port 9383 conflict" in conflicts[0]
        assert "admin server conflicts with read-only server" in conflicts[0]

    def test_check_port_conflicts_disabled_servers_ignored(self):
        """Test that disabled servers are ignored in conflict detection."""
        configs = [
            McpServerConfig(server_type=McpServerType.READ_ONLY, port=9383, enabled=True),
            McpServerConfig(server_type=McpServerType.ADMIN, port=9383, enabled=False)  # Disabled
        ]

        conflicts = self.port_manager.check_port_conflicts(configs)

        assert len(conflicts) == 0

    def test_check_port_conflicts_multiple_conflicts(self):
        """Test port conflict detection with multiple conflicts."""
        configs = [
            McpServerConfig(server_type=McpServerType.READ_ONLY, port=9383),
            McpServerConfig(server_type=McpServerType.ADMIN, port=9383),  # First conflict
            McpServerConfig(server_type=McpServerType.READ_ONLY, port=9384),
            McpServerConfig(server_type=McpServerType.ADMIN, port=9384)   # Second conflict
        ]

        conflicts = self.port_manager.check_port_conflicts(configs)

        assert len(conflicts) == 2

    def test_validate_server_configs_valid(self):
        """Test server configuration validation with valid configs."""
        configs = [
            McpServerConfig(server_type=McpServerType.READ_ONLY, port=9383),
            McpServerConfig(server_type=McpServerType.ADMIN, port=9384)
        ]

        with patch.object(self.port_manager, 'is_port_available', return_value=True):
            is_valid, errors = self.port_manager.validate_server_configs(configs)

            assert is_valid is True
            assert len(errors) == 0

    def test_validate_server_configs_with_conflicts(self):
        """Test server configuration validation with port conflicts."""
        configs = [
            McpServerConfig(server_type=McpServerType.READ_ONLY, port=9383),
            McpServerConfig(server_type=McpServerType.ADMIN, port=9383)  # Same port
        ]

        with patch.object(self.port_manager, 'is_port_available', return_value=True):
            is_valid, errors = self.port_manager.validate_server_configs(configs)

            assert is_valid is False
            assert len(errors) == 1
            assert "Port 9383 conflict" in errors[0]

    def test_validate_server_configs_port_unavailable(self):
        """Test server configuration validation with unavailable ports."""
        configs = [
            McpServerConfig(server_type=McpServerType.READ_ONLY, port=9383, host="localhost")
        ]

        with patch.object(self.port_manager, 'is_port_available', return_value=False):
            is_valid, errors = self.port_manager.validate_server_configs(configs)

            assert is_valid is False
            assert len(errors) == 1
            assert "Port 9383 is not available on localhost" in errors[0]

    def test_validate_server_configs_mixed_issues(self):
        """Test server configuration validation with mixed issues."""
        configs = [
            McpServerConfig(server_type=McpServerType.READ_ONLY, port=9383),
            McpServerConfig(server_type=McpServerType.ADMIN, port=9383),  # Conflict
            McpServerConfig(server_type=McpServerType.READ_ONLY, port=9999)  # Unavailable
        ]

        def mock_is_available(port, host):
            return port != 9999  # Port 9999 is not available

        with patch.object(self.port_manager, 'is_port_available', side_effect=mock_is_available):
            is_valid, errors = self.port_manager.validate_server_configs(configs)

            assert is_valid is False
            assert len(errors) == 2  # One conflict + one unavailable port

    def test_suggest_port_fixes(self):
        """Test port fix suggestions."""
        configs = [
            McpServerConfig(server_type=McpServerType.READ_ONLY, port=9383),
            McpServerConfig(server_type=McpServerType.ADMIN, port=9383)  # Conflict
        ]

        def mock_find_available(preferred_port, host):
            if preferred_port == 9383:
                return 9385  # Suggest alternative
            return preferred_port

        with patch.object(self.port_manager, 'find_available_port', side_effect=mock_find_available):
            suggestions = self.port_manager.suggest_port_fixes(configs)

            # Both configs should get suggestions since they conflict
            assert len(suggestions) == 2
            for config, suggested_port in suggestions:
                assert suggested_port == 9385

    def test_suggest_port_fixes_no_alternatives(self):
        """Test port fix suggestions when no alternatives are available."""
        configs = [
            McpServerConfig(server_type=McpServerType.READ_ONLY, port=9383),
            McpServerConfig(server_type=McpServerType.ADMIN, port=9383)  # Conflict
        ]

        with patch.object(self.port_manager, 'find_available_port', return_value=None):
            suggestions = self.port_manager.suggest_port_fixes(configs)

            # No suggestions since no alternative ports available
            assert len(suggestions) == 0

    def test_get_default_configs(self):
        """Test getting default configurations."""
        configs = self.port_manager.get_default_configs()

        assert len(configs) == 2

        # Check read-only config
        read_only_config = next(c for c in configs if c.server_type == McpServerType.READ_ONLY)
        assert read_only_config.host == "0.0.0.0"
        assert read_only_config.port == 9383
        assert read_only_config.enabled is True

        # Check admin config
        admin_config = next(c for c in configs if c.server_type == McpServerType.ADMIN)
        assert admin_config.host == "127.0.0.1"
        assert admin_config.port == 9384
        assert admin_config.enabled is True

    def test_get_port_status_report(self):
        """Test getting port status report."""
        # Allocate some ports
        self.port_manager.allocate_port(8080)
        self.port_manager.allocate_port(8081)

        with patch.object(self.port_manager, 'is_port_available') as mock_is_available:
            # Mock availability for default ports
            mock_is_available.side_effect = lambda port, host: port == 9383

            report = self.port_manager.get_port_status_report()

            # Check structure
            assert "allocated_ports" in report
            assert "default_ports" in report
            assert "port_availability" in report

            # Check allocated ports
            assert set(report["allocated_ports"]) == {8080, 8081}

            # Check default ports
            assert report["default_ports"]["read_only"] == 9383
            assert report["default_ports"]["admin"] == 9384

            # Check availability checks were called for default ports
            expected_calls = [
                call(9383, "0.0.0.0"),
                call(9384, "127.0.0.1")
            ]
            mock_is_available.assert_has_calls(expected_calls, any_order=True)

    def test_port_manager_integration_workflow(self):
        """Test a complete workflow with PortManager."""
        # Create configs with a conflict
        configs = [
            McpServerConfig(server_type=McpServerType.READ_ONLY, port=9383),
            McpServerConfig(server_type=McpServerType.ADMIN, port=9383)  # Conflict
        ]

        # Validate configs (should find conflict)
        with patch.object(self.port_manager, 'is_port_available', return_value=True):
            is_valid, errors = self.port_manager.validate_server_configs(configs)
            assert not is_valid
            assert len(errors) > 0

        # Get suggestions
        def mock_find_available(preferred_port, host):
            # Return different ports for different configs to avoid new conflicts
            if preferred_port == 9383:
                return 9385 if configs[0].port == 9383 else 9386
            return preferred_port

        with patch.object(self.port_manager, 'find_available_port', side_effect=mock_find_available):
            suggestions = self.port_manager.suggest_port_fixes(configs)
            assert len(suggestions) == 2

            # Apply suggestions - each config gets a different port
            configs[0].port = 9385
            configs[1].port = 9386

        # Validate again (should be valid now after fixing all conflicts)
        with patch.object(self.port_manager, 'is_port_available', return_value=True):
            is_valid, errors = self.port_manager.validate_server_configs(configs)
            # Should be valid now since we fixed all conflicts and ports are available
            assert is_valid

    def test_port_range_boundaries(self):
        """Test port finding with edge case ranges."""
        # Test minimum range
        result = self.port_manager.find_available_port(
            9383,
            port_range=(1024, 1024)
        )

        with patch.object(self.port_manager, 'is_port_available') as mock_is_available:
            mock_is_available.return_value = True
            result = self.port_manager.find_available_port(
                9383,
                port_range=(1024, 1024)
            )
            # Should check port 1024 since preferred port is outside range
            assert mock_is_available.called

    def test_find_available_port_preferred_in_range(self):
        """Test finding available port when preferred port is within range."""
        with patch.object(self.port_manager, 'is_port_available', return_value=True):
            result = self.port_manager.find_available_port(
                8080,
                port_range=(8000, 8100)
            )
            assert result == 8080

    def test_large_allocated_ports_set(self):
        """Test performance with large number of allocated ports."""
        # Allocate many ports
        for port in range(9000, 9100):
            self.port_manager.allocate_port(port)

        assert len(self.port_manager._allocated_ports) == 100

        # Test allocation of already allocated port
        result = self.port_manager.allocate_port(9050)
        assert result is False

        # Test release
        result = self.port_manager.release_port(9050)
        assert result is True
        assert 9050 not in self.port_manager._allocated_ports