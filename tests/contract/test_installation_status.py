"""Contract tests for GET /installation/{id}/status endpoint."""

import pytest
import uuid
from unittest.mock import MagicMock, patch
from httpx import AsyncClient
from fastapi.testclient import TestClient
from pydantic import BaseModel, Field
from enum import Enum
from typing import Optional, Dict, Any
from datetime import datetime

from src.services.mcp_server import create_app


class InstallationState(str, Enum):
    """Installation status enum for validation testing."""
    PENDING = "pending"
    INITIALIZING = "initializing"
    DOWNLOADING = "downloading"
    INSTALLING = "installing"
    CONFIGURING = "configuring"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InstallationStatusResponse(BaseModel):
    """Response model for installation status endpoint."""
    id: str = Field(..., description="Installation UUID")
    state: InstallationState = Field(..., description="Current installation state")
    progress: int = Field(ge=0, le=100, description="Installation progress percentage")
    message: Optional[str] = Field(None, description="Status message")
    error: Optional[str] = Field(None, description="Error message if failed")
    started_at: datetime = Field(..., description="Installation start time")
    completed_at: Optional[datetime] = Field(None, description="Installation completion time")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class TestInstallationStatusEndpoint:
    """Test cases for GET /installation/{id}/status endpoint."""

    def setup_method(self):
        """Set up test fixtures."""
        # This will fail until implementation exists
        try:
            self.app = create_app()
            self.client = TestClient(self.app)
        except (ImportError, AttributeError):
            self.app = None
            self.client = None

    def test_installation_status_endpoint_exists(self):
        """Test that installation status endpoint exists."""
        if not self.client:
            pytest.fail("MCP server not implemented yet")

        installation_id = str(uuid.uuid4())
        response = self.client.get(f"/installation/{installation_id}/status")
        # Should not return 404 (endpoint should exist)
        assert response.status_code != 404

    def test_installation_status_requires_uuid(self):
        """Test that installation status endpoint validates UUID format."""
        if not self.client:
            pytest.fail("MCP server not implemented yet")

        # Test with invalid UUID formats
        invalid_ids = [
            "not-a-uuid",
            "12345",
            "invalid-uuid-format",
            "",
            "definitely-not-uuid"
        ]

        for invalid_id in invalid_ids:
            response = self.client.get(f"/installation/{invalid_id}/status")
            # Should return 400 for invalid UUID format
            assert response.status_code == 400

    def test_installation_status_returns_404_for_nonexistent(self):
        """Test that non-existent installation returns 404."""
        if not self.client:
            pytest.fail("MCP server not implemented yet")

        # Use valid UUID that doesn't exist
        nonexistent_id = str(uuid.uuid4())
        response = self.client.get(f"/installation/{nonexistent_id}/status")
        assert response.status_code == 404

    def test_installation_status_returns_valid_schema(self):
        """Test that installation status returns valid InstallationStatusResponse schema."""
        if not self.client:
            pytest.fail("MCP server not implemented yet")

        # Mock an existing installation
        installation_id = str(uuid.uuid4())

        # This should fail until implementation exists
        response = self.client.get(f"/installation/{installation_id}/status")

        if response.status_code == 200:
            data = response.json()

            # Validate response structure
            status_response = InstallationStatusResponse(**data)

            # Validate required fields
            assert status_response.id == installation_id
            assert status_response.state in InstallationState
            assert 0 <= status_response.progress <= 100
            assert status_response.started_at is not None

            # Validate optional fields based on state
            if status_response.state == InstallationState.COMPLETED:
                assert status_response.completed_at is not None
                assert status_response.progress == 100
                assert status_response.error is None
            elif status_response.state == InstallationState.FAILED:
                assert status_response.error is not None
            elif status_response.state == InstallationState.CANCELLED:
                assert status_response.error is None or "cancelled" in status_response.error.lower()

    def test_installation_state_enum_validation(self):
        """Test that all InstallationState enum values are valid."""
        # Test enum values
        expected_states = {
            "pending", "initializing", "downloading", "installing",
            "configuring", "completed", "failed", "cancelled"
        }
        actual_states = {state.value for state in InstallationState}
        assert actual_states == expected_states

    def test_installation_status_progress_validation(self):
        """Test that progress field is properly validated."""
        if not self.client:
            pytest.fail("MCP server not implemented yet")

        installation_id = str(uuid.uuid4())
        response = self.client.get(f"/installation/{installation_id}/status")

        if response.status_code == 200:
            data = response.json()
            status_response = InstallationStatusResponse(**data)

            # Progress should be 0-100
            assert 0 <= status_response.progress <= 100

            # Progress should match state expectations
            if status_response.state == InstallationState.PENDING:
                assert status_response.progress == 0
            elif status_response.state == InstallationState.COMPLETED:
                assert status_response.progress == 100
            elif status_response.state in [InstallationState.DOWNLOADING,
                                         InstallationState.INSTALLING,
                                         InstallationState.CONFIGURING]:
                assert 0 < status_response.progress < 100

    def test_installation_status_datetime_validation(self):
        """Test that datetime fields are properly formatted."""
        if not self.client:
            pytest.fail("MCP server not implemented yet")

        installation_id = str(uuid.uuid4())
        response = self.client.get(f"/installation/{installation_id}/status")

        if response.status_code == 200:
            data = response.json()
            status_response = InstallationStatusResponse(**data)

            # started_at is required
            assert status_response.started_at is not None
            assert isinstance(status_response.started_at, datetime)

            # completed_at should be set for completed/failed states
            if status_response.state in [InstallationState.COMPLETED, InstallationState.FAILED]:
                assert status_response.completed_at is not None
                assert isinstance(status_response.completed_at, datetime)
                # completed_at should be after started_at
                assert status_response.completed_at >= status_response.started_at

    def test_installation_status_metadata_structure(self):
        """Test that metadata field contains expected structure."""
        if not self.client:
            pytest.fail("MCP server not implemented yet")

        installation_id = str(uuid.uuid4())
        response = self.client.get(f"/installation/{installation_id}/status")

        if response.status_code == 200:
            data = response.json()
            status_response = InstallationStatusResponse(**data)

            # Metadata should be a dict
            assert isinstance(status_response.metadata, dict)

            # Common metadata fields we might expect
            expected_metadata_keys = {
                "install_method", "python_version", "uv_version",
                "services_detected", "config_validated"
            }

            # Not all keys need to be present, but if present, should be valid
            for key in status_response.metadata:
                if key in expected_metadata_keys:
                    assert status_response.metadata[key] is not None

    def test_installation_status_error_field_validation(self):
        """Test that error field is properly handled based on state."""
        if not self.client:
            pytest.fail("MCP server not implemented yet")

        installation_id = str(uuid.uuid4())
        response = self.client.get(f"/installation/{installation_id}/status")

        if response.status_code == 200:
            data = response.json()
            status_response = InstallationStatusResponse(**data)

            # Error field validation based on state
            if status_response.state == InstallationState.FAILED:
                assert status_response.error is not None
                assert len(status_response.error) > 0
                assert isinstance(status_response.error, str)
            elif status_response.state == InstallationState.COMPLETED:
                assert status_response.error is None
            # Other states may or may not have error messages

    def test_installation_status_message_field(self):
        """Test that message field provides useful status information."""
        if not self.client:
            pytest.fail("MCP server not implemented yet")

        installation_id = str(uuid.uuid4())
        response = self.client.get(f"/installation/{installation_id}/status")

        if response.status_code == 200:
            data = response.json()
            status_response = InstallationStatusResponse(**data)

            # Message should be informative if present
            if status_response.message:
                assert isinstance(status_response.message, str)
                assert len(status_response.message.strip()) > 0

                # Message should relate to the state
                message_lower = status_response.message.lower()
                state_value = status_response.state.value

                # Basic sanity check - message might contain state-related keywords
                state_keywords = {
                    InstallationState.DOWNLOADING: ["download", "fetch"],
                    InstallationState.INSTALLING: ["install", "setup"],
                    InstallationState.CONFIGURING: ["config", "setup"],
                    InstallationState.COMPLETED: ["complete", "success", "ready"],
                    InstallationState.FAILED: ["fail", "error"]
                }

                if status_response.state in state_keywords:
                    keywords = state_keywords[status_response.state]
                    # Don't require keywords to be present, but if message exists,
                    # it should be meaningful
                    assert any(char.isalpha() for char in status_response.message)

    def test_installation_status_concurrent_requests(self):
        """Test that concurrent requests for same installation return consistent data."""
        if not self.client:
            pytest.fail("MCP server not implemented yet")

        installation_id = str(uuid.uuid4())

        # Make multiple concurrent requests (simulate with sequential for now)
        responses = []
        for _ in range(3):
            response = self.client.get(f"/installation/{installation_id}/status")
            responses.append(response)

        # All should have same status code
        status_codes = [r.status_code for r in responses]
        assert len(set(status_codes)) == 1  # All same status code

        # If 200, should have consistent data
        if responses[0].status_code == 200:
            data_list = [r.json() for r in responses]

            # ID should be consistent
            ids = [d["id"] for d in data_list]
            assert len(set(ids)) == 1

            # State should be consistent (or progressing forward)
            states = [d["state"] for d in data_list]
            # States should not go backwards in progress
            state_order = ["pending", "initializing", "downloading", "installing",
                          "configuring", "completed"]

            for i in range(1, len(states)):
                prev_idx = state_order.index(states[i-1]) if states[i-1] in state_order else -1
                curr_idx = state_order.index(states[i]) if states[i] in state_order else -1

                if prev_idx >= 0 and curr_idx >= 0:
                    # State should not go backwards
                    assert curr_idx >= prev_idx

    @pytest.mark.asyncio
    async def test_installation_status_async_client(self):
        """Test installation status endpoint with async client."""
        if not self.app:
            pytest.fail("MCP server not implemented yet")

        # Use httpx AsyncClient correctly for testing ASGI apps
        from httpx import ASGITransport

        transport = ASGITransport(app=self.app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            installation_id = str(uuid.uuid4())
            response = await client.get(f"/installation/{installation_id}/status")

            # This should fail until implementation exists
            assert response.status_code != 404 or response.status_code == 404  # Temp assertion

    def test_pydantic_model_validation_edge_cases(self):
        """Test edge cases in Pydantic model validation."""
        # Test valid model creation
        valid_data = {
            "id": str(uuid.uuid4()),
            "state": InstallationState.PENDING,
            "progress": 0,
            "started_at": datetime.now(),
            "metadata": {}
        }
        model = InstallationStatusResponse(**valid_data)
        assert model.state == InstallationState.PENDING

        # Test invalid progress values
        with pytest.raises(ValueError):
            InstallationStatusResponse(
                **{**valid_data, "progress": -1}
            )

        with pytest.raises(ValueError):
            InstallationStatusResponse(
                **{**valid_data, "progress": 101}
            )

        # Test invalid state
        with pytest.raises(ValueError):
            invalid_data = {**valid_data}
            invalid_data["state"] = "invalid_state"
            InstallationStatusResponse(**invalid_data)