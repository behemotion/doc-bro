"""Contract test for admin server /mcp/v1/project_create endpoint.

This test validates the MCP admin server's project creation endpoint
against the OpenAPI specification in contracts/mcp-admin-server.json.
"""

import pytest
import httpx


class TestMcpAdminProjectCreate:
    """Contract tests for /mcp/v1/project_create endpoint."""

    @pytest.fixture
    def base_url(self) -> str:
        """Base URL for admin MCP server (localhost only)."""
        return "http://127.0.0.1:9384"

    @pytest.mark.contract
    async def test_project_create_basic_request(self, base_url: str) -> None:
        """Test basic project creation request."""
        request_data = {
            "method": "project_create",
            "params": {
                "name": "test-mcp-project",
                "type": "data"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/project_create",
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

        assert op_data["operation"] == "create"
        assert op_data["project_name"] == "test-mcp-project"
        assert isinstance(op_data["result"], str)

    @pytest.mark.contract
    async def test_project_create_with_description(self, base_url: str) -> None:
        """Test project creation with description."""
        request_data = {
            "method": "project_create",
            "params": {
                "name": "test-described-project",
                "type": "storage",
                "description": "Test project created via MCP admin server"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/project_create",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()

        op_data = data["data"]
        assert op_data["operation"] == "create"
        assert op_data["project_name"] == "test-described-project"

    @pytest.mark.contract
    async def test_project_create_with_settings(self, base_url: str) -> None:
        """Test project creation with custom settings."""
        request_data = {
            "method": "project_create",
            "params": {
                "name": "test-configured-project",
                "type": "crawling",
                "description": "Project with custom settings",
                "settings": {
                    "crawl_depth": 2,
                    "rate_limit": 1.5
                }
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/project_create",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()

        op_data = data["data"]
        assert op_data["operation"] == "create"
        assert op_data["project_name"] == "test-configured-project"

    @pytest.mark.contract
    async def test_project_create_all_project_types(self, base_url: str) -> None:
        """Test project creation for all valid project types."""
        project_types = ["crawling", "data", "storage"]

        for project_type in project_types:
            request_data = {
                "method": "project_create",
                "params": {
                    "name": f"test-{project_type}-project",
                    "type": project_type
                }
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{base_url}/mcp/v1/project_create",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )

            # Should accept all valid project types
            assert response.status_code == 200

    @pytest.mark.contract
    async def test_project_create_missing_name(self, base_url: str) -> None:
        """Test project creation without required name parameter fails."""
        request_data = {
            "method": "project_create",
            "params": {
                "type": "data"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/project_create",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        # Should return an error for missing required parameter
        assert response.status_code in [400, 422]

    @pytest.mark.contract
    async def test_project_create_missing_type(self, base_url: str) -> None:
        """Test project creation without required type parameter fails."""
        request_data = {
            "method": "project_create",
            "params": {
                "name": "test-no-type-project"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/project_create",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        # Should return an error for missing required parameter
        assert response.status_code in [400, 422]

    @pytest.mark.contract
    async def test_project_create_invalid_type(self, base_url: str) -> None:
        """Test project creation with invalid type fails."""
        request_data = {
            "method": "project_create",
            "params": {
                "name": "test-invalid-type-project",
                "type": "invalid_type"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/project_create",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        # Should return an error for invalid project type
        assert response.status_code in [400, 422]

    @pytest.mark.contract
    async def test_project_create_duplicate_name(self, base_url: str) -> None:
        """Test creating project with duplicate name fails gracefully."""
        request_data = {
            "method": "project_create",
            "params": {
                "name": "duplicate-project",
                "type": "data"
            }
        }

        async with httpx.AsyncClient() as client:
            # Try to create the same project twice
            response1 = await client.post(
                f"{base_url}/mcp/v1/project_create",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

            response2 = await client.post(
                f"{base_url}/mcp/v1/project_create",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        # First creation might succeed
        assert response1.status_code == 200

        # Second creation should handle duplicate gracefully
        if response2.status_code == 200:
            data = response2.json()
            # If successful response, check if error is indicated
            if not data["success"]:
                assert "error" in data
        else:
            # Or return appropriate error status
            assert response2.status_code in [400, 409, 422]