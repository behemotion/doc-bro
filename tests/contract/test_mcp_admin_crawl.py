"""Contract test for admin server /mcp/v1/crawl_project endpoint.

This test validates the MCP admin server's project crawling endpoint
against the OpenAPI specification in contracts/mcp-admin-server.json.
"""

import pytest
import httpx


class TestMcpAdminCrawlProject:
    """Contract tests for /mcp/v1/crawl_project endpoint."""

    @pytest.fixture
    def base_url(self) -> str:
        """Base URL for admin MCP server (localhost only)."""
        return "http://127.0.0.1:9384"

    @pytest.mark.contract
    async def test_crawl_project_basic_request(self, base_url: str) -> None:
        """Test basic project crawling request."""
        request_data = {
            "method": "crawl_project",
            "params": {
                "project_name": "test-crawl-project"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/crawl_project",
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

        # Check crawl operation data structure
        crawl_data = data["data"]
        required_fields = ["project_name", "pages_crawled", "errors_encountered",
                          "duration_seconds", "status"]
        for field in required_fields:
            assert field in crawl_data

        assert crawl_data["project_name"] == "test-crawl-project"
        assert isinstance(crawl_data["pages_crawled"], int)
        assert isinstance(crawl_data["errors_encountered"], int)
        assert isinstance(crawl_data["duration_seconds"], (int, float))
        assert crawl_data["status"] in ["completed", "partial", "failed"]

    @pytest.mark.contract
    async def test_crawl_project_with_url(self, base_url: str) -> None:
        """Test project crawling with specific URL."""
        request_data = {
            "method": "crawl_project",
            "params": {
                "project_name": "test-url-crawl-project",
                "url": "https://example.com/docs"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/crawl_project",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()

        crawl_data = data["data"]
        assert crawl_data["project_name"] == "test-url-crawl-project"

    @pytest.mark.contract
    async def test_crawl_project_with_max_pages(self, base_url: str) -> None:
        """Test project crawling with max_pages limit."""
        request_data = {
            "method": "crawl_project",
            "params": {
                "project_name": "test-limited-crawl-project",
                "max_pages": 10
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/crawl_project",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()

        crawl_data = data["data"]
        assert crawl_data["project_name"] == "test-limited-crawl-project"
        # Pages crawled should respect the limit
        assert crawl_data["pages_crawled"] <= 10

    @pytest.mark.contract
    async def test_crawl_project_with_depth(self, base_url: str) -> None:
        """Test project crawling with depth setting."""
        request_data = {
            "method": "crawl_project",
            "params": {
                "project_name": "test-depth-crawl-project",
                "depth": 2
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/crawl_project",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()

        crawl_data = data["data"]
        assert crawl_data["project_name"] == "test-depth-crawl-project"

    @pytest.mark.contract
    async def test_crawl_project_with_rate_limit(self, base_url: str) -> None:
        """Test project crawling with rate limit setting."""
        request_data = {
            "method": "crawl_project",
            "params": {
                "project_name": "test-rate-limit-crawl-project",
                "rate_limit": 0.5
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/crawl_project",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()

        crawl_data = data["data"]
        assert crawl_data["project_name"] == "test-rate-limit-crawl-project"

    @pytest.mark.contract
    async def test_crawl_project_all_parameters(self, base_url: str) -> None:
        """Test project crawling with all optional parameters."""
        request_data = {
            "method": "crawl_project",
            "params": {
                "project_name": "test-full-crawl-project",
                "url": "https://example.com/docs",
                "max_pages": 5,
                "depth": 3,
                "rate_limit": 1.0
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/crawl_project",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()

        crawl_data = data["data"]
        assert crawl_data["project_name"] == "test-full-crawl-project"

    @pytest.mark.contract
    async def test_crawl_project_missing_project_name(self, base_url: str) -> None:
        """Test project crawling without required project_name parameter fails."""
        request_data = {
            "method": "crawl_project",
            "params": {}
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/crawl_project",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        # Should return an error for missing required parameter
        assert response.status_code in [400, 422]

    @pytest.mark.contract
    async def test_crawl_project_invalid_url(self, base_url: str) -> None:
        """Test project crawling with invalid URL format."""
        request_data = {
            "method": "crawl_project",
            "params": {
                "project_name": "test-invalid-url-project",
                "url": "not-a-valid-url"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/crawl_project",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        # Should validate URL format
        if response.status_code == 200:
            data = response.json()
            # If successful response, check if error is indicated
            if not data["success"]:
                assert "error" in data
        else:
            # Or return appropriate error status
            assert response.status_code in [400, 422]

    @pytest.mark.contract
    async def test_crawl_project_nonexistent_project(self, base_url: str) -> None:
        """Test crawling non-existent project fails gracefully."""
        request_data = {
            "method": "crawl_project",
            "params": {
                "project_name": "non-existent-crawl-project-12345"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/crawl_project",
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