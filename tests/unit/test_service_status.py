"""Unit tests for ServiceStatus model."""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError

from src.models.installation import ServiceStatus


class TestServiceStatus:
    """Test cases for ServiceStatus model validation and behavior."""

    def test_valid_service_status_creation(self):
        """Test creating a valid ServiceStatus instance."""
        status = ServiceStatus(
            name="docker",
            available=True,
            version="24.0.0",
            endpoint="unix:///var/run/docker.sock",
            last_checked=datetime.now(),
            error_message=None,
            setup_completed=True
        )

        assert status.name == "docker"
        assert status.available is True
        assert status.version == "24.0.0"
        assert status.setup_completed is True

    def test_service_name_validation(self):
        """Test that name must be one of supported services."""
        supported_services = ["docker", "ollama", "qdrant"]

        for service_name in supported_services:
            status = ServiceStatus(
                name=service_name,
                available=True,
                last_checked=datetime.now(),
                setup_completed=False
            )
            assert status.name == service_name

        # Test invalid service name
        with pytest.raises(ValidationError):
            ServiceStatus(
                name="unsupported_service",
                available=True,
                last_checked=datetime.now(),
                setup_completed=False
            )

    def test_optional_fields(self):
        """Test that optional fields can be None."""
        status = ServiceStatus(
            name="ollama",
            available=False,
            version=None,
            endpoint=None,
            last_checked=datetime.now(),
            error_message="Service not found",
            setup_completed=False
        )

        assert status.version is None
        assert status.endpoint is None
        assert status.error_message == "Service not found"

    def test_endpoint_format_validation(self):
        """Test endpoint format validation based on service type."""
        # Test valid endpoints for different services
        test_cases = [
            ("docker", "unix:///var/run/docker.sock"),
            ("ollama", "http://localhost:11434"),
            ("qdrant", "http://localhost:6333")
        ]

        for service_name, endpoint in test_cases:
            status = ServiceStatus(
                name=service_name,
                available=True,
                endpoint=endpoint,
                last_checked=datetime.now(),
                setup_completed=True
            )
            assert status.endpoint == endpoint

    def test_error_handling_when_unavailable(self):
        """Test proper error message handling when service is unavailable."""
        status = ServiceStatus(
            name="docker",
            available=False,
            version=None,
            endpoint=None,
            last_checked=datetime.now(),
            error_message="Docker daemon is not running",
            setup_completed=False
        )

        assert status.available is False
        assert status.error_message is not None
        assert "daemon is not running" in status.error_message

    def test_last_checked_timestamp(self):
        """Test that last_checked timestamp is properly handled."""
        now = datetime.now()
        status = ServiceStatus(
            name="ollama",
            available=True,
            last_checked=now,
            setup_completed=True
        )

        assert status.last_checked == now

        # Test that timestamp is within reasonable range
        time_diff = abs((datetime.now() - status.last_checked).total_seconds())
        assert time_diff < 60  # Should be within 1 minute

    def test_json_serialization(self):
        """Test that ServiceStatus can be serialized to/from JSON."""
        original = ServiceStatus(
            name="qdrant",
            available=True,
            version="1.7.0",
            endpoint="http://localhost:6333",
            last_checked=datetime(2025, 1, 25, 10, 30, 0),
            error_message=None,
            setup_completed=True
        )

        # Serialize to JSON
        json_data = original.model_dump(mode='json')
        assert isinstance(json_data, dict)
        assert json_data["name"] == "qdrant"
        assert json_data["available"] is True
        assert json_data["version"] == "7.2.0"

        # Deserialize from JSON
        restored = ServiceStatus.model_validate(json_data)
        assert restored.name == original.name
        assert restored.available == original.available
        assert restored.version == original.version

    def test_setup_completed_flag(self):
        """Test setup_completed flag behavior."""
        # Service available but setup not completed
        status1 = ServiceStatus(
            name="qdrant",
            available=True,
            version="1.7.0",
            endpoint="http://localhost:6333",
            last_checked=datetime.now(),
            setup_completed=False
        )
        assert status1.available is True
        assert status1.setup_completed is False

        # Service available and setup completed
        status2 = ServiceStatus(
            name="qdrant",
            available=True,
            version="1.7.0",
            endpoint="http://localhost:6333",
            last_checked=datetime.now(),
            setup_completed=True
        )
        assert status2.available is True
        assert status2.setup_completed is True

    def test_service_version_formats(self):
        """Test various version format handling."""
        version_formats = ["1.0.0", "24.0.0-beta", "0.1.17", "latest", None]

        for version in version_formats:
            status = ServiceStatus(
                name="docker",
                available=version is not None,
                version=version,
                last_checked=datetime.now(),
                setup_completed=False
            )
            assert status.version == version

    def test_error_message_when_available(self):
        """Test that error_message can be None when service is available."""
        status = ServiceStatus(
            name="ollama",
            available=True,
            version="0.1.17",
            endpoint="http://localhost:11434",
            last_checked=datetime.now(),
            error_message=None,
            setup_completed=True
        )

        assert status.available is True
        assert status.error_message is None