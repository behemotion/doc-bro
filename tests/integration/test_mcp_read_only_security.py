"""Integration test for read-only MCP server security enforcement.

This test validates that the read-only server properly prevents
write operations as specified in quickstart.md.
"""

import pytest
import httpx


class TestMcpReadOnlySecurityEnforcement:
    """Integration tests for read-only server security."""

    @pytest.fixture
    def base_url(self) -> str:
        """Base URL for read-only MCP server."""
        return "http://localhost:9383"

    @pytest.mark.integration
    async def test_read_only_prevents_execute_command(self, base_url: str) -> None:
        """Test that read-only server blocks execute_command endpoint."""
        request_data = {
            "method": "execute_command",
            "params": {
                "command": "project",
                "arguments": ["--create", "unauthorized-project"],
                "options": {"type": "data"}
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/execute_command",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        # Should return 404 or method not found - read-only server doesn't expose this
        assert response.status_code == 404

    @pytest.mark.integration
    async def test_read_only_prevents_project_create(self, base_url: str) -> None:
        """Test that read-only server blocks project_create endpoint."""
        request_data = {
            "method": "project_create",
            "params": {
                "name": "unauthorized-project",
                "type": "data"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/project_create",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        # Should return 404 - read-only server doesn't expose this endpoint
        assert response.status_code == 404

    @pytest.mark.integration
    async def test_read_only_prevents_project_remove(self, base_url: str) -> None:
        """Test that read-only server blocks project_remove endpoint."""
        request_data = {
            "method": "project_remove",
            "params": {
                "name": "some-project"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/project_remove",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        # Should return 404 - read-only server doesn't expose this endpoint
        assert response.status_code == 404

    @pytest.mark.integration
    async def test_read_only_prevents_crawl_project(self, base_url: str) -> None:
        """Test that read-only server blocks crawl_project endpoint."""
        request_data = {
            "method": "crawl_project",
            "params": {
                "project_name": "some-project"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/crawl_project",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        # Should return 404 - read-only server doesn't expose this endpoint
        assert response.status_code == 404

    @pytest.mark.integration
    async def test_read_only_allows_safe_operations(self, base_url: str) -> None:
        """Test that read-only server allows safe read operations."""
        # Test list_projects
        list_request = {
            "method": "list_projects",
            "params": {}
        }

        async with httpx.AsyncClient() as client:
            list_response = await client.post(
                f"{base_url}/mcp/v1/list_projects",
                json=list_request,
                headers={"Content-Type": "application/json"}
            )

        # Should succeed
        assert list_response.status_code == 200

        # Test search_projects
        search_request = {
            "method": "search_projects",
            "params": {
                "query": "test"
            }
        }

        async with httpx.AsyncClient() as client:
            search_response = await client.post(
                f"{base_url}/mcp/v1/search_projects",
                json=search_request,
                headers={"Content-Type": "application/json"}
            )

        # Should succeed
        assert search_response.status_code == 200

    @pytest.mark.integration
    async def test_read_only_allows_file_access_with_restrictions(
        self, base_url: str
    ) -> None:
        """Test that read-only server allows file access but respects project type restrictions."""
        # Test basic file access
        file_request = {
            "method": "get_project_files",
            "params": {
                "project_name": "test-project"
            }
        }

        async with httpx.AsyncClient() as client:
            file_response = await client.post(
                f"{base_url}/mcp/v1/get_project_files",
                json=file_request,
                headers={"Content-Type": "application/json"}
            )

        # Should succeed (even if project doesn't exist, endpoint should be available)
        assert file_response.status_code == 200

    @pytest.mark.integration
    async def test_read_only_health_check_accessible(self, base_url: str) -> None:
        """Test that read-only server health check is accessible."""
        async with httpx.AsyncClient() as client:
            health_response = await client.get(f"{base_url}/mcp/v1/health")

        assert health_response.status_code == 200
        data = health_response.json()

        # Should identify as read-only server
        assert data["data"]["server_type"] == "read-only"

    @pytest.mark.integration
    async def test_read_only_method_validation(self, base_url: str) -> None:
        """Test that read-only server properly validates method names."""
        # Valid method should work
        valid_request = {
            "method": "list_projects",
            "params": {}
        }

        async with httpx.AsyncClient() as client:
            valid_response = await client.post(
                f"{base_url}/mcp/v1/list_projects",
                json=valid_request,
                headers={"Content-Type": "application/json"}
            )

        assert valid_response.status_code == 200

        # Invalid method should fail
        invalid_request = {
            "method": "invalid_method",
            "params": {}
        }

        async with httpx.AsyncClient() as client:
            invalid_response = await client.post(
                f"{base_url}/mcp/v1/list_projects",
                json=invalid_request,
                headers={"Content-Type": "application/json"}
            )

        # Should return error for invalid method
        assert invalid_response.status_code in [400, 422]

    @pytest.mark.integration
    async def test_read_only_parameter_validation(self, base_url: str) -> None:
        """Test that read-only server validates parameters correctly."""
        # Missing required parameter should fail
        missing_param_request = {
            "method": "search_projects",
            "params": {}  # Missing required 'query' parameter
        }

        async with httpx.AsyncClient() as client:
            missing_param_response = await client.post(
                f"{base_url}/mcp/v1/search_projects",
                json=missing_param_request,
                headers={"Content-Type": "application/json"}
            )

        # Should return validation error
        assert missing_param_response.status_code in [400, 422]

    @pytest.mark.integration
    async def test_read_only_prevents_system_modification(self, base_url: str) -> None:
        """Test that read-only server prevents any system modification attempts."""
        modification_attempts = [
            # Direct HTTP methods that might modify state
            ("PUT", f"{base_url}/mcp/v1/list_projects"),
            ("DELETE", f"{base_url}/mcp/v1/list_projects"),
            ("PATCH", f"{base_url}/mcp/v1/list_projects"),
        ]

        async with httpx.AsyncClient() as client:
            for method, url in modification_attempts:
                response = await client.request(method, url)
                # Should not allow these methods
                assert response.status_code == 405  # Method Not Allowed