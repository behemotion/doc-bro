"""Service status entity model."""

from pydantic import BaseModel, Field, model_validator

from .service_type import ServiceType


class ServiceStatus(BaseModel):
    """External service availability and configuration details."""

    service: ServiceType = Field(..., description="Type of external service")
    available: bool = Field(..., description="Whether the service is accessible")
    version: str | None = Field(None, description="Detected version if available")
    url: str | None = Field(None, description="Service URL if applicable")
    config_valid: bool = Field(..., description="Whether service configuration is valid")
    error_message: str | None = Field(None, description="Error details if unavailable")

    @model_validator(mode='after')
    def validate_service_consistency(self) -> 'ServiceStatus':
        """Validate service status consistency."""
        # Validate error message is provided when service is unavailable
        if self.available is False and not self.error_message:
            raise ValueError("Error message required when service is unavailable")

        # Validate version format if provided
        if self.version and not any(char.isdigit() for char in self.version):
            raise ValueError("Version should contain numeric components")

        return self

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

    model_config = {}
