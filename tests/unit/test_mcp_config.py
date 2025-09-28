"""Unit tests for McpServerConfig validation."""

import pytest
from pydantic import ValidationError

from src.logic.mcp.models.config import McpServerConfig
from src.logic.mcp.models.server_type import McpServerType


class TestMcpServerConfig:
    """Test cases for McpServerConfig model validation."""

    def test_read_only_server_default_configuration(self):
        """Test read-only server gets correct default configuration."""
        config = McpServerConfig(server_type=McpServerType.READ_ONLY)

        assert config.server_type == McpServerType.READ_ONLY
        assert config.host == "0.0.0.0"
        assert config.port == 9383
        assert config.enabled is True
        assert config.url == "http://0.0.0.0:9383"
        assert config.is_localhost_only() is False

    def test_admin_server_default_configuration(self):
        """Test admin server gets correct default configuration."""
        config = McpServerConfig(server_type=McpServerType.ADMIN)

        assert config.server_type == McpServerType.ADMIN
        assert config.host == "127.0.0.1"
        assert config.port == 9384
        assert config.enabled is True
        assert config.url == "http://127.0.0.1:9384"
        assert config.is_localhost_only() is True

    def test_custom_configuration_read_only(self):
        """Test read-only server with custom host and port."""
        config = McpServerConfig(
            server_type=McpServerType.READ_ONLY,
            host="192.168.1.100",
            port=8080,
            enabled=False
        )

        assert config.server_type == McpServerType.READ_ONLY
        assert config.host == "192.168.1.100"
        assert config.port == 8080
        assert config.enabled is False
        assert config.url == "http://192.168.1.100:8080"

    def test_admin_server_localhost_validation_success(self):
        """Test admin server accepts localhost addresses."""
        # Test 127.0.0.1
        config1 = McpServerConfig(
            server_type=McpServerType.ADMIN,
            host="127.0.0.1"
        )
        assert config1.host == "127.0.0.1"

        # Test localhost
        config2 = McpServerConfig(
            server_type=McpServerType.ADMIN,
            host="localhost"
        )
        assert config2.host == "localhost"

    def test_admin_server_rejects_non_localhost(self):
        """Test admin server rejects non-localhost addresses."""
        with pytest.raises(ValidationError) as exc_info:
            McpServerConfig(
                server_type=McpServerType.ADMIN,
                host="0.0.0.0"
            )

        error = exc_info.value
        assert "Admin server must be bound to localhost" in str(error)

    def test_admin_server_rejects_external_ip(self):
        """Test admin server rejects external IP addresses."""
        with pytest.raises(ValidationError) as exc_info:
            McpServerConfig(
                server_type=McpServerType.ADMIN,
                host="192.168.1.100"
            )

        error = exc_info.value
        assert "Admin server must be bound to localhost" in str(error)

    def test_port_range_validation_minimum(self):
        """Test port validation rejects ports below 1024."""
        with pytest.raises(ValidationError) as exc_info:
            McpServerConfig(
                server_type=McpServerType.READ_ONLY,
                port=1023
            )

        error = exc_info.value
        assert "Port must be between 1024 and 65535" in str(error)

    def test_port_range_validation_maximum(self):
        """Test port validation rejects ports above 65535."""
        with pytest.raises(ValidationError) as exc_info:
            McpServerConfig(
                server_type=McpServerType.READ_ONLY,
                port=65536
            )

        error = exc_info.value
        assert "Port must be between 1024 and 65535" in str(error)

    def test_port_range_validation_valid_bounds(self):
        """Test port validation accepts valid port range."""
        # Test minimum valid port
        config1 = McpServerConfig(
            server_type=McpServerType.READ_ONLY,
            port=1024
        )
        assert config1.port == 1024

        # Test maximum valid port
        config2 = McpServerConfig(
            server_type=McpServerType.READ_ONLY,
            port=65535
        )
        assert config2.port == 65535

    def test_custom_port_overrides_default(self):
        """Test custom port overrides default for server type."""
        config = McpServerConfig(
            server_type=McpServerType.ADMIN,
            port=9999
        )

        assert config.port == 9999  # Custom port, not default 9384

    def test_custom_host_overrides_default_for_read_only(self):
        """Test custom host overrides default for read-only server."""
        config = McpServerConfig(
            server_type=McpServerType.READ_ONLY,
            host="127.0.0.1"
        )

        assert config.host == "127.0.0.1"  # Custom host, not default 0.0.0.0

    def test_enabled_flag_validation(self):
        """Test enabled flag is properly validated."""
        # Test enabled=True
        config1 = McpServerConfig(
            server_type=McpServerType.READ_ONLY,
            enabled=True
        )
        assert config1.enabled is True

        # Test enabled=False
        config2 = McpServerConfig(
            server_type=McpServerType.READ_ONLY,
            enabled=False
        )
        assert config2.enabled is False

    def test_url_property_formatting(self):
        """Test URL property formats correctly."""
        config = McpServerConfig(
            server_type=McpServerType.ADMIN,
            host="127.0.0.1",
            port=9999
        )

        assert config.url == "http://127.0.0.1:9999"

    def test_is_localhost_only_method(self):
        """Test is_localhost_only method behavior."""
        read_only_config = McpServerConfig(server_type=McpServerType.READ_ONLY)
        admin_config = McpServerConfig(server_type=McpServerType.ADMIN)

        assert read_only_config.is_localhost_only() is False
        assert admin_config.is_localhost_only() is True

    def test_serialization_and_deserialization(self):
        """Test config can be serialized and deserialized."""
        original_config = McpServerConfig(
            server_type=McpServerType.ADMIN,
            host="127.0.0.1",
            port=9999,
            enabled=False
        )

        # Serialize to dict
        config_dict = original_config.model_dump()

        # Deserialize back
        restored_config = McpServerConfig(**config_dict)

        assert restored_config.server_type == original_config.server_type
        assert restored_config.host == original_config.host
        assert restored_config.port == original_config.port
        assert restored_config.enabled == original_config.enabled

    def test_empty_host_uses_default(self):
        """Test empty host string uses server type default."""
        config = McpServerConfig(
            server_type=McpServerType.READ_ONLY,
            host=""  # Empty string should trigger default
        )

        assert config.host == "0.0.0.0"  # Should use READ_ONLY default

    def test_zero_port_uses_default(self):
        """Test zero port uses server type default."""
        config = McpServerConfig(
            server_type=McpServerType.ADMIN,
            port=0  # Zero should trigger default
        )

        assert config.port == 9384  # Should use ADMIN default