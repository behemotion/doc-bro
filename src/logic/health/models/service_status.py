"""Service status entity model."""

from typing import Optional
from pydantic import BaseModel, Field, validator

from .service_type import ServiceType


class ServiceStatus(BaseModel):
    """External service availability and configuration details."""

    service: ServiceType = Field(..., description="Type of external service")
    available: bool = Field(..., description="Whether the service is accessible")
    version: Optional[str] = Field(None, description="Detected version if available")
    url: Optional[str] = Field(None, description="Service URL if applicable")
    config_valid: bool = Field(..., description="Whether service configuration is valid")
    error_message: Optional[str] = Field(None, description="Error details if unavailable")

    @validator('error_message')
    def validate_error_message_when_unavailable(cls, v, values):
        """Validate error message is provided when service is unavailable."""
        available = values.get('available')
        if available is False and not v:
            raise ValueError("Error message required when service is unavailable")
        return v

    @validator('version')
    def validate_version_format(cls, v, values):
        """Validate version format based on service type."""
        if not v:
            return v

        service = values.get('service')
        if not service:
            return v

        # Basic version validation - should contain numbers
        if not any(char.isdigit() for char in v):
            raise ValueError("Version should contain numeric components")

        return v

    @property
    def is_healthy(self) -> bool:
        """Check if service is in healthy state."""
        return self.available and self.config_valid

    @property
    def display_name(self) -> str:
        """Get display name for this service."""
        return self.service.display_name

    @property
    def is_required(self) -> bool:
        """Check if this service is required for basic operation."""
        return self.service.is_required

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "service": self.service.value,
            "available": self.available,
            "version": self.version,
            "url": self.url,
            "config_valid": self.config_valid,
            "error_message": self.error_message
        }

    class Config:
        """Pydantic configuration."""
        pass