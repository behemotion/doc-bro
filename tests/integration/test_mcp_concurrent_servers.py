"""Integration test for concurrent MCP server operation.

This test validates that both read-only and admin MCP servers
can run concurrently without conflicts, as specified in quickstart.md.
"""

import pytest
import asyncio
import httpx
from typing import AsyncGenerator


class TestMcpConcurrentServers:
    """Integration tests for concurrent MCP server operation."""

    @pytest.fixture
    def read_only_url(self) -> str:
        """Base URL for read-only MCP server."""
        return "http://localhost:9383"

    @pytest.fixture
    def admin_url(self) -> str:
        """Base URL for admin MCP server."""
        return "http://127.0.0.1:9384"

    @pytest.mark.integration
    async def test_both_servers_start_concurrently(
        self, read_only_url: str, admin_url: str
    ) -> None:
        """Test that both servers can start and run concurrently."""
        # This test assumes servers are already running
        # In a real scenario, this would start both servers

        async with httpx.AsyncClient() as client:
            # Test read-only server is accessible
            read_only_response = await client.get(f"{read_only_url}/mcp/v1/health")
            assert read_only_response.status_code == 200

            # Test admin server is accessible
            admin_response = await client.get(f"{admin_url}/mcp/v1/health")
            assert admin_response.status_code == 200

    @pytest.mark.integration
    async def test_servers_use_different_ports(
        self, read_only_url: str, admin_url: str
    ) -> None:
        """Test that servers run on different ports without conflicts."""
        async with httpx.AsyncClient() as client:
            # Get health from both servers
            read_only_response = await client.get(f"{read_only_url}/mcp/v1/health")
            admin_response = await client.get(f"{admin_url}/mcp/v1/health")

            assert read_only_response.status_code == 200
            assert admin_response.status_code == 200

            read_only_data = read_only_response.json()
            admin_data = admin_response.json()

            # Verify they identify as different server types
            assert read_only_data["data"]["server_type"] == "read-only"
            assert admin_data["data"]["server_type"] == "admin"

    @pytest.mark.integration
    async def test_concurrent_requests_to_both_servers(
        self, read_only_url: str, admin_url: str
    ) -> None:
        """Test concurrent requests to both servers work without interference."""
        async def make_read_only_request() -> httpx.Response:
            async with httpx.AsyncClient() as client:
                return await client.post(
                    f"{read_only_url}/mcp/v1/list_projects",
                    json={"method": "list_projects", "params": {}}
                )

        async def make_admin_request() -> httpx.Response:
            async with httpx.AsyncClient() as client:
                return await client.post(
                    f"{admin_url}/mcp/v1/execute_command",
                    json={"method": "execute_command", "params": {"command": "health"}}
                )

        # Make concurrent requests
        read_only_task = asyncio.create_task(make_read_only_request())
        admin_task = asyncio.create_task(make_admin_request())

        read_only_response, admin_response = await asyncio.gather(
            read_only_task, admin_task
        )

        # Both should succeed
        assert read_only_response.status_code == 200
        assert admin_response.status_code == 200

    @pytest.mark.integration
    async def test_server_isolation(
        self, read_only_url: str, admin_url: str
    ) -> None:
        """Test that servers are properly isolated and don't share state."""
        async with httpx.AsyncClient() as client:
            # Try to access admin endpoint on read-only server
            read_only_admin_attempt = await client.post(
                f"{read_only_url}/mcp/v1/execute_command",
                json={"method": "execute_command", "params": {"command": "health"}}
            )

            # Should fail - read-only server doesn't have admin endpoints
            assert read_only_admin_attempt.status_code == 404

            # Try to access read-only endpoint on admin server
            admin_list_attempt = await client.post(
                f"{admin_url}/mcp/v1/list_projects",
                json={"method": "list_projects", "params": {}}
            )

            # Should fail - admin server doesn't have read-only endpoints
            assert admin_list_attempt.status_code == 404

    @pytest.mark.integration
    async def test_health_checks_independent(
        self, read_only_url: str, admin_url: str
    ) -> None:
        """Test that health checks are independent between servers."""
        async with httpx.AsyncClient() as client:
            # Get health from both servers
            read_only_health = await client.get(f"{read_only_url}/mcp/v1/health")
            admin_health = await client.get(f"{admin_url}/mcp/v1/health")

            assert read_only_health.status_code == 200
            assert admin_health.status_code == 200

            read_only_data = read_only_health.json()["data"]
            admin_data = admin_health.json()["data"]

            # Both should have healthy status but different characteristics
            assert read_only_data["server_type"] == "read-only"
            assert admin_data["server_type"] == "admin"

            # Admin should have security status, read-only should not
            assert "security_status" not in read_only_data
            assert "security_status" in admin_data

    @pytest.mark.integration
    async def test_graceful_shutdown_independence(
        self, read_only_url: str, admin_url: str
    ) -> None:
        """Test that shutting down one server doesn't affect the other."""
        # This test would simulate server shutdown scenarios
        # For now, just verify both are responsive
        async with httpx.AsyncClient() as client:
            read_only_response = await client.get(f"{read_only_url}/mcp/v1/health")
            admin_response = await client.get(f"{admin_url}/mcp/v1/health")

            assert read_only_response.status_code == 200
            assert admin_response.status_code == 200

    @pytest.mark.integration
    async def test_load_balancing_behavior(
        self, read_only_url: str, admin_url: str
    ) -> None:
        """Test behavior under concurrent load to both servers."""
        read_only_requests = []
        admin_requests = []

        # Create multiple concurrent requests
        for i in range(5):
            read_only_requests.append(
                self._make_read_only_health_request(read_only_url)
            )
            admin_requests.append(
                self._make_admin_health_request(admin_url)
            )

        # Execute all requests concurrently
        all_responses = await asyncio.gather(
            *read_only_requests, *admin_requests, return_exceptions=True
        )

        # All should succeed (no exceptions)
        for response in all_responses:
            assert isinstance(response, httpx.Response)
            assert response.status_code == 200

    async def _make_read_only_health_request(self, url: str) -> httpx.Response:
        """Helper to make read-only health request."""
        async with httpx.AsyncClient() as client:
            return await client.get(f"{url}/mcp/v1/health")

    async def _make_admin_health_request(self, url: str) -> httpx.Response:
        """Helper to make admin health request."""
        async with httpx.AsyncClient() as client:
            return await client.get(f"{url}/mcp/v1/health")