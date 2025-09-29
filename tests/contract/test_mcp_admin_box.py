"""Contract tests for MCP /admin/context/create-box endpoint.

These tests define the expected behavior for the admin box creation endpoint.
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


class TestMcpAdminBoxEndpoint:
    """Contract tests for MCP admin box creation endpoint."""

    @pytest.mark.contract
    def test_endpoint_import_available(self):
        """Test that MCP admin context endpoints can be imported."""
        assert MCP_ADMIN_IMPLEMENTED, "MCP admin context endpoints not implemented yet"

    @pytest.mark.contract
    def test_create_box_endpoint_exists(self):
        """Test that /admin/context/create-box endpoint exists."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        # Create test client
        app = McpAdminServer().app
        client = TestClient(app)

        # Test endpoint exists with POST method
        response = client.post("/admin/context/create-box", json={
            "name": "test-box",
            "type": "drag",
            "shelf": "test-shelf",
            "description": "Test box",
            "run_wizard": False
        })

        # Should not return 404 Not Found for the endpoint itself
        assert response.status_code != 404

    @pytest.mark.contract
    def test_create_box_response_structure(self):
        """Test response structure for successful box creation."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        response = client.post("/admin/context/create-box", json={
            "name": "test-box-new",
            "type": "drag",
            "shelf": "test-shelf",
            "description": "Test box",
            "run_wizard": False
        })

        if response.status_code == 200:
            data = response.json()

            # Required top-level fields
            assert "success" in data
            assert "box" in data
            assert "wizard_applied" in data
            assert "fill_suggestions" in data

            # success should be boolean
            assert isinstance(data["success"], bool)
            assert data["success"] is True

            # box structure
            box = data["box"]
            assert "name" in box
            assert "type" in box
            assert "created_at" in box
            assert "configuration_state" in box

            assert box["name"] == "test-box-new"
            assert box["type"] == "drag"
            assert isinstance(box["created_at"], str)

            # Parse created_at as datetime
            from datetime import datetime
            datetime.fromisoformat(box["created_at"].replace('Z', '+00:00'))

            # configuration_state structure
            config_state = box["configuration_state"]
            assert isinstance(config_state, dict)

            # wizard_applied should be boolean
            assert isinstance(data["wizard_applied"], bool)
            assert data["wizard_applied"] is False

            # fill_suggestions should be array
            assert isinstance(data["fill_suggestions"], list)

    @pytest.mark.contract
    def test_required_fields_validation(self):
        """Test that required fields are enforced."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        # Missing name should fail
        response = client.post("/admin/context/create-box", json={
            "type": "drag",
            "shelf": "test-shelf",
            "run_wizard": False
        })
        assert response.status_code == 422

        # Missing type should fail
        response = client.post("/admin/context/create-box", json={
            "name": "test-box",
            "shelf": "test-shelf",
            "run_wizard": False
        })
        assert response.status_code == 422

        # Missing shelf should fail
        response = client.post("/admin/context/create-box", json={
            "name": "test-box",
            "type": "drag",
            "run_wizard": False
        })
        assert response.status_code == 422

        # description should be optional
        response = client.post("/admin/context/create-box", json={
            "name": "test-box-minimal",
            "type": "rag",
            "shelf": "test-shelf",
            "run_wizard": False
        })
        assert response.status_code != 422

        # run_wizard should be optional (default to False)
        response = client.post("/admin/context/create-box", json={
            "name": "test-box-default-wizard",
            "type": "bag",
            "shelf": "test-shelf"
        })
        assert response.status_code != 422

    @pytest.mark.contract
    def test_box_type_validation(self):
        """Test that box type validation rules are enforced."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        # Valid types should work
        valid_types = ["drag", "rag", "bag"]
        for box_type in valid_types:
            response = client.post("/admin/context/create-box", json={
                "name": f"test-box-{box_type}",
                "type": box_type,
                "shelf": "test-shelf",
                "description": f"Test {box_type} box",
                "run_wizard": False
            })

            # Should not fail validation
            assert response.status_code != 422

        # Invalid type should fail
        response = client.post("/admin/context/create-box", json={
            "name": "test-box-invalid",
            "type": "invalid",
            "shelf": "test-shelf",
            "run_wizard": False
        })

        # Should fail validation
        assert response.status_code == 422

    @pytest.mark.contract
    def test_box_name_validation(self):
        """Test that box name validation rules are enforced."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        # Valid names should work
        valid_names = ["test-box", "my_box", "box123", "test-box-1"]
        for name in valid_names:
            response = client.post("/admin/context/create-box", json={
                "name": name,
                "type": "drag",
                "shelf": "test-shelf",
                "description": f"Test {name}",
                "run_wizard": False
            })

            # Should not fail validation
            assert response.status_code != 422

        # Invalid names should fail
        invalid_names = ["box with spaces", "box/with/slashes", "box@domain", "box.dot"]
        for name in invalid_names:
            response = client.post("/admin/context/create-box", json={
                "name": name,
                "type": "drag",
                "shelf": "test-shelf",
                "description": f"Test {name}",
                "run_wizard": False
            })

            # Should fail validation
            assert response.status_code == 422

    @pytest.mark.contract
    def test_shelf_name_validation(self):
        """Test that shelf name validation rules are enforced."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        # Valid shelf names should work
        valid_shelf_names = ["test-shelf", "my_shelf", "shelf123"]
        for shelf_name in valid_shelf_names:
            response = client.post("/admin/context/create-box", json={
                "name": "test-box-shelf-valid",
                "type": "drag",
                "shelf": shelf_name,
                "run_wizard": False
            })

            # Should not fail validation
            assert response.status_code != 422

        # Invalid shelf names should fail
        invalid_shelf_names = ["shelf with spaces", "shelf/slash"]
        for shelf_name in invalid_shelf_names:
            response = client.post("/admin/context/create-box", json={
                "name": "test-box-shelf-invalid",
                "type": "drag",
                "shelf": shelf_name,
                "run_wizard": False
            })

            # Should fail validation
            assert response.status_code == 422

    @pytest.mark.contract
    def test_duplicate_box_handling(self):
        """Test handling of duplicate box names."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        box_name = "duplicate-test-box"

        # Create first box
        response1 = client.post("/admin/context/create-box", json={
            "name": box_name,
            "type": "drag",
            "shelf": "test-shelf",
            "description": "First box",
            "run_wizard": False
        })

        if response1.status_code == 200:
            # Try to create duplicate
            response2 = client.post("/admin/context/create-box", json={
                "name": box_name,
                "type": "rag",
                "shelf": "test-shelf",
                "description": "Duplicate box",
                "run_wizard": False
            })

            # Should fail with conflict or return existing box
            assert response2.status_code in [409, 422, 400]

    @pytest.mark.contract
    def test_wizard_configuration_structure(self):
        """Test wizard_config structure when run_wizard=true."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        wizard_config = {
            "auto_process": True,
            "file_patterns": ["*.pdf", "*.md"],
            "initial_source": "https://example.com"
        }

        response = client.post("/admin/context/create-box", json={
            "name": "test-box-wizard",
            "type": "drag",
            "shelf": "test-shelf",
            "description": "Test box with wizard",
            "run_wizard": True,
            "wizard_config": wizard_config
        })

        if response.status_code == 200:
            data = response.json()

            # wizard_applied should be True
            assert data["wizard_applied"] is True

            # Configuration should be applied to box
            box = data["box"]
            config_state = box["configuration_state"]

            # Should reflect wizard configuration
            assert "is_configured" in config_state
            if config_state.get("is_configured"):
                assert config_state["is_configured"] is True

    @pytest.mark.contract
    def test_fill_suggestions_structure(self):
        """Test fill_suggestions array structure and type-specific content."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        # Test drag box suggestions
        response = client.post("/admin/context/create-box", json={
            "name": "test-drag-box",
            "type": "drag",
            "shelf": "test-shelf",
            "description": "Test drag box",
            "run_wizard": False
        })

        if response.status_code == 200:
            data = response.json()
            fill_suggestions = data["fill_suggestions"]

            assert isinstance(fill_suggestions, list)
            assert len(fill_suggestions) > 0

            # Each suggestion should have required structure
            for suggestion in fill_suggestions:
                assert "source_type" in suggestion
                assert "description" in suggestion
                assert "example" in suggestion

                assert isinstance(suggestion["source_type"], str)
                assert isinstance(suggestion["description"], str)
                assert isinstance(suggestion["example"], str)

            # Drag box should suggest URL sources
            source_types = [s["source_type"] for s in fill_suggestions]
            assert "url" in source_types

        # Test rag box suggestions
        response = client.post("/admin/context/create-box", json={
            "name": "test-rag-box",
            "type": "rag",
            "shelf": "test-shelf",
            "description": "Test rag box",
            "run_wizard": False
        })

        if response.status_code == 200:
            data = response.json()
            fill_suggestions = data["fill_suggestions"]

            # Rag box should suggest file sources
            source_types = [s["source_type"] for s in fill_suggestions]
            assert "file" in source_types

        # Test bag box suggestions
        response = client.post("/admin/context/create-box", json={
            "name": "test-bag-box",
            "type": "bag",
            "shelf": "test-shelf",
            "description": "Test bag box",
            "run_wizard": False
        })

        if response.status_code == 200:
            data = response.json()
            fill_suggestions = data["fill_suggestions"]

            # Bag box should suggest data sources
            source_types = [s["source_type"] for s in fill_suggestions]
            assert "data" in source_types

    @pytest.mark.contract
    def test_wizard_config_validation(self):
        """Test validation of wizard_config structure."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        # Valid wizard config
        valid_config = {
            "auto_process": True,
            "file_patterns": ["*.pdf", "*.md"],
            "initial_source": "https://example.com"
        }

        response = client.post("/admin/context/create-box", json={
            "name": "test-box-valid-wizard",
            "type": "drag",
            "shelf": "test-shelf",
            "description": "Test box",
            "run_wizard": True,
            "wizard_config": valid_config
        })

        # Should not fail validation
        assert response.status_code != 422

        # Invalid file_patterns type
        invalid_config = {
            "auto_process": True,
            "file_patterns": "not_an_array",
            "initial_source": "https://example.com"
        }

        response = client.post("/admin/context/create-box", json={
            "name": "test-box-invalid-wizard",
            "type": "drag",
            "shelf": "test-shelf",
            "description": "Test box",
            "run_wizard": True,
            "wizard_config": invalid_config
        })

        # Should fail validation
        assert response.status_code == 422

    @pytest.mark.contract
    def test_optional_description_field(self):
        """Test that description field is properly optional."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        # Create box without description
        response = client.post("/admin/context/create-box", json={
            "name": "test-box-no-desc",
            "type": "drag",
            "shelf": "test-shelf",
            "run_wizard": False
        })

        if response.status_code == 200:
            data = response.json()
            box = data["box"]

            # Should handle missing description gracefully
            assert "description" not in box or box["description"] is None

    @pytest.mark.contract
    def test_configuration_state_defaults(self):
        """Test default configuration_state values for new box."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        response = client.post("/admin/context/create-box", json={
            "name": "test-box-defaults",
            "type": "drag",
            "shelf": "test-shelf",
            "description": "Test defaults",
            "run_wizard": False
        })

        if response.status_code == 200:
            data = response.json()
            box = data["box"]
            config_state = box["configuration_state"]

            # New box without wizard should have default state
            if "is_configured" in config_state:
                assert config_state["is_configured"] is False

            if "has_content" in config_state:
                assert config_state["has_content"] is False

    @pytest.mark.contract
    def test_response_content_type(self):
        """Test that response has correct content type."""
        if not MCP_ADMIN_IMPLEMENTED:
            pytest.skip("MCP admin endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        response = client.post("/admin/context/create-box", json={
            "name": "test-box-content-type",
            "type": "drag",
            "shelf": "test-shelf",
            "description": "Test content type",
            "run_wizard": False
        })

        assert response.headers["content-type"] == "application/json"