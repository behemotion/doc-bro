"""McpResponse model for standardized MCP operation responses."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, field_validator, ValidationInfo


class McpResponse(BaseModel):
    """Standardized response format for MCP operations.

    Attributes:
        success: Operation success indicator
        data: Response data (varies by method)
        error: Error message if success is False
        message: Human-readable message (especially for errors)
        metadata: Additional response metadata
    """

    success: bool
    data: Any = Field(default=None)
    error: Optional[str] = Field(default=None)
    message: Optional[str] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default=None)

    @field_validator("error")
    @classmethod
    def validate_error_with_success(cls, v: Optional[str], info: ValidationInfo) -> Optional[str]:
        """Validate that error is provided when success is False."""
        success = info.data.get("success", True) if info.data else True

        if not success and not v:
            raise ValueError("Error message must be provided when success is False")

        if success and v:
            raise ValueError("Error message should not be provided when success is True")

        return v

    @classmethod
    def success_response(
        cls,
        data: Any = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "McpResponse":
        """Create a successful response."""
        return cls(
            success=True,
            data=data,
            metadata=metadata
        )

    @classmethod
    def error_response(
        cls,
        error: str,
        message: Optional[str] = None,
        data: Any = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "McpResponse":
        """Create an error response."""
        return cls(
            success=False,
            error=error,
            message=message,
            data=data,
            metadata=metadata
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert response to dictionary format."""
        result = {
            "success": self.success,
            "data": self.data,
        }

        if self.error is not None:
            result["error"] = self.error

        if self.message is not None:
            result["message"] = self.message

        if self.metadata is not None:
            result["metadata"] = self.metadata

        return result