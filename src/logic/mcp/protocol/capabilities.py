"""
MCP Capability Negotiation Models

Implements server and client capability models for the MCP protocol.
Used during initialization handshake to declare supported features.
"""

from typing import Optional

from pydantic import BaseModel, Field


class ToolsCapability(BaseModel):
    """Tools capability configuration."""

    list_changed: bool = Field(
        default=True,
        alias="listChanged",
        description="Server supports notifications when tools list changes",
    )

    class Config:
        populate_by_name = True


class ResourcesCapability(BaseModel):
    """Resources capability configuration."""

    subscribe: bool = Field(
        default=False,
        description="Server supports resource subscriptions for real-time updates",
    )
    list_changed: bool = Field(
        default=True,
        alias="listChanged",
        description="Server supports notifications when resources list changes",
    )

    class Config:
        populate_by_name = True


class PromptsCapability(BaseModel):
    """Prompts capability configuration."""

    list_changed: bool = Field(
        default=False,
        alias="listChanged",
        description="Server supports notifications when prompts list changes",
    )

    class Config:
        populate_by_name = True


class LoggingCapability(BaseModel):
    """Logging capability configuration."""

    # Empty for now, but allows for future logging-related capabilities
    pass


class ServerCapabilities(BaseModel):
    """Server capabilities exposed during initialization."""

    tools: Optional[ToolsCapability] = Field(
        default=None,
        description="Tools capability (function calling)",
    )
    resources: Optional[ResourcesCapability] = Field(
        default=None,
        description="Resources capability (data access)",
    )
    prompts: Optional[PromptsCapability] = Field(
        default=None,
        description="Prompts capability (prompt templates)",
    )
    logging: Optional[LoggingCapability] = Field(
        default=None,
        description="Logging capability",
    )

    @classmethod
    def default_read_only(cls) -> "ServerCapabilities":
        """Create default capabilities for read-only server."""
        return cls(
            tools=ToolsCapability(list_changed=True),
            resources=ResourcesCapability(subscribe=False, list_changed=True),
            prompts=PromptsCapability(list_changed=False),
            logging=LoggingCapability(),
        )

    @classmethod
    def default_admin(cls) -> "ServerCapabilities":
        """Create default capabilities for admin server."""
        return cls(
            tools=ToolsCapability(list_changed=True),
            resources=ResourcesCapability(subscribe=False, list_changed=True),
            prompts=PromptsCapability(list_changed=False),
            logging=LoggingCapability(),
        )


class ClientCapabilities(BaseModel):
    """Client capabilities received during initialization."""

    experimental: Optional[dict] = Field(
        default=None,
        description="Experimental capabilities (client-specific)",
    )
    roots: Optional[dict] = Field(
        default=None,
        description="Root paths for file access",
    )


class ServerInfo(BaseModel):
    """Server information exposed during initialization."""

    name: str = Field(..., description="Server name")
    version: str = Field(..., description="Server version")


class InitializeRequest(BaseModel):
    """MCP initialize request parameters."""

    protocol_version: str = Field(
        alias="protocolVersion",
        description="MCP protocol version",
    )
    capabilities: ClientCapabilities = Field(
        ...,
        description="Client capabilities",
    )
    client_info: dict = Field(
        alias="clientInfo",
        description="Client information",
    )

    class Config:
        populate_by_name = True


class InitializeResponse(BaseModel):
    """MCP initialize response result."""

    protocol_version: str = Field(
        alias="protocolVersion",
        description="MCP protocol version",
    )
    capabilities: ServerCapabilities = Field(
        ...,
        description="Server capabilities",
    )
    server_info: ServerInfo = Field(
        alias="serverInfo",
        description="Server information",
    )

    class Config:
        populate_by_name = True

    @classmethod
    def create(
        cls,
        server_name: str,
        server_version: str,
        capabilities: ServerCapabilities,
        protocol_version: str = "2024-11-05",
    ) -> "InitializeResponse":
        """Create an initialize response."""
        return cls(
            protocol_version=protocol_version,
            capabilities=capabilities,
            server_info=ServerInfo(name=server_name, version=server_version),
        )
