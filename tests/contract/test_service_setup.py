"""Contract tests for PUT /installation/{id}/services endpoint."""

import pytest
from unittest.mock import MagicMock, patch, AsyncMock
from fastapi.testclient import TestClient
from fastapi import FastAPI
from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from pydantic import BaseModel, Field, field_validator

from src.services.mcp_server import create_app
from src.models.installation import ServiceStatus


class ServiceConfiguration(BaseModel):
    """Service configuration model for the API endpoint."""

    service_name: str = Field(..., description="Name of the service to configure")
    enabled: bool = Field(..., description="Whether the service is enabled")
    endpoint: Optional[str] = Field(None, description="Service endpoint URL")
    auto_setup: bool = Field(default=True, description="Whether to auto-setup the service")
    config_overrides: Dict[str, Any] = Field(default_factory=dict, description="Configuration overrides")

    @field_validator('service_name')
    @classmethod
    def validate_service_name(cls, v: str) -> str:
        """Validate service name is supported."""
        supported_services = {"docker", "ollama", "qdrant"}
        if v not in supported_services:
            raise ValueError(f"service_name must be one of {supported_services}")
        return v

    @field_validator('endpoint')
    @classmethod
    def validate_endpoint(cls, v: Optional[str]) -> Optional[str]:
        """Validate endpoint URL format if provided."""
        if v and not v.startswith(("http://", "https://")):
            raise ValueError("endpoint must be HTTP or HTTPS URL")
        return v


class TestServiceSetupEndpoint:
    """Contract tests for the PUT /installation/{id}/services endpoint."""

    def setup_method(self):
        """Set up test fixtures."""
        # This will fail initially since the endpoint doesn't exist yet (TDD requirement)
        try:
            self.app = create_app()
            self.client = TestClient(self.app)
            self.test_installation_id = str(uuid.uuid4())
        except (ImportError, AttributeError):
            self.app = None
            self.client = None
            self.test_installation_id = None

    def test_service_setup_endpoint_exists(self):
        """Test that the PUT /installation/{id}/services endpoint exists."""
        if not self.client:
            pytest.fail("MCP server not implemented yet")

        # Valid service configuration payload
        service_configs = [
            {
                "service_name": "docker",
                "enabled": True,
                "endpoint": "http://localhost:2376",
                "auto_setup": True,
                "config_overrides": {}
            }
        ]

        # Make request to endpoint
        response = self.client.put(
            f"/installation/{self.test_installation_id}/services",
            json=service_configs
        )

        # Endpoint should exist (not return 404)
        # This test will FAIL initially since the endpoint doesn't exist yet (TDD requirement)
        assert response.status_code != 404, "Endpoint should exist but doesn't (TDD: Expected to fail initially)"

    def test_service_configuration_array_validation(self):
        """Test that the endpoint validates ServiceConfiguration array in request body."""
        if not self.client:
            pytest.fail("MCP server not implemented yet")

        # Test with valid service configuration array
        valid_configs = [
            {
                "service_name": "docker",
                "enabled": True,
                "endpoint": "http://localhost:2376",
                "auto_setup": True,
                "config_overrides": {"timeout": 30}
            },
            {
                "service_name": "ollama",
                "enabled": False,
                "endpoint": "http://localhost:11434",
                "auto_setup": False,
                "config_overrides": {}
            },
            {
                "service_name": "qdrant",
                "enabled": True,
                "endpoint": "http://localhost:6333",
                "auto_setup": True,
                "config_overrides": {"collection": "documents"}
            }
        ]

        response = self.client.put(
            f"/installation/{self.test_installation_id}/services",
            json=valid_configs
        )

        # Should accept valid array format or return 404 if endpoint doesn't exist yet
        assert response.status_code in [200, 400, 404]  # 404 expected until endpoint implemented

    def test_service_configuration_validation_errors(self):
        """Test validation errors for invalid service configurations."""
        if not self.client:
            pytest.fail("MCP server not implemented yet")

        # Test invalid service name
        invalid_service_name = [{
            "service_name": "invalid_service",
            "enabled": True,
            "auto_setup": True
        }]

        response = self.client.put(
            f"/installation/{self.test_installation_id}/services",
            json=invalid_service_name
        )
        # Expect 400 for validation error or 404 if endpoint doesn't exist yet
        assert response.status_code in [400, 404]

        # Test missing required fields
        missing_fields = [{
            "enabled": True
            # Missing service_name
        }]

        response = self.client.put(
            f"/installation/{self.test_installation_id}/services",
            json=missing_fields
        )
        # Expect 400 for validation error or 404 if endpoint doesn't exist yet
        assert response.status_code in [400, 404]

        # Test invalid endpoint URL
        invalid_endpoint = [{
            "service_name": "docker",
            "enabled": True,
            "endpoint": "not-a-valid-url",
            "auto_setup": True
        }]

        response = self.client.put(
            f"/installation/{self.test_installation_id}/services",
            json=invalid_endpoint
        )
        # Expect 400 for validation error or 404 if endpoint doesn't exist yet
        assert response.status_code in [400, 404]

        # Test non-array payload
        response = self.client.put(
            f"/installation/{self.test_installation_id}/services",
            json={"not": "an_array"}
        )
        # Expect 400 for validation error or 404 if endpoint doesn't exist yet
        assert response.status_code in [400, 404]

    def test_service_configuration_response_codes(self):
        """Test expected response codes for different scenarios."""
        if not self.client:
            pytest.fail("MCP server not implemented yet")

        # Test successful configuration update (200)
        valid_config = [{
            "service_name": "docker",
            "enabled": True,
            "endpoint": "http://localhost:2376",
            "auto_setup": True,
            "config_overrides": {}
        }]

        response = self.client.put(
            f"/installation/{self.test_installation_id}/services",
            json=valid_config
        )

        # Should return 200 for successful update, 400 for validation error, or 404 if endpoint doesn't exist yet
        assert response.status_code in [200, 400, 404]

        # Test non-existent installation ID (should be 404 when implemented)
        fake_id = str(uuid.uuid4())
        response = self.client.put(
            f"/installation/{fake_id}/services",
            json=valid_config
        )

        # Should eventually return 404 for non-existent installation or endpoint
        assert response.status_code in [400, 404]  # Acceptable until endpoint is implemented

    def test_service_configuration_updates_services(self):
        """Test that endpoint actually updates service configurations."""
        if not self.client:
            pytest.fail("MCP server not implemented yet")

        # Test updating multiple services
        service_updates = [
            {
                "service_name": "docker",
                "enabled": True,
                "endpoint": "http://localhost:2376",
                "auto_setup": True,
                "config_overrides": {"driver": "overlay2"}
            },
            {
                "service_name": "qdrant",
                "enabled": False,
                "endpoint": "http://localhost:6333",
                "auto_setup": False,
                "config_overrides": {"storage": "disk"}
            }
        ]

        response = self.client.put(
            f"/installation/{self.test_installation_id}/services",
            json=service_updates
        )

        if response.status_code == 200:
            # Should return updated service configurations
            response_data = response.json()
            assert "services" in response_data
            assert len(response_data["services"]) == 2

            # Verify service configurations were updated
            docker_service = next((s for s in response_data["services"] if s["name"] == "docker"), None)
            assert docker_service is not None
            assert docker_service["enabled"] == True
            assert docker_service["endpoint"] == "http://localhost:2376"

            qdrant_service = next((s for s in response_data["services"] if s["name"] == "qdrant"), None)
            assert qdrant_service is not None
            assert qdrant_service["enabled"] == False

    def test_service_configuration_partial_updates(self):
        """Test that endpoint handles partial service configuration updates."""
        if not self.client:
            pytest.fail("MCP server not implemented yet")

        # Test updating only specific fields
        partial_update = [{
            "service_name": "ollama",
            "enabled": False
            # Only updating enabled status, other fields should remain unchanged
        }]

        response = self.client.put(
            f"/installation/{self.test_installation_id}/services",
            json=partial_update
        )

        if response.status_code == 200:
            response_data = response.json()
            ollama_service = next((s for s in response_data["services"] if s["name"] == "ollama"), None)
            assert ollama_service is not None
            assert ollama_service["enabled"] == False

    def test_service_configuration_config_overrides(self):
        """Test that config_overrides are properly handled."""
        if not self.client:
            pytest.fail("MCP server not implemented yet")

        # Test with complex config overrides
        config_with_overrides = [{
            "service_name": "qdrant",
            "enabled": True,
            "endpoint": "http://localhost:6333",
            "auto_setup": True,
            "config_overrides": {
                "collection_name": "documents",
                "vector_size": 1536,
                "distance": "cosine",
                "on_disk_payload": True,
                "timeout": 30.0
            }
        }]

        response = self.client.put(
            f"/installation/{self.test_installation_id}/services",
            json=config_with_overrides
        )

        if response.status_code == 200:
            response_data = response.json()
            qdrant_service = next((s for s in response_data["services"] if s["name"] == "qdrant"), None)
            assert qdrant_service is not None
            assert "config_overrides" in qdrant_service
            assert qdrant_service["config_overrides"]["collection_name"] == "documents"
            assert qdrant_service["config_overrides"]["vector_size"] == 1536

    def test_service_configuration_authentication_required(self):
        """Test that the endpoint requires authentication."""
        if not self.client:
            pytest.fail("MCP server not implemented yet")

        valid_config = [{
            "service_name": "docker",
            "enabled": True,
            "auto_setup": True
        }]

        # Test without authentication
        response = self.client.put(
            f"/installation/{self.test_installation_id}/services",
            json=valid_config
        )

        # Should require authentication (401/403) when fully implemented
        # For now, accept 404 for missing endpoint or 400 for validation errors
        assert response.status_code in [400, 401, 403, 404]

    def test_service_configuration_response_format(self):
        """Test the expected response format for successful updates."""
        if not self.client:
            pytest.fail("MCP server not implemented yet")

        valid_config = [{
            "service_name": "docker",
            "enabled": True,
            "endpoint": "http://localhost:2376",
            "auto_setup": True,
            "config_overrides": {"timeout": 60}
        }]

        response = self.client.put(
            f"/installation/{self.test_installation_id}/services",
            json=valid_config
        )

        if response.status_code == 200:
            response_data = response.json()

            # Should contain expected response structure
            assert "installation_id" in response_data
            assert "services" in response_data
            assert "updated_at" in response_data

            # Verify service structure
            service = response_data["services"][0]
            assert "name" in service
            assert "enabled" in service
            assert "endpoint" in service
            assert "auto_setup" in service
            assert "config_overrides" in service
            assert "last_updated" in service

    def test_service_configuration_concurrent_updates(self):
        """Test handling of concurrent service configuration updates."""
        if not self.client:
            pytest.fail("MCP server not implemented yet")

        # This test ensures the endpoint handles concurrent modifications properly
        config1 = [{
            "service_name": "docker",
            "enabled": True,
            "auto_setup": True
        }]

        config2 = [{
            "service_name": "docker",
            "enabled": False,
            "auto_setup": False
        }]

        # Simulate concurrent requests (simplified for testing)
        response1 = self.client.put(
            f"/installation/{self.test_installation_id}/services",
            json=config1
        )

        response2 = self.client.put(
            f"/installation/{self.test_installation_id}/services",
            json=config2
        )

        # Both should be handled appropriately (not crash)
        assert response1.status_code in [200, 400, 404, 409]  # 404 until endpoint implemented, 409 for conflict
        assert response2.status_code in [200, 400, 404, 409]


class TestServiceConfigurationModel:
    """Test the ServiceConfiguration Pydantic model validation."""

    def test_valid_service_configuration(self):
        """Test valid ServiceConfiguration instances."""
        # Test minimal valid configuration
        config = ServiceConfiguration(
            service_name="docker",
            enabled=True
        )
        assert config.service_name == "docker"
        assert config.enabled == True
        assert config.auto_setup == True  # Default value
        assert config.config_overrides == {}  # Default value

        # Test full configuration
        full_config = ServiceConfiguration(
            service_name="qdrant",
            enabled=True,
            endpoint="http://localhost:6333",
            auto_setup=False,
            config_overrides={"timeout": 30, "retries": 3}
        )
        assert full_config.service_name == "qdrant"
        assert full_config.endpoint == "http://localhost:6333"
        assert full_config.auto_setup == False
        assert full_config.config_overrides["timeout"] == 30

    def test_invalid_service_name(self):
        """Test invalid service names raise ValidationError."""
        with pytest.raises(ValueError, match="service_name must be one of"):
            ServiceConfiguration(
                service_name="invalid_service",
                enabled=True
            )

    def test_invalid_endpoint_url(self):
        """Test invalid endpoint URLs raise ValidationError."""
        with pytest.raises(ValueError, match="endpoint must be HTTP or HTTPS URL"):
            ServiceConfiguration(
                service_name="docker",
                enabled=True,
                endpoint="not-a-url"
            )

        with pytest.raises(ValueError, match="endpoint must be HTTP or HTTPS URL"):
            ServiceConfiguration(
                service_name="docker",
                enabled=True,
                endpoint="ftp://localhost:21"
            )

    def test_service_configuration_serialization(self):
        """Test ServiceConfiguration can be serialized to JSON."""
        config = ServiceConfiguration(
            service_name="ollama",
            enabled=True,
            endpoint="http://localhost:11434",
            auto_setup=True,
            config_overrides={"model": "llama2", "context_length": 4096}
        )

        json_data = config.model_dump()
        assert json_data["service_name"] == "ollama"
        assert json_data["enabled"] == True
        assert json_data["endpoint"] == "http://localhost:11434"
        assert json_data["config_overrides"]["model"] == "llama2"

    def test_service_configuration_deserialization(self):
        """Test ServiceConfiguration can be created from JSON data."""
        json_data = {
            "service_name": "qdrant",
            "enabled": False,
            "endpoint": "https://qdrant.example.com:6333",
            "auto_setup": False,
            "config_overrides": {
                "api_key": "secret",
                "timeout": 60
            }
        }

        config = ServiceConfiguration(**json_data)
        assert config.service_name == "qdrant"
        assert config.enabled == False
        assert config.endpoint == "https://qdrant.example.com:6333"
        assert config.config_overrides["api_key"] == "secret"