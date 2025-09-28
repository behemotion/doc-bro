"""Contract test for read-only server /mcp/v1/list_projects endpoint.

This test validates the MCP read-only server's project listing endpoint
against the OpenAPI specification in contracts/mcp-read-only-server.json.
"""

import pytest
import httpx
from typing import Any, Dict


class TestMcpReadOnlyListProjects:
    """Contract tests for /mcp/v1/list_projects endpoint."""

    @pytest.fixture
    def base_url(self) -> str:
        """Base URL for read-only MCP server."""
        return "http://localhost:9383"

    @pytest.mark.contract
    async def test_list_projects_basic_request(self, base_url: str) -> None:
        """Test basic project listing request."""
        request_data = {
            "method": "list_projects",
            "params": {}
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/list_projects",
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
        assert isinstance(data["data"], list)
        assert "metadata" in data
        assert isinstance(data["metadata"], dict)

        # Check metadata structure
        metadata = data["metadata"]
        assert "total_count" in metadata
        assert "filtered_count" in metadata
        assert isinstance(metadata["total_count"], int)
        assert isinstance(metadata["filtered_count"], int)

    @pytest.mark.contract
    async def test_list_projects_with_status_filter(self, base_url: str) -> None:
        """Test project listing with status filter."""
        request_data = {
            "method": "list_projects",
            "params": {
                "status_filter": "active"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/list_projects",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()

        # Validate that all returned projects have active status
        for project in data["data"]:
            assert project["status"] == "active"

    @pytest.mark.contract
    async def test_list_projects_with_limit(self, base_url: str) -> None:
        """Test project listing with limit parameter."""
        request_data = {
            "method": "list_projects",
            "params": {
                "limit": 5
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/list_projects",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()

        # Validate limit is respected
        assert len(data["data"]) <= 5

    @pytest.mark.contract
    async def test_project_metadata_schema(self, base_url: str) -> None:
        """Test that project metadata matches OpenAPI schema."""
        request_data = {
            "method": "list_projects",
            "params": {"limit": 1}
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/list_projects",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()

        if data["data"]:  # If there are projects
            project = data["data"][0]

            # Validate ProjectMetadata schema
            required_fields = ["name", "type", "status", "description",
                             "created_at", "last_updated", "file_count"]
            for field in required_fields:
                assert field in project

            # Validate field types and constraints
            assert isinstance(project["name"], str)
            assert project["type"] in ["crawling", "data", "storage"]
            assert project["status"] in ["active", "inactive", "error", "processing"]
            assert isinstance(project["description"], str)
            assert isinstance(project["file_count"], int)