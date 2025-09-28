"""Contract test for read-only server /mcp/v1/search_projects endpoint.

This test validates the MCP read-only server's search endpoint
against the OpenAPI specification in contracts/mcp-read-only-server.json.
"""

import pytest
import httpx


class TestMcpReadOnlySearchProjects:
    """Contract tests for /mcp/v1/search_projects endpoint."""

    @pytest.fixture
    def base_url(self) -> str:
        """Base URL for read-only MCP server."""
        return "http://localhost:9383"

    @pytest.mark.contract
    async def test_search_projects_basic_request(self, base_url: str) -> None:
        """Test basic search request with required query parameter."""
        request_data = {
            "method": "search_projects",
            "params": {
                "query": "test documentation"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/search_projects",
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
        assert "query" in metadata
        assert "total_results" in metadata
        assert "search_time_ms" in metadata
        assert metadata["query"] == "test documentation"
        assert isinstance(metadata["total_results"], int)
        assert isinstance(metadata["search_time_ms"], (int, float))

    @pytest.mark.contract
    async def test_search_projects_with_project_filter(self, base_url: str) -> None:
        """Test search with project_names filter."""
        request_data = {
            "method": "search_projects",
            "params": {
                "query": "documentation",
                "project_names": ["test-project", "docs-project"]
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/search_projects",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()

        # Validate that all results are from specified projects
        for result in data["data"]:
            assert result["project_name"] in ["test-project", "docs-project"]

    @pytest.mark.contract
    async def test_search_projects_with_limit(self, base_url: str) -> None:
        """Test search with limit parameter."""
        request_data = {
            "method": "search_projects",
            "params": {
                "query": "documentation",
                "limit": 3
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/search_projects",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()

        # Validate limit is respected
        assert len(data["data"]) <= 3

    @pytest.mark.contract
    async def test_search_result_schema(self, base_url: str) -> None:
        """Test that search results match OpenAPI SearchResult schema."""
        request_data = {
            "method": "search_projects",
            "params": {
                "query": "test",
                "limit": 1
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/search_projects",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()

        if data["data"]:  # If there are search results
            result = data["data"][0]

            # Validate SearchResult schema
            required_fields = ["project_name", "file_path", "content_snippet",
                             "similarity_score", "metadata"]
            for field in required_fields:
                assert field in result

            # Validate field types and constraints
            assert isinstance(result["project_name"], str)
            assert isinstance(result["file_path"], str)
            assert isinstance(result["content_snippet"], str)
            assert isinstance(result["similarity_score"], (int, float))
            assert 0 <= result["similarity_score"] <= 1
            assert isinstance(result["metadata"], dict)

    @pytest.mark.contract
    async def test_search_projects_missing_query(self, base_url: str) -> None:
        """Test search request without required query parameter fails."""
        request_data = {
            "method": "search_projects",
            "params": {}
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/search_projects",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        # Should return an error for missing required parameter
        assert response.status_code in [400, 422]