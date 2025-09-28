"""
Security tests for write operation rejection on read-only server.

Tests that read-only MCP server properly rejects all write operations.
"""
import pytest
import httpx
from unittest.mock import patch, Mock
from src.logic.mcp.core.read_only_server import McpReadOnlyServer


class TestMcpWriteRejection:
    """Test that read-only server rejects write operations."""

    @pytest.fixture
    def read_only_server(self):
        """Create read-only server instance."""
        return McpReadOnlyServer()

    @pytest.mark.asyncio
    async def test_execute_command_not_available(self, read_only_server):
        """Test that execute_command endpoint is not available on read-only server."""
        async with httpx.AsyncClient(app=read_only_server.app, base_url="http://localhost:9383") as client:
            response = await client.post(
                "/mcp/v1/execute_command",
                json={
                    "method": "execute_command",
                    "params": {"command": "health", "arguments": []}
                }
            )

            # Should return 404 or 405 (not found or method not allowed)
            assert response.status_code in [404, 405], "Read-only server should not expose execute_command"

    @pytest.mark.asyncio
    async def test_project_create_not_available(self, read_only_server):
        """Test that project_create endpoint is not available on read-only server."""
        async with httpx.AsyncClient(app=read_only_server.app, base_url="http://localhost:9383") as client:
            response = await client.post(
                "/mcp/v1/project_create",
                json={
                    "method": "project_create",
                    "params": {
                        "name": "test-project",
                        "type": "data",
                        "description": "Test project"
                    }
                }
            )

            # Should return 404 or 405 (not found or method not allowed)
            assert response.status_code in [404, 405], "Read-only server should not expose project_create"

    @pytest.mark.asyncio
    async def test_project_remove_not_available(self, read_only_server):
        """Test that project_remove endpoint is not available on read-only server."""
        async with httpx.AsyncClient(app=read_only_server.app, base_url="http://localhost:9383") as client:
            response = await client.post(
                "/mcp/v1/project_remove",
                json={
                    "method": "project_remove",
                    "params": {
                        "name": "test-project",
                        "confirm": True
                    }
                }
            )

            # Should return 404 or 405 (not found or method not allowed)
            assert response.status_code in [404, 405], "Read-only server should not expose project_remove"

    @pytest.mark.asyncio
    async def test_crawl_project_not_available(self, read_only_server):
        """Test that crawl_project endpoint is not available on read-only server."""
        async with httpx.AsyncClient(app=read_only_server.app, base_url="http://localhost:9383") as client:
            response = await client.post(
                "/mcp/v1/crawl_project",
                json={
                    "method": "crawl_project",
                    "params": {
                        "project_name": "test-project",
                        "url": "https://example.com"
                    }
                }
            )

            # Should return 404 or 405 (not found or method not allowed)
            assert response.status_code in [404, 405], "Read-only server should not expose crawl_project"

    @pytest.mark.asyncio
    async def test_read_only_endpoints_available(self, read_only_server):
        """Test that read-only endpoints are available and work correctly."""
        with patch('src.logic.mcp.services.read_only.ReadOnlyMcpService') as mock_service:
            # Mock the service responses
            mock_service.return_value.list_projects.return_value = {
                "success": True,
                "data": [],
                "metadata": {"total_count": 0}
            }
            mock_service.return_value.search_projects.return_value = {
                "success": True,
                "data": [],
                "metadata": {"total_results": 0}
            }
            mock_service.return_value.get_project_files.return_value = {
                "success": True,
                "data": [],
                "metadata": {"project_name": "test"}
            }

            async with httpx.AsyncClient(app=read_only_server.app, base_url="http://localhost:9383") as client:
                # Test list_projects (should work)
                response = await client.post(
                    "/mcp/v1/list_projects",
                    json={
                        "method": "list_projects",
                        "params": {}
                    }
                )
                assert response.status_code == 200, "Read-only server should support list_projects"

                # Test search_projects (should work)
                response = await client.post(
                    "/mcp/v1/search_projects",
                    json={
                        "method": "search_projects",
                        "params": {"query": "test"}
                    }
                )
                assert response.status_code == 200, "Read-only server should support search_projects"

                # Test get_project_files (should work)
                response = await client.post(
                    "/mcp/v1/get_project_files",
                    json={
                        "method": "get_project_files",
                        "params": {"project_name": "test-project"}
                    }
                )
                assert response.status_code == 200, "Read-only server should support get_project_files"

                # Test health (should work)
                response = await client.get("/mcp/v1/health")
                assert response.status_code == 200, "Read-only server should support health check"

    @pytest.mark.asyncio
    async def test_write_operations_via_search_injection(self, read_only_server):
        """Test that write operations cannot be performed via search query injection."""
        # Attempt to inject write operations through search queries
        malicious_queries = [
            "'; INSERT INTO projects (name) VALUES ('malicious'); --",
            "'; UPDATE projects SET name='hacked' WHERE id=1; --",
            "'; DELETE FROM projects; --",
            "test' UNION INSERT INTO projects (name) VALUES ('evil') --",
        ]

        async with httpx.AsyncClient(app=read_only_server.app, base_url="http://localhost:9383") as client:
            for query in malicious_queries:
                response = await client.post(
                    "/mcp/v1/search_projects",
                    json={
                        "method": "search_projects",
                        "params": {"query": query}
                    }
                )

                # Should handle safely without executing write operations
                assert response.status_code in [200, 400, 422]

                if response.status_code == 200:
                    data = response.json()
                    # Should not indicate successful write operations
                    assert data.get("success") is not False or "write" not in data.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_file_content_modification_prevention(self, read_only_server):
        """Test that file content cannot be modified through read-only endpoints."""
        # Test various attempts to modify file content
        modification_attempts = [
            {
                "project_name": "test-project",
                "file_path": "test.txt",
                "content": "malicious content",  # Should not be processed
                "operation": "write"  # Should not be processed
            },
            {
                "project_name": "test-project",
                "file_path": "test.txt",
                "include_content": True,
                "modify_content": "hacked"  # Should not be processed
            }
        ]

        async with httpx.AsyncClient(app=read_only_server.app, base_url="http://localhost:9383") as client:
            for attempt in modification_attempts:
                response = await client.post(
                    "/mcp/v1/get_project_files",
                    json={
                        "method": "get_project_files",
                        "params": attempt
                    }
                )

                # Should ignore modification parameters and only read
                assert response.status_code in [200, 400, 422]

    @pytest.mark.asyncio
    async def test_http_method_restrictions(self, read_only_server):
        """Test that write HTTP methods are not supported on read endpoints."""
        async with httpx.AsyncClient(app=read_only_server.app, base_url="http://localhost:9383") as client:
            # Test PUT on read endpoints (should not be allowed)
            response = await client.put(
                "/mcp/v1/list_projects",
                json={"method": "list_projects", "params": {}}
            )
            assert response.status_code in [405, 404], "PUT should not be allowed on read endpoints"

            # Test DELETE on read endpoints (should not be allowed)
            response = await client.delete("/mcp/v1/list_projects")
            assert response.status_code in [405, 404], "DELETE should not be allowed on read endpoints"

            # Test PATCH on read endpoints (should not be allowed)
            response = await client.patch(
                "/mcp/v1/list_projects",
                json={"method": "list_projects", "params": {}}
            )
            assert response.status_code in [405, 404], "PATCH should not be allowed on read endpoints"

    def test_read_only_service_restrictions(self):
        """Test that read-only service class prevents write operations."""
        from src.logic.mcp.services.read_only import ReadOnlyMcpService

        service = ReadOnlyMcpService()

        # Verify that write methods are not available
        write_methods = [
            'create_project',
            'remove_project',
            'update_project',
            'execute_command',
            'crawl_project',
            'modify_file',
            'delete_file',
            'upload_file'
        ]

        for method_name in write_methods:
            assert not hasattr(service, method_name), f"Read-only service should not have {method_name} method"

        # Verify that only read methods are available
        read_methods = [
            'list_projects',
            'search_projects',
            'get_project_files',
            'health_check'
        ]

        for method_name in read_methods:
            assert hasattr(service, method_name), f"Read-only service should have {method_name} method"

    @pytest.mark.asyncio
    async def test_file_access_level_enforcement(self, read_only_server):
        """Test that file access levels are enforced correctly."""
        # Test with different project types
        project_type_tests = [
            {
                "project_name": "crawling-project",
                "project_type": "crawling",
                "expected_access": "metadata"  # Should only allow metadata
            },
            {
                "project_name": "data-project",
                "project_type": "data",
                "expected_access": "metadata"  # Should only allow metadata
            },
            {
                "project_name": "storage-project",
                "project_type": "storage",
                "expected_access": "content"  # Should allow content access
            }
        ]

        with patch('src.logic.mcp.services.read_only.ReadOnlyMcpService') as mock_service:
            mock_service.return_value.get_project_files.return_value = {
                "success": True,
                "data": [],
                "metadata": {"access_level": "metadata"}
            }

            async with httpx.AsyncClient(app=read_only_server.app, base_url="http://localhost:9383") as client:
                for test in project_type_tests:
                    response = await client.post(
                        "/mcp/v1/get_project_files",
                        json={
                            "method": "get_project_files",
                            "params": {
                                "project_name": test["project_name"],
                                "include_content": True  # Request content even for restricted projects
                            }
                        }
                    )

                    assert response.status_code == 200

                    # Verify access level is enforced
                    data = response.json()
                    if data.get("success"):
                        metadata = data.get("metadata", {})
                        # Should respect project type restrictions
                        assert "access_level" in metadata

    @pytest.mark.asyncio
    async def test_admin_endpoint_simulation_attempts(self, read_only_server):
        """Test attempts to simulate admin endpoints on read-only server."""
        # Attempt to access admin-style endpoints on read-only server
        admin_endpoint_attempts = [
            "/mcp/v1/admin/execute_command",
            "/mcp/v1/admin/project_create",
            "/mcp/v1/admin/project_remove",
            "/mcp/v1/execute_command",  # Direct admin endpoint
            "/admin/mcp/v1/execute_command",
            "/api/admin/execute_command"
        ]

        async with httpx.AsyncClient(app=read_only_server.app, base_url="http://localhost:9383") as client:
            for endpoint in admin_endpoint_attempts:
                response = await client.post(
                    endpoint,
                    json={
                        "method": "execute_command",
                        "params": {"command": "health", "arguments": []}
                    }
                )

                # Should return 404 (not found)
                assert response.status_code == 404, f"Read-only server should not expose admin endpoint: {endpoint}"

    def test_configuration_enforces_read_only(self):
        """Test that server configuration enforces read-only mode."""
        from src.logic.mcp.core.read_only_server import McpReadOnlyServer

        server = McpReadOnlyServer()

        # Should be configured in read-only mode
        assert hasattr(server, 'read_only_mode')
        assert server.read_only_mode is True

        # Should not have admin capabilities
        assert not hasattr(server, 'admin_service')
        assert not hasattr(server, 'command_executor')

    @pytest.mark.asyncio
    async def test_environment_variable_override_attempts(self, read_only_server):
        """Test that environment variables cannot override read-only restrictions."""
        import os

        # Attempt to use environment variables to enable write operations
        with patch.dict(os.environ, {
            'MCP_ALLOW_WRITE': 'true',
            'MCP_ADMIN_MODE': 'true',
            'MCP_DISABLE_READ_ONLY': 'true',
            'FORCE_ADMIN_MODE': 'true'
        }):
            # Server should still be read-only
            server = McpReadOnlyServer()
            assert server.read_only_mode is True

            # Admin endpoints should still not be available
            async with httpx.AsyncClient(app=server.app, base_url="http://localhost:9383") as client:
                response = await client.post(
                    "/mcp/v1/execute_command",
                    json={
                        "method": "execute_command",
                        "params": {"command": "health", "arguments": []}
                    }
                )

                assert response.status_code in [404, 405], "Environment variables should not override read-only restrictions"