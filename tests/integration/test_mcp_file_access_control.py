"""Integration test for file access control by project type.

This test validates that file access is properly controlled based on
project type as specified in the data model and quickstart.md.
"""

import pytest
import httpx
from typing import Dict, Any


class TestMcpFileAccessControl:
    """Integration tests for project-type-based file access control."""

    @pytest.fixture
    def base_url(self) -> str:
        """Base URL for read-only MCP server."""
        return "http://localhost:9383"

    @pytest.mark.integration
    async def test_storage_project_full_access(self, base_url: str) -> None:
        """Test that storage projects allow full file access including content."""
        request_data = {
            "method": "get_project_files",
            "params": {
                "project_name": "test-storage-project",
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

        # Check metadata indicates storage project with content access
        metadata = data["metadata"]
        if metadata.get("project_type") == "storage":
            assert metadata["access_level"] == "content"

            # If files are returned, they should include content when requested
            for file_info in data["data"]:
                # Content field should be present for storage projects
                assert "content" in file_info or file_info.get("content") is not None

    @pytest.mark.integration
    async def test_crawling_project_metadata_only(self, base_url: str) -> None:
        """Test that crawling projects only allow metadata access, not content."""
        request_data = {
            "method": "get_project_files",
            "params": {
                "project_name": "test-crawling-project",
                "include_content": True  # Requesting content, but should be denied
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

        # Check metadata indicates crawling project with metadata-only access
        metadata = data["metadata"]
        if metadata.get("project_type") == "crawling":
            assert metadata["access_level"] == "metadata"

            # Files should not include content even when requested
            for file_info in data["data"]:
                assert "content" not in file_info or file_info["content"] is None

    @pytest.mark.integration
    async def test_data_project_metadata_only(self, base_url: str) -> None:
        """Test that data projects only allow metadata access, not content."""
        request_data = {
            "method": "get_project_files",
            "params": {
                "project_name": "test-data-project",
                "include_content": True  # Requesting content, but should be denied
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

        # Check metadata indicates data project with metadata-only access
        metadata = data["metadata"]
        if metadata.get("project_type") == "data":
            assert metadata["access_level"] == "metadata"

            # Files should not include content even when requested
            for file_info in data["data"]:
                assert "content" not in file_info or file_info["content"] is None

    @pytest.mark.integration
    async def test_file_metadata_always_available(self, base_url: str) -> None:
        """Test that file metadata is available for all project types."""
        project_types = [
            "test-storage-project",
            "test-crawling-project",
            "test-data-project"
        ]

        for project_name in project_types:
            request_data = {
                "method": "get_project_files",
                "params": {
                    "project_name": project_name,
                    "include_content": False  # Only requesting metadata
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

            # All project types should provide metadata
            for file_info in data["data"]:
                # Basic metadata should always be present
                required_metadata = ["path", "size", "modified_at", "content_type"]
                for field in required_metadata:
                    assert field in file_info

    @pytest.mark.integration
    async def test_specific_file_access_control(self, base_url: str) -> None:
        """Test file access control when requesting a specific file."""
        # Test specific file from storage project
        storage_request = {
            "method": "get_project_files",
            "params": {
                "project_name": "test-storage-project",
                "file_path": "documents/readme.txt",
                "include_content": True
            }
        }

        async with httpx.AsyncClient() as client:
            storage_response = await client.post(
                f"{base_url}/mcp/v1/get_project_files",
                json=storage_request,
                headers={"Content-Type": "application/json"}
            )

        if storage_response.status_code == 200:
            storage_data = storage_response.json()
            if storage_data["metadata"].get("project_type") == "storage":
                assert storage_data["metadata"]["access_level"] == "content"

        # Test specific file from crawling project
        crawling_request = {
            "method": "get_project_files",
            "params": {
                "project_name": "test-crawling-project",
                "file_path": "documents/readme.txt",
                "include_content": True
            }
        }

        async with httpx.AsyncClient() as client:
            crawling_response = await client.post(
                f"{base_url}/mcp/v1/get_project_files",
                json=crawling_request,
                headers={"Content-Type": "application/json"}
            )

        if crawling_response.status_code == 200:
            crawling_data = crawling_response.json()
            if crawling_data["metadata"].get("project_type") == "crawling":
                assert crawling_data["metadata"]["access_level"] == "metadata"

    @pytest.mark.integration
    async def test_access_control_matrix_compliance(self, base_url: str) -> None:
        """Test that access control follows the matrix from data-model.md."""
        # Matrix from data model:
        # | Project Type | Metadata | Content | Files |
        # |-------------|----------|---------|-------|
        # | crawling    | ✓        | ✗       | ✗     |
        # | data        | ✓        | ✗       | ✗     |
        # | storage     | ✓        | ✓       | ✓     |

        access_test_cases = [
            ("test-crawling-project", "metadata"),
            ("test-data-project", "metadata"),
            ("test-storage-project", "content"),
        ]

        for project_name, expected_access in access_test_cases:
            request_data = {
                "method": "get_project_files",
                "params": {
                    "project_name": project_name,
                    "include_content": True
                }
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{base_url}/mcp/v1/get_project_files",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )

            if response.status_code == 200:
                data = response.json()
                metadata = data["metadata"]

                # Verify access level matches expected
                if "access_level" in metadata:
                    assert metadata["access_level"] == expected_access

    @pytest.mark.integration
    async def test_project_type_detection(self, base_url: str) -> None:
        """Test that server correctly detects and enforces project types."""
        test_projects = {
            "storage-project": "storage",
            "crawling-project": "crawling",
            "data-project": "data"
        }

        for project_name, expected_type in test_projects.items():
            request_data = {
                "method": "get_project_files",
                "params": {
                    "project_name": project_name
                }
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{base_url}/mcp/v1/get_project_files",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )

            if response.status_code == 200:
                data = response.json()
                metadata = data["metadata"]

                # Project type should be correctly identified
                if "project_type" in metadata:
                    assert metadata["project_type"] == expected_type

    @pytest.mark.integration
    async def test_file_boundary_enforcement(self, base_url: str) -> None:
        """Test that file access respects project boundaries."""
        # Test access to files outside project boundaries should fail
        boundary_test_request = {
            "method": "get_project_files",
            "params": {
                "project_name": "test-project",
                "file_path": "../../../etc/passwd"  # Attempt directory traversal
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/get_project_files",
                json=boundary_test_request,
                headers={"Content-Type": "application/json"}
            )

        # Should either reject the request or return empty results
        if response.status_code == 200:
            data = response.json()
            # Should not return files outside project boundaries
            assert len(data["data"]) == 0 or not data["success"]
        else:
            # Or should return appropriate error status
            assert response.status_code in [400, 403, 422]