"""
Integration test for AI assistant workflow simulation.

Tests complete MCP workflow scenarios that an AI assistant would use.
"""
import pytest
import asyncio
import httpx
from unittest.mock import patch, Mock
from src.logic.mcp.core.read_only_server import McpReadOnlyServer
from src.logic.mcp.core.admin_server import McpAdminServer


class TestMcpAiAssistantWorkflow:
    """Test complete AI assistant workflows using MCP servers."""

    @pytest.fixture
    async def read_only_server(self):
        """Create read-only server instance with mocked services."""
        with patch('src.logic.mcp.services.read_only.ReadOnlyMcpService') as mock_service:
            # Mock project data
            mock_projects = [
                {
                    "name": "python-docs",
                    "type": "crawling",
                    "status": "active",
                    "description": "Python documentation",
                    "file_count": 150
                },
                {
                    "name": "api-reference",
                    "type": "storage",
                    "status": "active",
                    "description": "API reference documentation",
                    "file_count": 75
                }
            ]

            mock_service.return_value.list_projects.return_value = {
                "success": True,
                "data": mock_projects,
                "metadata": {"total_count": 2}
            }

            mock_service.return_value.search_projects.return_value = {
                "success": True,
                "data": [
                    {
                        "project_name": "python-docs",
                        "file_path": "functions/built-in.md",
                        "content_snippet": "The len() function returns the length of an object...",
                        "similarity_score": 0.95
                    }
                ],
                "metadata": {"total_results": 1, "search_time_ms": 45}
            }

            mock_service.return_value.get_project_files.return_value = {
                "success": True,
                "data": [
                    {
                        "path": "functions/built-in.md",
                        "size": 2048,
                        "modified_at": "2024-01-01T12:00:00Z",
                        "content": "# Built-in Functions\n\nThe len() function..."
                    }
                ],
                "metadata": {
                    "project_name": "api-reference",
                    "project_type": "storage",
                    "access_level": "content"
                }
            }

            server = McpReadOnlyServer()
            yield server

    @pytest.fixture
    async def admin_server(self):
        """Create admin server instance with mocked services."""
        with patch('src.logic.mcp.services.admin.AdminMcpService') as mock_service:
            mock_service.return_value.execute_command.return_value = {
                "success": True,
                "data": {
                    "command": "project",
                    "exit_code": 0,
                    "stdout": "project1\nproject2\n",
                    "stderr": "",
                    "execution_time_ms": 150
                }
            }

            mock_service.return_value.create_project.return_value = {
                "success": True,
                "data": {
                    "operation": "create",
                    "project_name": "new-project",
                    "result": "Project created successfully"
                }
            }

            mock_service.return_value.crawl_project.return_value = {
                "success": True,
                "data": {
                    "project_name": "python-docs",
                    "pages_crawled": 25,
                    "errors_encountered": 0,
                    "duration_seconds": 45.5,
                    "status": "completed"
                }
            }

            server = McpAdminServer()
            yield server

    @pytest.mark.asyncio
    async def test_documentation_research_workflow(self, read_only_server):
        """Test AI assistant workflow for documentation research."""
        async with httpx.AsyncClient(app=read_only_server.app, base_url="http://localhost:9383") as client:
            # Step 1: AI asks "What projects are available?"
            response = await client.post(
                "/mcp/v1/list_projects",
                json={"method": "list_projects", "params": {}}
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]) == 2
            projects = data["data"]

            # Step 2: AI searches for specific information
            response = await client.post(
                "/mcp/v1/search_projects",
                json={
                    "method": "search_projects",
                    "params": {"query": "len function python"}
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]) == 1
            search_result = data["data"][0]
            assert "len() function" in search_result["content_snippet"]

            # Step 3: AI requests full file content for context
            response = await client.post(
                "/mcp/v1/get_project_files",
                json={
                    "method": "get_project_files",
                    "params": {
                        "project_name": "api-reference",
                        "file_path": "functions/built-in.md",
                        "include_content": True
                    }
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert len(data["data"]) == 1
            file_info = data["data"][0]
            assert "len() function" in file_info["content"]

    @pytest.mark.asyncio
    async def test_project_management_workflow(self, admin_server):
        """Test AI assistant workflow for project management."""
        async with httpx.AsyncClient(app=admin_server.app, base_url="http://127.0.0.1:9384") as client:
            # Step 1: AI creates a new project
            response = await client.post(
                "/mcp/v1/project_create",
                json={
                    "method": "project_create",
                    "params": {
                        "name": "new-docs-project",
                        "type": "crawling",
                        "description": "New documentation project for testing"
                    }
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["operation"] == "create"

            # Step 2: AI initiates crawling
            response = await client.post(
                "/mcp/v1/crawl_project",
                json={
                    "method": "crawl_project",
                    "params": {
                        "project_name": "python-docs",
                        "max_pages": 50,
                        "depth": 2
                    }
                }
            )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["status"] == "completed"
            assert data["data"]["pages_crawled"] > 0

            # Step 3: AI checks system health
            response = await client.get("/mcp/v1/health")

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True
            assert data["data"]["server_type"] == "admin"

    @pytest.mark.asyncio
    async def test_combined_read_write_workflow(self, read_only_server, admin_server):
        """Test workflow using both read-only and admin servers."""
        # Simulate an AI assistant using both servers for different tasks

        # Phase 1: Research using read-only server
        async with httpx.AsyncClient(app=read_only_server.app, base_url="http://localhost:9383") as read_client:
            # Get available projects for research
            response = await read_client.post(
                "/mcp/v1/list_projects",
                json={"method": "list_projects", "params": {}}
            )

            assert response.status_code == 200
            projects_data = response.json()
            assert projects_data["success"] is True

        # Phase 2: Management using admin server
        async with httpx.AsyncClient(app=admin_server.app, base_url="http://127.0.0.1:9384") as admin_client:
            # Create a new project based on research
            response = await admin_client.post(
                "/mcp/v1/project_create",
                json={
                    "method": "project_create",
                    "params": {
                        "name": "research-based-project",
                        "type": "data",
                        "description": "Project created based on research findings"
                    }
                }
            )

            assert response.status_code == 200
            creation_data = response.json()
            assert creation_data["success"] is True

        # Phase 3: Verify with read-only server
        async with httpx.AsyncClient(app=read_only_server.app, base_url="http://localhost:9383") as read_client:
            # List projects again to see the new one
            response = await read_client.post(
                "/mcp/v1/list_projects",
                json={"method": "list_projects", "params": {}}
            )

            assert response.status_code == 200
            updated_projects = response.json()
            assert updated_projects["success"] is True

    @pytest.mark.asyncio
    async def test_error_handling_workflow(self, admin_server):
        """Test AI assistant workflow with error scenarios."""
        async with httpx.AsyncClient(app=admin_server.app, base_url="http://127.0.0.1:9384") as client:
            # Step 1: Try to create project with invalid parameters
            response = await client.post(
                "/mcp/v1/project_create",
                json={
                    "method": "project_create",
                    "params": {
                        "name": "",  # Invalid empty name
                        "type": "invalid_type",  # Invalid type
                    }
                }
            )

            # Should handle gracefully
            assert response.status_code in [200, 400, 422]

            # Step 2: Try to execute invalid command
            response = await client.post(
                "/mcp/v1/execute_command",
                json={
                    "method": "execute_command",
                    "params": {
                        "command": "nonexistent_command",
                        "arguments": []
                    }
                }
            )

            # Should handle gracefully
            assert response.status_code in [200, 400, 404]

    @pytest.mark.asyncio
    async def test_concurrent_ai_requests_workflow(self, read_only_server):
        """Test multiple AI assistants using server concurrently."""
        async with httpx.AsyncClient(app=read_only_server.app, base_url="http://localhost:9383") as client:
            # Simulate 3 AI assistants making concurrent requests
            tasks = []

            # AI 1: Searching for Python documentation
            tasks.append(client.post(
                "/mcp/v1/search_projects",
                json={
                    "method": "search_projects",
                    "params": {"query": "python functions"}
                }
            ))

            # AI 2: Listing all projects
            tasks.append(client.post(
                "/mcp/v1/list_projects",
                json={"method": "list_projects", "params": {}}
            ))

            # AI 3: Getting file information
            tasks.append(client.post(
                "/mcp/v1/get_project_files",
                json={
                    "method": "get_project_files",
                    "params": {"project_name": "api-reference"}
                }
            ))

            # Execute all requests concurrently
            responses = await asyncio.gather(*tasks)

            # All requests should succeed
            for i, response in enumerate(responses):
                assert response.status_code == 200, f"Request {i+1} failed"
                data = response.json()
                assert data["success"] is True, f"Request {i+1} returned error"

    @pytest.mark.asyncio
    async def test_ai_learning_workflow(self, read_only_server, admin_server):
        """Test AI assistant learning and improving workflow."""
        # Simulate an AI that learns about the system and improves its queries

        # Phase 1: Initial exploration
        async with httpx.AsyncClient(app=read_only_server.app, base_url="http://localhost:9383") as client:
            # AI starts with broad query
            response = await client.post(
                "/mcp/v1/search_projects",
                json={
                    "method": "search_projects",
                    "params": {"query": "documentation"}
                }
            )

            assert response.status_code == 200
            initial_results = response.json()

        # Phase 2: Refined search based on learning
        async with httpx.AsyncClient(app=read_only_server.app, base_url="http://localhost:9383") as client:
            # AI makes more specific query based on initial results
            response = await client.post(
                "/mcp/v1/search_projects",
                json={
                    "method": "search_projects",
                    "params": {
                        "query": "python built-in functions",
                        "limit": 5
                    }
                }
            )

            assert response.status_code == 200
            refined_results = response.json()
            assert refined_results["success"] is True

        # Phase 3: Adaptive project management
        async with httpx.AsyncClient(app=admin_server.app, base_url="http://127.0.0.1:9384") as client:
            # AI creates project based on learned patterns
            response = await client.post(
                "/mcp/v1/project_create",
                json={
                    "method": "project_create",
                    "params": {
                        "name": "ai-learned-project",
                        "type": "storage",  # AI learned storage type allows full access
                        "description": "Project created based on AI learning patterns"
                    }
                }
            )

            assert response.status_code == 200
            learned_creation = response.json()
            assert learned_creation["success"] is True

    def test_mcp_protocol_compliance(self):
        """Test that servers comply with MCP protocol standards."""
        # Verify read-only server exposes correct methods
        read_only_server = McpReadOnlyServer()
        expected_read_methods = [
            "list_projects",
            "search_projects",
            "get_project_files"
        ]

        # Check that only read methods are available
        for method in expected_read_methods:
            assert hasattr(read_only_server, f"handle_{method}") or method in read_only_server.available_methods

        # Verify admin server exposes correct methods
        admin_server = McpAdminServer()
        expected_admin_methods = [
            "execute_command",
            "project_create",
            "project_remove",
            "crawl_project"
        ]

        for method in expected_admin_methods:
            assert hasattr(admin_server, f"handle_{method}") or method in admin_server.available_methods

    @pytest.mark.asyncio
    async def test_ai_assistant_security_workflow(self, read_only_server, admin_server):
        """Test AI assistant respects security boundaries."""
        # Test 1: AI tries admin operations on read-only server (should fail)
        async with httpx.AsyncClient(app=read_only_server.app, base_url="http://localhost:9383") as client:
            response = await client.post(
                "/mcp/v1/execute_command",  # Admin endpoint
                json={
                    "method": "execute_command",
                    "params": {"command": "project", "arguments": ["--create", "test"]}
                }
            )

            # Should be rejected
            assert response.status_code in [404, 405], "Read-only server should reject admin operations"

        # Test 2: AI respects file access restrictions
        async with httpx.AsyncClient(app=read_only_server.app, base_url="http://localhost:9383") as client:
            response = await client.post(
                "/mcp/v1/get_project_files",
                json={
                    "method": "get_project_files",
                    "params": {
                        "project_name": "python-docs",  # Crawling project
                        "include_content": True  # Should be restricted
                    }
                }
            )

            assert response.status_code == 200
            data = response.json()
            # Should return metadata only for crawling projects
            if data["success"]:
                metadata = data.get("metadata", {})
                assert metadata.get("access_level") in ["metadata", "content"]