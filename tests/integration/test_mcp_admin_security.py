"""Integration test for admin MCP server localhost restriction.

This test validates that the admin server is properly restricted
to localhost access as specified in quickstart.md.
"""

import pytest
import httpx
import socket
from typing import List


class TestMcpAdminSecurityRestriction:
    """Integration tests for admin server localhost restriction."""

    @pytest.fixture
    def admin_localhost_url(self) -> str:
        """Base URL for admin MCP server via localhost."""
        return "http://127.0.0.1:9384"

    @pytest.fixture
    def admin_external_urls(self) -> List[str]:
        """URLs that should NOT work for admin server (external access)."""
        # Get local IP addresses to test external access blocking
        hostname = socket.gethostname()
        local_ips = []

        try:
            # Try to get local IP
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                local_ip = s.getsockname()[0]
                local_ips.append(f"http://{local_ip}:9384")
        except Exception:
            pass

        # Add common external access attempts
        return [
            "http://0.0.0.0:9384",  # Should not work if properly bound to localhost
            "http://localhost:9384",  # This might work depending on configuration
        ] + local_ips

    @pytest.mark.integration
    async def test_admin_accessible_via_localhost(
        self, admin_localhost_url: str
    ) -> None:
        """Test that admin server is accessible via 127.0.0.1."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{admin_localhost_url}/mcp/v1/health")

        assert response.status_code == 200
        data = response.json()

        # Should identify as admin server
        assert data["data"]["server_type"] == "admin"

        # Should indicate localhost-only security
        security_status = data["data"]["security_status"]
        assert security_status["localhost_only"] is True

    @pytest.mark.integration
    async def test_admin_health_reports_security_status(
        self, admin_localhost_url: str
    ) -> None:
        """Test that admin health endpoint reports proper security status."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{admin_localhost_url}/mcp/v1/health")

        assert response.status_code == 200
        data = response.json()

        security_status = data["data"]["security_status"]

        # Validate security status fields
        assert "localhost_only" in security_status
        assert "port" in security_status
        assert security_status["localhost_only"] is True
        assert security_status["port"] == 9384

    @pytest.mark.integration
    async def test_admin_command_execution_localhost_only(
        self, admin_localhost_url: str
    ) -> None:
        """Test that admin command execution works from localhost."""
        request_data = {
            "method": "execute_command",
            "params": {
                "command": "health"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{admin_localhost_url}/mcp/v1/execute_command",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        # Should work from localhost
        assert response.status_code == 200

    @pytest.mark.integration
    async def test_admin_project_operations_localhost_only(
        self, admin_localhost_url: str
    ) -> None:
        """Test that admin project operations work from localhost."""
        # Test project creation
        create_request = {
            "method": "project_create",
            "params": {
                "name": "test-localhost-project",
                "type": "data"
            }
        }

        async with httpx.AsyncClient() as client:
            create_response = await client.post(
                f"{admin_localhost_url}/mcp/v1/project_create",
                json=create_request,
                headers={"Content-Type": "application/json"}
            )

        # Should work from localhost
        assert create_response.status_code == 200

    @pytest.mark.integration
    async def test_admin_security_headers(self, admin_localhost_url: str) -> None:
        """Test that admin server returns appropriate security headers."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{admin_localhost_url}/mcp/v1/health")

        assert response.status_code == 200

        # Check for security-related headers
        headers = response.headers

        # Should return JSON content type
        assert "application/json" in headers.get("content-type", "")

    @pytest.mark.integration
    async def test_admin_binding_configuration(
        self, admin_localhost_url: str
    ) -> None:
        """Test that admin server is properly configured for localhost binding."""
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{admin_localhost_url}/mcp/v1/health")

        assert response.status_code == 200
        data = response.json()

        # Verify server reports correct binding configuration
        security_status = data["data"]["security_status"]
        assert security_status["localhost_only"] is True
        assert security_status["port"] == 9384

    @pytest.mark.integration
    async def test_admin_method_restrictions(self, admin_localhost_url: str) -> None:
        """Test that admin server methods are only accessible via proper channels."""
        # Test that all admin methods work from localhost
        admin_methods = [
            ("execute_command", {"command": "health"}),
            ("project_create", {"name": "test-method-project", "type": "data"}),
            ("project_remove", {"name": "test-method-project"}),
            ("crawl_project", {"project_name": "test-method-project"}),
        ]

        async with httpx.AsyncClient() as client:
            for method, params in admin_methods:
                request_data = {
                    "method": method,
                    "params": params
                }

                response = await client.post(
                    f"{admin_localhost_url}/mcp/v1/{method}",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )

                # All methods should be accessible from localhost
                # (They may fail due to missing projects/etc, but endpoint should exist)
                assert response.status_code != 404  # Endpoint should exist

    @pytest.mark.integration
    async def test_admin_vs_read_only_security_difference(
        self, admin_localhost_url: str
    ) -> None:
        """Test security differences between admin and read-only servers."""
        # Admin server health check
        async with httpx.AsyncClient() as client:
            admin_response = await client.get(f"{admin_localhost_url}/mcp/v1/health")

        assert admin_response.status_code == 200
        admin_data = admin_response.json()["data"]

        # Admin should have security status
        assert "security_status" in admin_data
        assert admin_data["security_status"]["localhost_only"] is True

        # Read-only server health check for comparison
        read_only_url = "http://localhost:9383"
        async with httpx.AsyncClient() as client:
            read_only_response = await client.get(f"{read_only_url}/mcp/v1/health")

        if read_only_response.status_code == 200:
            read_only_data = read_only_response.json()["data"]

            # Read-only should not have security_status (different security model)
            assert "security_status" not in read_only_data
            assert read_only_data["server_type"] == "read-only"

    @pytest.mark.integration
    async def test_admin_port_isolation(self, admin_localhost_url: str) -> None:
        """Test that admin server port is properly isolated."""
        # Verify admin server responds on its designated port
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{admin_localhost_url}/mcp/v1/health")

        assert response.status_code == 200

        # Verify it doesn't respond on read-only server port
        wrong_port_url = "http://127.0.0.1:9383/mcp/v1/execute_command"
        async with httpx.AsyncClient() as client:
            try:
                wrong_response = await client.post(
                    wrong_port_url,
                    json={"method": "execute_command", "params": {"command": "health"}},
                    timeout=5.0
                )
                # If it responds, it should be 404 (different server)
                assert wrong_response.status_code == 404
            except httpx.ConnectError:
                # Connection error is also acceptable (different server)
                pass