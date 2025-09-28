"""Contract test for admin server /mcp/v1/project_remove endpoint.

This test validates the MCP admin server's project removal endpoint
against the OpenAPI specification in contracts/mcp-admin-server.json.
"""

import pytest
import httpx


class TestMcpAdminProjectRemove:
    """Contract tests for /mcp/v1/project_remove endpoint."""

    @pytest.fixture
    def base_url(self) -> str:
        """Base URL for admin MCP server (localhost only)."""
        return "http://127.0.0.1:9384"

    @pytest.mark.contract
    async def test_project_remove_basic_request(self, base_url: str) -> None:
        """Test basic project removal request."""
        request_data = {
            "method": "project_remove",
            "params": {
                "name": "test-remove-project"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/project_remove",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        # Validate response structure according to OpenAPI spec
        assert response.status_code == 200
        data = response.json()

        # Check response schema
        assert "success" in data
        assert isinstance(data["success"], bool)
        assert "data" in data
        assert isinstance(data["data"], dict)

        # Check project operation data structure
        op_data = data["data"]
        required_fields = ["operation", "project_name", "result"]
        for field in required_fields:
            assert field in op_data

        assert op_data["operation"] == "remove"
        assert op_data["project_name"] == "test-remove-project"
        assert isinstance(op_data["result"], str)

    @pytest.mark.contract
    async def test_project_remove_with_confirm(self, base_url: str) -> None:
        """Test project removal with confirm flag."""
        request_data = {
            "method": "project_remove",
            "params": {
                "name": "test-confirm-remove-project",
                "confirm": True
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/project_remove",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()

        op_data = data["data"]
        assert op_data["operation"] == "remove"
        assert op_data["project_name"] == "test-confirm-remove-project"

    @pytest.mark.contract
    async def test_project_remove_with_backup(self, base_url: str) -> None:
        """Test project removal with backup flag."""
        request_data = {
            "method": "project_remove",
            "params": {
                "name": "test-backup-remove-project",
                "backup": True
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/project_remove",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()

        op_data = data["data"]
        assert op_data["operation"] == "remove"
        assert op_data["project_name"] == "test-backup-remove-project"

    @pytest.mark.contract
    async def test_project_remove_with_confirm_and_backup(self, base_url: str) -> None:
        """Test project removal with both confirm and backup flags."""
        request_data = {
            "method": "project_remove",
            "params": {
                "name": "test-full-remove-project",
                "confirm": True,
                "backup": True
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/project_remove",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()

        op_data = data["data"]
        assert op_data["operation"] == "remove"
        assert op_data["project_name"] == "test-full-remove-project"

    @pytest.mark.contract
    async def test_project_remove_missing_name(self, base_url: str) -> None:
        """Test project removal without required name parameter fails."""
        request_data = {
            "method": "project_remove",
            "params": {}
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/project_remove",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        # Should return an error for missing required parameter
        assert response.status_code in [400, 422]

    @pytest.mark.contract
    async def test_project_remove_nonexistent_project(self, base_url: str) -> None:
        """Test removing non-existent project fails gracefully."""
        request_data = {
            "method": "project_remove",
            "params": {
                "name": "non-existent-project-12345"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/project_remove",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        # Should handle non-existent projects gracefully
        assert response.status_code == 200
        data = response.json()

        # Success may be false for non-existent projects
        if not data["success"]:
            assert "error" in data
            assert isinstance(data["error"], str)
        else:
            # Or indicate in the result that project wasn't found
            op_data = data["data"]
            assert op_data["operation"] == "remove"
            assert op_data["project_name"] == "non-existent-project-12345"

    @pytest.mark.contract
    async def test_project_remove_confirm_default_false(self, base_url: str) -> None:
        """Test that confirm parameter defaults to false."""
        request_data = {
            "method": "project_remove",
            "params": {
                "name": "test-default-confirm-project"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/project_remove",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        # Should work even without explicit confirm=true
        # The OpenAPI spec shows confirm defaults to false
        assert response.status_code == 200

    @pytest.mark.contract
    async def test_project_remove_backup_default_false(self, base_url: str) -> None:
        """Test that backup parameter defaults to false."""
        request_data = {
            "method": "project_remove",
            "params": {
                "name": "test-default-backup-project"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/project_remove",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        # Should work even without explicit backup=true
        # The OpenAPI spec shows backup defaults to false
        assert response.status_code == 200