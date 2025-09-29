"""Contract tests for MCP shelf/basket endpoints.

Tests the MCP endpoint contracts defined in specs/017-projects-as-collections/contracts/mcp-shelf-endpoints.md.
These tests will initially FAIL as the shelf-aware MCP endpoints do not exist yet.
"""

import pytest
import httpx
import json
from unittest.mock import AsyncMock, patch

pytestmark = [pytest.mark.contract, pytest.mark.async_test]


class TestMcpReadOnlyShelfEndpoints:
    """Contract tests for read-only MCP server shelf endpoints."""

    @pytest.fixture
    def base_url(self) -> str:
        """Base URL for read-only MCP server."""
        return "http://0.0.0.0:9383"

    @pytest.mark.contract
    async def test_list_shelfs_endpoint_exists(self, base_url: str) -> None:
        """Test that the list_shelfs endpoint is available."""
        request_data = {
            "method": "list_shelfs",
            "params": {
                "include_baskets": True,
                "limit": 50
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/list_shelfs",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        # Should return valid response when implemented
        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert isinstance(data["success"], bool)

    @pytest.mark.contract
    async def test_list_shelfs_response_structure(self, base_url: str) -> None:
        """Test list_shelfs response follows the contract structure."""
        request_data = {
            "method": "list_shelfs",
            "params": {
                "include_baskets": True,
                "include_empty": False,
                "limit": 50
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/list_shelfs",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "success" in data
        assert "data" in data
        assert isinstance(data["data"], list)

        if data["data"]:  # If shelfs exist
            shelf = data["data"][0]
            required_fields = ["name", "created_at", "updated_at", "is_current", "basket_count"]
            for field in required_fields:
                assert field in shelf

            if "baskets" in shelf:
                assert isinstance(shelf["baskets"], list)
                if shelf["baskets"]:
                    basket = shelf["baskets"][0]
                    basket_fields = ["name", "type", "status", "files"]
                    for field in basket_fields:
                        assert field in basket

        # Validate metadata
        if "metadata" in data:
            metadata = data["metadata"]
            metadata_fields = ["total_shelfs", "current_shelf", "total_baskets"]
            for field in metadata_fields:
                assert field in metadata

    @pytest.mark.contract
    async def test_list_shelfs_parameters(self, base_url: str) -> None:
        """Test list_shelfs with different parameter combinations."""
        test_cases = [
            # Basic request
            {"include_baskets": True, "limit": 10},
            # Without baskets
            {"include_baskets": False, "limit": 20},
            # Current only
            {"current_only": True, "include_baskets": True},
            # Include empty shelfs
            {"include_empty": True, "include_baskets": False}
        ]

        for params in test_cases:
            request_data = {
                "method": "list_shelfs",
                "params": params
            }

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{base_url}/mcp/v1/list_shelfs",
                    json=request_data,
                    headers={"Content-Type": "application/json"}
                )

            assert response.status_code == 200
            data = response.json()
            assert data["success"] is True

    @pytest.mark.contract
    async def test_get_shelf_structure_endpoint(self, base_url: str) -> None:
        """Test get_shelf_structure endpoint contract."""
        request_data = {
            "method": "get_shelf_structure",
            "params": {
                "shelf_name": "documentation",
                "include_basket_details": True,
                "include_file_list": False
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/get_shelf_structure",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()

        # Validate response structure
        assert "success" in data
        assert "data" in data

        if data["success"]:
            response_data = data["data"]
            assert "shelf" in response_data
            assert "baskets" in response_data
            assert "summary" in response_data

            # Validate shelf info
            shelf_info = response_data["shelf"]
            shelf_fields = ["name", "created_at", "updated_at", "is_current"]
            for field in shelf_fields:
                assert field in shelf_info

            # Validate baskets
            baskets = response_data["baskets"]
            assert isinstance(baskets, list)

            # Validate summary
            summary = response_data["summary"]
            summary_fields = ["total_baskets", "total_files", "total_size_bytes"]
            for field in summary_fields:
                assert field in summary

    @pytest.mark.contract
    async def test_get_shelf_structure_missing_shelf(self, base_url: str) -> None:
        """Test get_shelf_structure with non-existent shelf."""
        request_data = {
            "method": "get_shelf_structure",
            "params": {
                "shelf_name": "non-existent-shelf-12345"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/get_shelf_structure",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        # Should handle gracefully
        data = response.json()
        if not data.get("success", True):
            assert "error" in data
            assert "shelf_not_found" in data.get("error", "")

    @pytest.mark.contract
    async def test_enhanced_list_projects_with_shelf_filter(self, base_url: str) -> None:
        """Test enhanced list_projects endpoint with shelf filtering."""
        request_data = {
            "method": "list_projects",
            "params": {
                "shelf_name": "documentation",
                "include_shelf_context": True,
                "status_filter": "ready",
                "limit": 25
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
        assert "success" in data

        if data["success"] and data.get("data"):
            # Validate enhanced project structure
            project = data["data"][0]

            # Existing fields (backward compatibility)
            existing_fields = ["id", "name", "status", "type", "created_at"]
            for field in existing_fields:
                assert field in project

            # New shelf context fields
            if "include_shelf_context" in request_data["params"]:
                shelf_fields = ["shelf_name", "basket_type", "hierarchy_path"]
                for field in shelf_fields:
                    assert field in project

    @pytest.mark.contract
    async def test_enhanced_search_projects_shelf_aware(self, base_url: str) -> None:
        """Test enhanced search_projects with shelf awareness."""
        request_data = {
            "method": "search_projects",
            "params": {
                "query": "authentication methods",
                "shelf_names": ["documentation", "examples"],
                "basket_types": ["crawling", "data"],
                "include_shelf_context": True,
                "limit": 20
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
        assert "success" in data

        if data["success"] and data.get("data"):
            # Validate enhanced search results
            result = data["data"][0]

            # Existing fields
            existing_fields = ["file_path", "content_snippet", "similarity_score"]
            for field in existing_fields:
                assert field in result

            # New hierarchical context fields
            context_fields = ["shelf_name", "basket_name", "hierarchy_path"]
            for field in context_fields:
                assert field in result

            # Validate metadata
            if "metadata" in data:
                metadata = data["metadata"]
                enhanced_fields = ["shelf_breakdown", "basket_breakdown", "search_scope"]
                for field in enhanced_fields:
                    assert field in metadata

    @pytest.mark.contract
    async def test_get_current_shelf_endpoint(self, base_url: str) -> None:
        """Test get_current_shelf endpoint."""
        request_data = {
            "method": "get_current_shelf",
            "params": {}
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/get_current_shelf",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data
        assert "data" in data

        response_data = data["data"]

        if response_data.get("current_shelf"):
            # Validate current shelf structure
            current_shelf = response_data["current_shelf"]
            shelf_fields = ["name", "created_at", "basket_count", "total_files"]
            for field in shelf_fields:
                assert field in current_shelf

            # Validate context
            assert "context" in response_data
            context = response_data["context"]
            context_fields = ["session_id", "last_context_update"]
            for field in context_fields:
                assert field in context
        else:
            # No current shelf set
            assert "available_shelfs" in response_data
            assert isinstance(response_data["available_shelfs"], list)


class TestMcpAdminShelfEndpoints:
    """Contract tests for admin MCP server shelf management endpoints."""

    @pytest.fixture
    def admin_base_url(self) -> str:
        """Base URL for admin MCP server (localhost only)."""
        return "http://127.0.0.1:9384"

    @pytest.mark.contract
    async def test_create_shelf_endpoint(self, admin_base_url: str) -> None:
        """Test create_shelf admin endpoint."""
        request_data = {
            "method": "create_shelf",
            "params": {
                "name": "test-new-shelf",
                "description": "Test shelf creation",
                "set_current": False,
                "force": False
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{admin_base_url}/mcp/v1/create_shelf",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data

        if data["success"]:
            # Validate operation response structure
            assert "data" in data
            op_data = data["data"]

            required_fields = ["operation", "shelf_name", "result"]
            for field in required_fields:
                assert field in op_data

            assert op_data["operation"] == "create_shelf"
            assert op_data["shelf_name"] == "test-new-shelf"
            assert op_data["result"] in ["created", "updated"]

            # Validate details
            if "details" in op_data:
                details = op_data["details"]
                detail_fields = ["shelf_id", "created_at", "is_current"]
                for field in detail_fields:
                    assert field in details

    @pytest.mark.contract
    async def test_create_shelf_with_set_current(self, admin_base_url: str) -> None:
        """Test create_shelf with set_current flag."""
        request_data = {
            "method": "create_shelf",
            "params": {
                "name": "current-test-shelf",
                "set_current": True
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{admin_base_url}/mcp/v1/create_shelf",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()

        if data.get("success"):
            op_data = data["data"]
            if "details" in op_data:
                assert op_data["details"].get("is_current") is True

    @pytest.mark.contract
    async def test_delete_shelf_security_restriction(self, admin_base_url: str) -> None:
        """Test that delete_shelf is prohibited via MCP admin for security."""
        request_data = {
            "method": "delete_shelf",
            "params": {
                "name": "test-shelf-to-delete",
                "force": True,
                "confirm": True
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{admin_base_url}/mcp/v1/delete_shelf",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        # Should be prohibited for security
        data = response.json()
        assert data["success"] is False
        assert "operation_prohibited" in data.get("error", "")
        assert "security" in data.get("message", "").lower()

        # Should suggest CLI alternative
        if "details" in data:
            details = data["details"]
            assert "CLI only" in details.get("allowed_methods", [])
            assert "docbro shelf --remove" in details.get("alternative", "")

    @pytest.mark.contract
    async def test_add_basket_endpoint(self, admin_base_url: str) -> None:
        """Test add_basket admin endpoint."""
        request_data = {
            "method": "add_basket",
            "params": {
                "shelf_name": "documentation",
                "basket_name": "new-api-docs",
                "basket_type": "crawling",
                "description": "New API documentation",
                "force": False
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{admin_base_url}/mcp/v1/add_basket",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data

        if data["success"]:
            op_data = data["data"]

            required_fields = ["operation", "shelf_name", "basket_name", "result"]
            for field in required_fields:
                assert field in op_data

            assert op_data["operation"] == "add_basket"
            assert op_data["shelf_name"] == "documentation"
            assert op_data["basket_name"] == "new-api-docs"

            # Validate details
            if "details" in op_data:
                details = op_data["details"]
                detail_fields = ["basket_id", "basket_type", "status", "created_at"]
                for field in detail_fields:
                    assert field in details

    @pytest.mark.contract
    async def test_add_basket_default_type(self, admin_base_url: str) -> None:
        """Test add_basket with default type (data)."""
        request_data = {
            "method": "add_basket",
            "params": {
                "shelf_name": "documentation",
                "basket_name": "default-type-basket"
                # No basket_type specified - should default to "data"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{admin_base_url}/mcp/v1/add_basket",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()

        if data.get("success"):
            op_data = data["data"]
            if "details" in op_data:
                assert op_data["details"].get("basket_type") == "data"

    @pytest.mark.contract
    async def test_remove_basket_endpoint(self, admin_base_url: str) -> None:
        """Test remove_basket admin endpoint."""
        request_data = {
            "method": "remove_basket",
            "params": {
                "shelf_name": "documentation",
                "basket_name": "old-basket",
                "confirm": True,
                "backup": True
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{admin_base_url}/mcp/v1/remove_basket",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data

        if data["success"]:
            op_data = data["data"]

            required_fields = ["operation", "shelf_name", "basket_name", "result"]
            for field in required_fields:
                assert field in op_data

            assert op_data["operation"] == "remove_basket"

            # Validate removal details
            if "details" in op_data:
                details = op_data["details"]
                assert "files_deleted" in details
                assert isinstance(details["files_deleted"], int)

    @pytest.mark.contract
    async def test_set_current_shelf_endpoint(self, admin_base_url: str) -> None:
        """Test set_current_shelf admin endpoint."""
        request_data = {
            "method": "set_current_shelf",
            "params": {
                "shelf_name": "examples"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{admin_base_url}/mcp/v1/set_current_shelf",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        assert response.status_code == 200
        data = response.json()
        assert "success" in data

        if data["success"]:
            op_data = data["data"]

            required_fields = ["operation", "shelf_name", "result"]
            for field in required_fields:
                assert field in op_data

            assert op_data["operation"] == "set_current_shelf"
            assert op_data["shelf_name"] == "examples"

            # Validate context update details
            if "details" in op_data:
                details = op_data["details"]
                context_fields = ["previous_current", "new_current", "context_updated", "session_id"]
                for field in context_fields:
                    assert field in details

    @pytest.mark.contract
    async def test_admin_endpoint_localhost_only(self, admin_base_url: str) -> None:
        """Test that admin endpoints are only accessible from localhost."""
        # This test assumes the server enforces localhost-only access
        # In practice, this might be enforced at the network level

        request_data = {
            "method": "create_shelf",
            "params": {
                "name": "security-test-shelf"
            }
        }

        # Try to access from localhost - should work
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{admin_base_url}/mcp/v1/create_shelf",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        # Should either succeed or fail gracefully (not return 403/404 for wrong host)
        assert response.status_code in [200, 400, 422, 500]  # Any response means server is accessible


class TestMcpShelfEndpointErrorHandling:
    """Contract tests for error handling across shelf endpoints."""

    @pytest.fixture
    def base_url(self) -> str:
        """Base URL for read-only MCP server."""
        return "http://0.0.0.0:9383"

    @pytest.mark.contract
    async def test_shelf_not_found_error(self, base_url: str) -> None:
        """Test shelf_not_found error response format."""
        request_data = {
            "method": "get_shelf_structure",
            "params": {
                "shelf_name": "definitely-nonexistent-shelf-12345"
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/get_shelf_structure",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        data = response.json()

        if not data.get("success", True):
            # Validate error response structure
            assert "error" in data
            assert "message" in data
            assert isinstance(data["message"], str)

            if "details" in data:
                details = data["details"]
                assert "error_code" in details
                assert details.get("error_code") in ["SHELF_NOT_FOUND", "shelf_not_found"]

    @pytest.mark.contract
    async def test_invalid_request_error(self, base_url: str) -> None:
        """Test validation error for invalid request parameters."""
        request_data = {
            "method": "list_shelfs",
            "params": {
                "limit": -1,  # Invalid limit
                "include_baskets": "not_a_boolean"  # Invalid type
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/list_shelfs",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        # Should return validation error
        assert response.status_code in [400, 422]
        data = response.json()

        if not data.get("success", True):
            assert "error" in data
            assert "validation" in data.get("error", "").lower()

    @pytest.mark.contract
    async def test_missing_required_parameters(self, base_url: str) -> None:
        """Test error for missing required parameters."""
        request_data = {
            "method": "get_shelf_structure",
            "params": {
                # Missing required "shelf_name" parameter
            }
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{base_url}/mcp/v1/get_shelf_structure",
                json=request_data,
                headers={"Content-Type": "application/json"}
            )

        # Should return parameter error
        assert response.status_code in [400, 422]


class TestMcpShelfBackwardCompatibility:
    """Contract tests for backward compatibility with existing MCP endpoints."""

    @pytest.fixture
    def base_url(self) -> str:
        """Base URL for read-only MCP server."""
        return "http://0.0.0.0:9383"

    @pytest.mark.contract
    async def test_legacy_list_projects_still_works(self, base_url: str) -> None:
        """Test that legacy list_projects requests work unchanged."""
        # Exact same request format as before shelf implementation
        request_data = {
            "method": "list_projects",
            "params": {
                "status_filter": "ready",
                "limit": 25
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
        assert "success" in data

        if data["success"] and data.get("data"):
            # Should still return projects in legacy format
            project = data["data"][0]
            legacy_fields = ["id", "name", "status", "type"]
            for field in legacy_fields:
                assert field in project

    @pytest.mark.contract
    async def test_legacy_search_projects_still_works(self, base_url: str) -> None:
        """Test that legacy search_projects requests work unchanged."""
        request_data = {
            "method": "search_projects",
            "params": {
                "query": "test search",
                "limit": 10
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
        assert "success" in data

        if data["success"] and data.get("data"):
            # Should still return search results in legacy format
            result = data["data"][0]
            legacy_fields = ["file_path", "content_snippet", "similarity_score"]
            for field in legacy_fields:
                assert field in result


# NOTE: All these tests will initially FAIL because:
# 1. The new MCP shelf endpoints don't exist yet (/mcp/v1/list_shelfs, etc.)
# 2. The enhanced list_projects and search_projects endpoints aren't shelf-aware yet
# 3. The admin shelf management endpoints aren't implemented
# 4. The shelf/basket services and data models don't exist yet
# 5. The current shelf context system isn't built
#
# These tests serve as the contract specification that the MCP endpoint implementation must satisfy.