"""Contract test for read-only server /mcp/v1/get_project_files endpoint.

This test validates the MCP read-only server's file access endpoint
against the OpenAPI specification in contracts/mcp-read-only-server.json.
"""

import pytest
import httpx


class TestMcpReadOnlyGetProjectFiles:
    """Contract tests for /mcp/v1/get_project_files endpoint."""

    @pytest.fixture
    def base_url(self) -> str:
        """Base URL for read-only MCP server."""
        return "http://localhost:9383"

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_get_project_files_basic_request(self, base_url: str) -> None:
        """Test basic file listing request for a project."""
        request_data = {
            "method": "get_project_files",
            "params": {
                "project_name": "test-project"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/get_project_files",
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
        assert "project_name" in metadata
        assert "project_type" in metadata
        assert "access_level" in metadata
        assert metadata["project_name"] == "test-project"
        assert metadata["access_level"] in ["metadata", "content"]

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_get_project_files_with_specific_file(self, base_url: str) -> None:
        """Test requesting a specific file from a project."""
        request_data = {
            "method": "get_project_files",
            "params": {
                "project_name": "test-project",
                "file_path": "docs/readme.md"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/get_project_files",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()

        # Should return specific file if it exists
        if data["data"]:
            file_info = data["data"][0]
            assert file_info["path"] == "docs/readme.md"

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_get_project_files_storage_project_with_content(self, base_url: str) -> None:
        """Test requesting file content from storage project."""
        request_data = {
            "method": "get_project_files",
            "params": {
                "project_name": "storage-project",
                "include_content": True
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/get_project_files",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()

        # For storage projects, content should be included when requested
        metadata = data["metadata"]
        if metadata["project_type"] == "storage":
            assert metadata["access_level"] == "content"
            # Files should include content field
            for file_info in data["data"]:
                if "content" in file_info:
                    assert isinstance(file_info["content"], str)

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_get_project_files_crawling_project_content_restriction(
        self, base_url: str
    ) -> None:
        """Test that crawling projects only return metadata, not content."""
        request_data = {
            "method": "get_project_files",
            "params": {
                "project_name": "crawling-project",
                "include_content": True
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/get_project_files",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()

        # For crawling projects, should only get metadata
        metadata = data["metadata"]
        if metadata["project_type"] == "crawling":
            assert metadata["access_level"] == "metadata"
            # Files should not include content field
            for file_info in data["data"]:
                assert "content" not in file_info or file_info["content"] is None

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_file_info_schema(self, base_url: str) -> None:
        """Test that file info matches OpenAPI FileInfo schema."""
        request_data = {
            "method": "get_project_files",
            "params": {
                "project_name": "test-project"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/get_project_files",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()

        if data["data"]:  # If there are files
            file_info = data["data"][0]

            # Validate FileInfo schema
            required_fields = ["path", "size", "modified_at", "content_type"]
            for field in required_fields:
                assert field in file_info

            # Validate field types
            assert isinstance(file_info["path"], str)
            assert isinstance(file_info["size"], int)
            assert isinstance(file_info["modified_at"], str)
            assert isinstance(file_info["content_type"], str)

    @pytest.mark.contract
    @pytest.mark.asyncio
    async def test_get_project_files_missing_project_name(self, base_url: str) -> None:
        """Test request without required project_name parameter fails."""
        request_data = {
            "method": "get_project_files",
            "params": {}
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/get_project_files",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        # Should return an error for missing required parameter
        assert response.status_code in [400, 422]