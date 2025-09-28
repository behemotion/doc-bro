"""McpResponse model for standardized MCP operation responses."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field, validator


class McpResponse(BaseModel):
    """Standardized response format for MCP operations.

    Attributes:
        success: Operation success indicator
        data: Response data (varies by method)
        error: Error message if success is False
        metadata: Additional response metadata
    """

    success: bool
    data: Any = Field(default=None)
    error: Optional[str] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default=None)

    @validator("error")
    def validate_error_with_success(cls, v: Optional[str], values: Dict[str, Any]) -> Optional[str]:
        """Validate that error is provided when success is False."""
        success = values.get("success", True)

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
        data: Any = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> "McpResponse":
        """Create an error response."""
        return cls(
            success=False,
            error=error,
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

        if self.metadata is not None:
            result["metadata"] = self.metadata

        return result