"""McpServerConfig model for MCP server configuration."""

from pydantic import BaseModel, Field, validator
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

    @validator("host", always=True)
    def set_default_host(cls, v: str, values: dict) -> str:
        """Set default host based on server type if not specified."""
        if not v and "server_type" in values:
            return values["server_type"].default_host
        return v

    @validator("port", always=True)
    def set_default_port(cls, v: int, values: dict) -> int:
        """Set default port based on server type if not specified."""
        if v == 0 and "server_type" in values:
            return values["server_type"].default_port
        return v

    @validator("port")
    def validate_port_range(cls, v: int) -> int:
        """Validate port is in valid range."""
        if v < 1024 or v > 65535:
            raise ValueError(f"Port must be between 1024 and 65535, got {v}")
        return v

    @validator("host")
    def validate_admin_localhost(cls, v: str, values: dict) -> str:
        """Validate that admin server is bound to localhost for security."""
        if (
            "server_type" in values
            and values["server_type"] == McpServerType.ADMIN
            and v not in ["127.0.0.1", "localhost"]
        ):
            raise ValueError("Admin server must be bound to localhost (127.0.0.1) for security")
        return v

    @property
    def url(self) -> str:
        """Get the full URL for this server configuration."""
        return f"http://{self.host}:{self.port}"

    def is_localhost_only(self) -> bool:
        """Check if this server is restricted to localhost access."""
        return self.server_type == McpServerType.ADMIN