"""
JSON-RPC 2.0 Message Models for MCP Protocol

Implements message structures according to JSON-RPC 2.0 specification.
https://www.jsonrpc.org/specification
"""

from enum import IntEnum
from typing import Any, Optional, Union

from pydantic import BaseModel, Field, field_validator


class McpErrorCode(IntEnum):
    """Standard JSON-RPC 2.0 error codes plus MCP-specific codes."""

    # Standard JSON-RPC 2.0 errors
    PARSE_ERROR = -32700
    INVALID_REQUEST = -32600
    METHOD_NOT_FOUND = -32601
    INVALID_PARAMS = -32602
    INTERNAL_ERROR = -32603

    # MCP-specific errors
    SERVER_NOT_INITIALIZED = -32002
    UNKNOWN_ERROR_CODE = -32001
    REQUEST_TIMEOUT = -32000


class JsonRpcError(BaseModel):
    """JSON-RPC 2.0 error object."""

    code: int = Field(..., description="Error code")
    message: str = Field(..., description="Error message")
    data: Optional[Any] = Field(None, description="Additional error data")

    @classmethod
    def from_code(cls, code: McpErrorCode, message: Optional[str] = None, data: Optional[Any] = None) -> "JsonRpcError":
        """Create error from standard code."""
        default_messages = {
            McpErrorCode.PARSE_ERROR: "Parse error",
            McpErrorCode.INVALID_REQUEST: "Invalid request",
            McpErrorCode.METHOD_NOT_FOUND: "Method not found",
            McpErrorCode.INVALID_PARAMS: "Invalid params",
            McpErrorCode.INTERNAL_ERROR: "Internal error",
            McpErrorCode.SERVER_NOT_INITIALIZED: "Server not initialized",
            McpErrorCode.UNKNOWN_ERROR_CODE: "Unknown error code",
            McpErrorCode.REQUEST_TIMEOUT: "Request timeout",
        }
        return cls(
            code=code,
            message=message or default_messages.get(code, "Unknown error"),
            data=data,
        )


class JsonRpcRequest(BaseModel):
    """JSON-RPC 2.0 request message."""

    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    id: Union[str, int] = Field(..., description="Request ID")
    method: str = Field(..., description="Method name")
    params: Optional[dict[str, Any]] = Field(None, description="Method parameters")

    @field_validator("jsonrpc")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Ensure JSON-RPC version is 2.0."""
        if v != "2.0":
            raise ValueError("jsonrpc version must be '2.0'")
        return v


class JsonRpcNotification(BaseModel):
    """JSON-RPC 2.0 notification message (no response expected)."""

    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    method: str = Field(..., description="Method name")
    params: Optional[dict[str, Any]] = Field(None, description="Method parameters")

    @field_validator("jsonrpc")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Ensure JSON-RPC version is 2.0."""
        if v != "2.0":
            raise ValueError("jsonrpc version must be '2.0'")
        return v


class JsonRpcResponse(BaseModel):
    """JSON-RPC 2.0 response message."""

    jsonrpc: str = Field("2.0", description="JSON-RPC version")
    id: Union[str, int] = Field(..., description="Request ID")
    result: Optional[Any] = Field(None, description="Result data")
    error: Optional[JsonRpcError] = Field(None, description="Error object")

    @field_validator("jsonrpc")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """Ensure JSON-RPC version is 2.0."""
        if v != "2.0":
            raise ValueError("jsonrpc version must be '2.0'")
        return v

    def model_post_init(self, __context: Any) -> None:
        """Validate that either result or error is set, but not both."""
        if self.result is not None and self.error is not None:
            raise ValueError("Response must have either result or error, not both")
        if self.result is None and self.error is None:
            raise ValueError("Response must have either result or error")

    @classmethod
    def success(cls, request_id: Union[str, int], result: Any) -> "JsonRpcResponse":
        """Create a success response."""
        return cls(id=request_id, result=result)

    @classmethod
    def error_response(
        cls,
        request_id: Union[str, int],
        code: McpErrorCode,
        message: Optional[str] = None,
        data: Optional[Any] = None,
    ) -> "JsonRpcResponse":
        """Create an error response."""
        return cls(
            id=request_id,
            error=JsonRpcError.from_code(code, message, data),
        )


# Type alias for any JSON-RPC message
JsonRpcMessage = Union[JsonRpcRequest, JsonRpcNotification, JsonRpcResponse]
