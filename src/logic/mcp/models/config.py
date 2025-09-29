"""McpServerConfig model for MCP server configuration."""

from typing import Any
from pydantic import BaseModel, Field, field_validator, model_validator
from .server_type import McpServerType


class McpServerConfig(BaseModel):
    """Configuration settings for MCP servers.

    Attributes:
        server_type: Type of server to configure
        host: Server bind address (default varies by server type)
        port: Server port (default varies by server type)
        enabled: Whether server is enabled
    """

    server_type: McpServerType
    host: str = ""  # Will be set by validator if empty
    port: int = 0  # Will be set by validator if 0
    enabled: bool = Field(default=True)

    @model_validator(mode='after')
    def set_defaults_and_validate(self) -> 'McpServerConfig':
        """Set defaults and validate configuration."""
        # Set default host if empty
        if not self.host:
            self.host = self.server_type.default_host

        # Set default port if zero
        if self.port == 0:
            self.port = self.server_type.default_port

        # Validate port range
        if self.port < 1024 or self.port > 65535:
            raise ValueError(f"Port must be between 1024 and 65535, got {self.port}")

        # Validate admin server is localhost only
        if (
            self.server_type == McpServerType.ADMIN
            and self.host not in ["127.0.0.1", "localhost"]
        ):
            raise ValueError("Admin server must be bound to localhost (127.0.0.1) for security")

        return self

    @property
    def url(self) -> str:
        """Get the full URL for this server configuration."""
        return f"http://{self.host}:{self.port}"

    def is_localhost_only(self) -> bool:
        """Check if this server is restricted to localhost access."""
        return self.server_type == McpServerType.ADMIN