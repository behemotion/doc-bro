"""Contract tests for MCP /admin/wizards/start endpoint.

These tests define the expected behavior for the wizard management endpoints.
They MUST FAIL initially until the endpoints are implemented (TDD approach).
"""

import json
import uuid
from typing import Any, Dict

import pytest
import httpx
from fastapi.testclient import TestClient

# This import will fail until the MCP wizard endpoints are implemented
try:
    from src.logic.mcp.core.mcp_admin_server import McpAdminServer
    from src.logic.mcp.endpoints.wizard import wizard_router
    MCP_WIZARD_IMPLEMENTED = True
except ImportError:
    MCP_WIZARD_IMPLEMENTED = False
    McpAdminServer = None
    wizard_router = None


class TestMcpWizardStartEndpoint:
    """Contract tests for MCP wizard start endpoint."""

    @pytest.mark.contract
    def test_endpoint_import_available(self):
        """Test that MCP wizard endpoints can be imported."""
        assert MCP_WIZARD_IMPLEMENTED, "MCP wizard endpoints not implemented yet"

    @pytest.mark.contract
    def test_wizard_start_endpoint_exists(self):
        """Test that /admin/wizards/start endpoint exists."""
        if not MCP_WIZARD_IMPLEMENTED:
            pytest.skip("MCP wizard endpoints not implemented yet")

        # Create test client
        app = McpAdminServer().app
        client = TestClient(app)

        # Test endpoint exists with POST method
        response = client.post("/admin/wizards/start", json={
            "wizard_type": "shelf",
            "target_entity": "test-shelf",
            "auto_advance": False
        })

        # Should not return 404 Not Found for the endpoint itself
        assert response.status_code != 404

    @pytest.mark.contract
    def test_wizard_start_response_structure(self):
        """Test response structure for successful wizard start."""
        if not MCP_WIZARD_IMPLEMENTED:
            pytest.skip("MCP wizard endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        response = client.post("/admin/wizards/start", json={
            "wizard_type": "shelf",
            "target_entity": "test-shelf",
            "auto_advance": False
        })

        if response.status_code == 200:
            data = response.json()

            # Required top-level fields
            assert "wizard_id" in data
            assert "session_info" in data
            assert "current_step" in data

            # wizard_id should be UUID format
            wizard_id = data["wizard_id"]
            assert isinstance(wizard_id, str)
            # Should be parseable as UUID
            uuid.UUID(wizard_id)

            # session_info structure
            session_info = data["session_info"]
            assert "type" in session_info
            assert "target" in session_info
            assert "total_steps" in session_info
            assert "estimated_time" in session_info

            assert session_info["type"] == "shelf"
            assert session_info["target"] == "test-shelf"
            assert isinstance(session_info["total_steps"], int)
            assert session_info["total_steps"] > 0
            assert isinstance(session_info["estimated_time"], str)

            # current_step structure
            current_step = data["current_step"]
            assert "number" in current_step
            assert "title" in current_step
            assert "prompt" in current_step
            assert "input_type" in current_step
            assert "is_optional" in current_step

            assert isinstance(current_step["number"], int)
            assert current_step["number"] >= 1
            assert isinstance(current_step["title"], str)
            assert isinstance(current_step["prompt"], str)
            assert current_step["input_type"] in ["choice", "text", "boolean", "file_path", "url"]
            assert isinstance(current_step["is_optional"], bool)

    @pytest.mark.contract
    def test_wizard_type_validation(self):
        """Test that only valid wizard types are accepted."""
        if not MCP_WIZARD_IMPLEMENTED:
            pytest.skip("MCP wizard endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        # Valid wizard types should work
        valid_types = ["shelf", "box", "mcp"]
        for wizard_type in valid_types:
            response = client.post("/admin/wizards/start", json={
                "wizard_type": wizard_type,
                "target_entity": "test-entity",
                "auto_advance": False
            })

            # Should not fail validation
            assert response.status_code != 422

        # Invalid wizard type should fail
        response = client.post("/admin/wizards/start", json={
            "wizard_type": "invalid",
            "target_entity": "test-entity",
            "auto_advance": False
        })

        assert response.status_code == 422

    @pytest.mark.contract
    def test_required_fields_validation(self):
        """Test that required fields are enforced."""
        if not MCP_WIZARD_IMPLEMENTED:
            pytest.skip("MCP wizard endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        # Missing wizard_type
        response = client.post("/admin/wizards/start", json={
            "target_entity": "test-entity",
            "auto_advance": False
        })
        assert response.status_code == 422

        # Missing target_entity
        response = client.post("/admin/wizards/start", json={
            "wizard_type": "shelf",
            "auto_advance": False
        })
        assert response.status_code == 422

        # auto_advance should be optional (default to False)
        response = client.post("/admin/wizards/start", json={
            "wizard_type": "shelf",
            "target_entity": "test-entity"
        })
        # Should not fail due to missing auto_advance
        assert response.status_code != 422

    @pytest.mark.contract
    def test_shelf_wizard_specific_fields(self):
        """Test shelf wizard specific response fields."""
        if not MCP_WIZARD_IMPLEMENTED:
            pytest.skip("MCP wizard endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        response = client.post("/admin/wizards/start", json={
            "wizard_type": "shelf",
            "target_entity": "test-shelf",
            "auto_advance": False
        })

        if response.status_code == 200:
            data = response.json()
            current_step = data["current_step"]

            # First step should be about description (typical for shelf wizard)
            assert "description" in current_step["prompt"].lower() or "name" in current_step["prompt"].lower()

    @pytest.mark.contract
    def test_box_wizard_specific_fields(self):
        """Test box wizard specific response fields."""
        if not MCP_WIZARD_IMPLEMENTED:
            pytest.skip("MCP wizard endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        response = client.post("/admin/wizards/start", json={
            "wizard_type": "box",
            "target_entity": "test-box",
            "auto_advance": False
        })

        if response.status_code == 200:
            data = response.json()
            current_step = data["current_step"]

            # Should have choices for box type or ask about type
            if current_step["input_type"] == "choice":
                assert "choices" in current_step
                assert isinstance(current_step["choices"], list)
                # Might include box types
                choices_text = " ".join(current_step["choices"]).lower()
                assert any(box_type in choices_text for box_type in ["drag", "rag", "bag"])

    @pytest.mark.contract
    def test_mcp_wizard_specific_fields(self):
        """Test MCP wizard specific response fields."""
        if not MCP_WIZARD_IMPLEMENTED:
            pytest.skip("MCP wizard endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        response = client.post("/admin/wizards/start", json={
            "wizard_type": "mcp",
            "target_entity": "mcp-server",
            "auto_advance": False
        })

        if response.status_code == 200:
            data = response.json()
            current_step = data["current_step"]

            # Should ask about server configuration
            prompt_lower = current_step["prompt"].lower()
            assert any(keyword in prompt_lower for keyword in ["server", "port", "enable", "read-only", "admin"])

    @pytest.mark.contract
    def test_choice_input_type_structure(self):
        """Test structure when input_type is 'choice'."""
        if not MCP_WIZARD_IMPLEMENTED:
            pytest.skip("MCP wizard endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        response = client.post("/admin/wizards/start", json={
            "wizard_type": "box",
            "target_entity": "test-box",
            "auto_advance": False
        })

        if response.status_code == 200:
            data = response.json()
            current_step = data["current_step"]

            if current_step["input_type"] == "choice":
                # Must have choices array
                assert "choices" in current_step
                assert isinstance(current_step["choices"], list)
                assert len(current_step["choices"]) > 0

                # Each choice should be a string
                for choice in current_step["choices"]:
                    assert isinstance(choice, str)

    @pytest.mark.contract
    def test_validation_rules_field(self):
        """Test validation_rules field in current_step."""
        if not MCP_WIZARD_IMPLEMENTED:
            pytest.skip("MCP wizard endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        response = client.post("/admin/wizards/start", json={
            "wizard_type": "shelf",
            "target_entity": "test-shelf",
            "auto_advance": False
        })

        if response.status_code == 200:
            data = response.json()
            current_step = data["current_step"]

            # validation_rules should be present
            if "validation_rules" in current_step:
                assert isinstance(current_step["validation_rules"], list)

                # Each rule should be a string
                for rule in current_step["validation_rules"]:
                    assert isinstance(rule, str)

    @pytest.mark.contract
    def test_auto_advance_functionality(self):
        """Test auto_advance parameter functionality."""
        if not MCP_WIZARD_IMPLEMENTED:
            pytest.skip("MCP wizard endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        # Test with auto_advance=true
        response = client.post("/admin/wizards/start", json={
            "wizard_type": "shelf",
            "target_entity": "test-shelf",
            "auto_advance": True
        })

        if response.status_code == 200:
            data = response.json()

            # With auto_advance, might skip optional steps
            current_step = data["current_step"]
            if current_step["is_optional"]:
                # Should have moved past optional steps
                assert current_step["number"] > 1 or not current_step["is_optional"]

    @pytest.mark.contract
    def test_target_entity_validation(self):
        """Test target_entity validation."""
        if not MCP_WIZARD_IMPLEMENTED:
            pytest.skip("MCP wizard endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        # Valid entity names should work
        valid_names = ["test-shelf", "my_shelf", "shelf123"]
        for name in valid_names:
            response = client.post("/admin/wizards/start", json={
                "wizard_type": "shelf",
                "target_entity": name,
                "auto_advance": False
            })

            # Should not fail validation
            assert response.status_code != 422

        # Invalid entity names should fail
        invalid_names = ["", "shelf with spaces", "shelf/slash"]
        for name in invalid_names:
            response = client.post("/admin/wizards/start", json={
                "wizard_type": "shelf",
                "target_entity": name,
                "auto_advance": False
            })

            # Should fail validation
            assert response.status_code == 422

    @pytest.mark.contract
    def test_response_content_type(self):
        """Test that response has correct content type."""
        if not MCP_WIZARD_IMPLEMENTED:
            pytest.skip("MCP wizard endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        response = client.post("/admin/wizards/start", json={
            "wizard_type": "shelf",
            "target_entity": "test-shelf",
            "auto_advance": False
        })

        assert response.headers["content-type"] == "application/json"

    @pytest.mark.contract
    def test_concurrent_wizard_sessions(self):
        """Test that multiple wizard sessions can be started concurrently."""
        if not MCP_WIZARD_IMPLEMENTED:
            pytest.skip("MCP wizard endpoints not implemented yet")

        app = McpAdminServer().app
        client = TestClient(app)

        # Start multiple wizard sessions
        sessions = []
        for i in range(3):
            response = client.post("/admin/wizards/start", json={
                "wizard_type": "shelf",
                "target_entity": f"test-shelf-{i}",
                "auto_advance": False
            })

            if response.status_code == 200:
                sessions.append(response.json())

        # Each session should have unique wizard_id
        wizard_ids = [session["wizard_id"] for session in sessions]
        assert len(set(wizard_ids)) == len(wizard_ids)  # All unique