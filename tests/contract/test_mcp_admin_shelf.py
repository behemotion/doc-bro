"""Contract tests for MCP /admin/context/create-shelf endpoint.

These tests define the expected behavior for the admin shelf creation endpoint.
They MUST FAIL initially until the endpoints are implemented (TDD approach).
"""

import json
from typing import Any, Dict

import pytest
import httpx
from fastapi.testclient import TestClient

# This import will fail until the MCP admin endpoints are implemented
try:
    from src.logic.mcp.core.mcp_admin_server import McpAdminServer
    from src.logic.mcp.endpoints.context import admin_context_router
    MCP_ADMIN_IMPLEMENTED = True
except ImportError:
    MCP_ADMIN_IMPLEMENTED = False
    McpAdminServer = None
    admin_context_router = None


class TestMcpAdminShelfEndpoint:
    """Contract tests for MCP admin shelf creation endpoint."""

    @pytest.mark.contract
    def test_endpoint_import_available(self):
        """Test that MCP admin context endpoints can be imported."""
        assert MCP_ADMIN_IMPLEMENTED, "MCP admin context endpoints not implemented yet"

    @pytest.mark.contract
    def test_create_shelf_endpoint_exists(self):
        """Test that /admin/context/create-shelf endpoint exists."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        # Create test client
        app = McpAdminServer().app
        client = TestClient(app)

        # Test endpoint exists with POST method
        response = client.post("/admin/context/create-shelf", json={
            "name": "test-shelf",
            "description": "Test shelf",
            "run_wizard": False
        })

        # Should not return 404 Not Found for the endpoint itself
        assert response.status_code != 404

    @pytest.mark.contract
    def test_create_shelf_response_structure(self):
        """Test response structure for successful shelf creation."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        response = client.post("/admin/context/create-shelf", json={
            "name": "test-shelf-new",
            "description": "Test shelf",
            "run_wizard": False
        })

        if response.status_code == 200:
            data = response.json()

            # Required top-level fields
            assert "success" in data
            assert "shelf" in data
            assert "wizard_applied" in data
            assert "next_actions" in data

            # success should be boolean
            assert isinstance(data["success"], bool)
            assert data["success"] is True

            # shelf structure
            shelf = data["shelf"]
            assert "name" in shelf
            assert "created_at" in shelf
            assert "configuration_state" in shelf

            assert shelf["name"] == "test-shelf-new"
            assert isinstance(shelf["created_at"], str)

            # Parse created_at as datetime
            from datetime import datetime
            datetime.fromisoformat(shelf["created_at"].replace('Z', '+00:00'))

            # configuration_state structure
            config_state = shelf["configuration_state"]
            assert isinstance(config_state, dict)

            # wizard_applied should be boolean
            assert isinstance(data["wizard_applied"], bool)
            assert data["wizard_applied"] is False

            # next_actions should be array
            assert isinstance(data["next_actions"], list)

    @pytest.mark.contract
    def test_required_fields_validation(self):
        """Test that required fields are enforced."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        # Missing name should fail
        response = client.post("/admin/context/create-shelf", json={
            "description": "Test shelf",
            "run_wizard": False
        })
        assert response.status_code == 422

        # Empty name should fail
        response = client.post("/admin/context/create-shelf", json={
            "name": "",
            "description": "Test shelf",
            "run_wizard": False
        })
        assert response.status_code == 422

        # description should be optional
        response = client.post("/admin/context/create-shelf", json={
            "name": "test-shelf-minimal",
            "run_wizard": False
        })
        assert response.status_code != 422

        # run_wizard should be optional (default to False)
        response = client.post("/admin/context/create-shelf", json={
            "name": "test-shelf-default-wizard"
        })
        assert response.status_code != 422

    @pytest.mark.contract
    def test_shelf_name_validation(self):
        """Test that shelf name validation rules are enforced."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        # Valid names should work
        valid_names = ["test-shelf", "my_shelf", "shelf123", "test-shelf-1"]
        for name in valid_names:
            response = client.post("/admin/context/create-shelf", json={
                "name": name,
                "description": f"Test {name}",
                "run_wizard": False
            })

            # Should not fail validation
            assert response.status_code != 422

        # Invalid names should fail
        invalid_names = ["shelf with spaces", "shelf/with/slashes", "shelf@domain", "shelf.dot"]
        for name in invalid_names:
            response = client.post("/admin/context/create-shelf", json={
                "name": name,
                "description": f"Test {name}",
                "run_wizard": False
            })

            # Should fail validation
            assert response.status_code == 422

    @pytest.mark.contract
    def test_duplicate_shelf_handling(self):
        """Test handling of duplicate shelf names."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        shelf_name = "duplicate-test-shelf"

        # Create first shelf
        response1 = client.post("/admin/context/create-shelf", json={
            "name": shelf_name,
            "description": "First shelf",
            "run_wizard": False
        })

        if response1.status_code == 200:
            # Try to create duplicate
            response2 = client.post("/admin/context/create-shelf", json={
                "name": shelf_name,
                "description": "Duplicate shelf",
                "run_wizard": False
            })

            # Should fail with conflict or return existing shelf
            assert response2.status_code in [409, 422, 400]

    @pytest.mark.contract
    def test_wizard_configuration_structure(self):
        """Test wizard_config structure when run_wizard=true."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        wizard_config = {
            "auto_fill": True,
            "default_box_type": "drag",
            "tags": ["docs", "main"]
        }

        response = client.post("/admin/context/create-shelf", json={
            "name": "test-shelf-wizard",
            "description": "Test shelf with wizard",
            "run_wizard": True,
            "wizard_config": wizard_config
        })

        if response.status_code == 200:
            data = response.json()

            # wizard_applied should be True
            assert data["wizard_applied"] is True

            # Configuration should be applied to shelf
            shelf = data["shelf"]
            config_state = shelf["configuration_state"]

            # Should reflect wizard configuration
            assert "is_configured" in config_state
            if config_state.get("is_configured"):
                assert config_state["is_configured"] is True

    @pytest.mark.contract
    def test_wizard_config_validation(self):
        """Test validation of wizard_config structure."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        # Valid wizard config
        valid_config = {
            "auto_fill": True,
            "default_box_type": "drag",
            "tags": ["docs", "main"]
        }

        response = client.post("/admin/context/create-shelf", json={
            "name": "test-shelf-valid-wizard",
            "description": "Test shelf",
            "run_wizard": True,
            "wizard_config": valid_config
        })

        # Should not fail validation
        assert response.status_code != 422

        # Invalid default_box_type
        invalid_config = {
            "auto_fill": True,
            "default_box_type": "invalid",
            "tags": ["docs"]
        }

        response = client.post("/admin/context/create-shelf", json={
            "name": "test-shelf-invalid-wizard",
            "description": "Test shelf",
            "run_wizard": True,
            "wizard_config": invalid_config
        })

        # Should fail validation
        assert response.status_code == 422

    @pytest.mark.contract
    def test_next_actions_structure(self):
        """Test next_actions array structure and content."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        response = client.post("/admin/context/create-shelf", json={
            "name": "test-shelf-actions",
            "description": "Test shelf",
            "run_wizard": False
        })

        if response.status_code == 200:
            data = response.json()
            next_actions = data["next_actions"]

            assert isinstance(next_actions, list)

            # Each action should have required structure
            for action in next_actions:
                assert "action" in action
                assert "description" in action
                assert "command" in action

                assert isinstance(action["action"], str)
                assert isinstance(action["description"], str)
                assert isinstance(action["command"], str)

                # Action should be relevant to shelf creation
                assert action["action"] in ["create-box", "configure", "fill", "view"]

    @pytest.mark.contract
    def test_optional_description_field(self):
        """Test that description field is properly optional."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        # Create shelf without description
        response = client.post("/admin/context/create-shelf", json={
            "name": "test-shelf-no-desc",
            "run_wizard": False
        })

        if response.status_code == 200:
            data = response.json()
            shelf = data["shelf"]

            # Should handle missing description gracefully
            assert "description" not in shelf or shelf["description"] is None

    @pytest.mark.contract
    def test_configuration_state_defaults(self):
        """Test default configuration_state values for new shelf."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        response = client.post("/admin/context/create-shelf", json={
            "name": "test-shelf-defaults",
            "description": "Test defaults",
            "run_wizard": False
        })

        if response.status_code == 200:
            data = response.json()
            shelf = data["shelf"]
            config_state = shelf["configuration_state"]

            # New shelf without wizard should have default state
            if "is_configured" in config_state:
                assert config_state["is_configured"] is False

            if "has_content" in config_state:
                assert config_state["has_content"] is False

            if "needs_migration" in config_state:
                assert config_state["needs_migration"] is False

    @pytest.mark.contract
    def test_response_content_type(self):
        """Test that response has correct content type."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        response = client.post("/admin/context/create-shelf", json={
            "name": "test-shelf-content-type",
            "description": "Test content type",
            "run_wizard": False
        })

        assert response.headers["content-type"] == "application/json"

    @pytest.mark.contract
    def test_error_response_structure(self):
        """Test error response structure for validation failures."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        # Trigger validation error
        response = client.post("/admin/context/create-shelf", json={
            "name": "",  # Invalid empty name
            "description": "Test error",
            "run_wizard": False
        })

        if response.status_code == 422:
            data = response.json()

            # Should have error details
            assert "detail" in data or "message" in data or "errors" in data