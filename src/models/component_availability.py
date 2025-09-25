"""ComponentAvailability model for DocBro setup logic.

This model tracks detection results and availability status of external dependencies.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any
from pathlib import Path
from pydantic import BaseModel, Field, field_validator, model_validator

from .setup_types import ComponentType, HealthStatus


class ComponentAvailability(BaseModel):
    """Tracks detection results and availability status of external dependencies.

    This model represents the current state of an external component (Docker, Ollama,
    MCP client) including its availability, version, health status, and capabilities.
    """

    component_type: ComponentType = Field(
        description="Type of component (Docker, Ollama, MCP_Client)"
    )
    component_name: str = Field(
        description="Specific component name (e.g., 'docker', 'ollama', 'claude-code')"
    )
    available: bool = Field(
        description="Whether the component is available and functional"
    )
    version: Optional[str] = Field(
        default=None,
        description="Detected version if available"
    )
    installation_path: Optional[Path] = Field(
        default=None,
        description="Path to component executable/installation"
    )
    configuration_path: Optional[Path] = Field(
        default=None,
        description="Path to component configuration files"
    )
    health_status: HealthStatus = Field(
        description="Current health status of the component"
    )
    last_checked: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="When availability was last verified"
    )
    error_message: Optional[str] = Field(
        default=None,
        description="Error details if component is unavailable"
    )
    capabilities: Dict[str, Any] = Field(
        default_factory=dict,
        description="Component-specific capability information"
    )

    class Config:
        """Pydantic configuration."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat(),
            Path: str
        }

    @field_validator('component_name')
    @classmethod
    def validate_component_name(cls, v: str) -> str:
        """Validate component name is not empty."""
        if not v.strip():
            raise ValueError("Component name must be non-empty string")
        return v.strip()

    @field_validator('installation_path')
    @classmethod
    def validate_installation_path(cls, v: Optional[Path]) -> Optional[Path]:
        """Validate installation path exists if provided."""
        if v is not None and not v.exists():
            # Note: In real usage, we might want to be more lenient here
            # as paths might be temporarily unavailable
            pass  # Allow non-existent paths for now
        return v

    @field_validator('configuration_path')
    @classmethod
    def validate_configuration_path(cls, v: Optional[Path]) -> Optional[Path]:
        """Validate configuration path exists if provided."""
        if v is not None and not v.exists():
            # Note: Similar to installation_path, allow non-existent paths
            pass  # Allow non-existent paths for now
        return v

    @model_validator(mode='after')
    def validate_availability_consistency(self) -> 'ComponentAvailability':
        """Validate consistency between availability and health status."""
        if self.available and self.health_status == HealthStatus.UNHEALTHY:
            raise ValueError("Component cannot be available if health status is UNHEALTHY")

        if not self.available and self.health_status == HealthStatus.HEALTHY:
            # This might be valid in some edge cases, so just ensure error message is present
            if not self.error_message:
                self.error_message = "Component unavailable but no error message provided"

        return self

    @model_validator(mode='after')
    def validate_recent_check(self) -> 'ComponentAvailability':
        """Validate last_checked is recent (within 24 hours for valid status)."""
        now = datetime.now(timezone.utc)
        time_diff = now - self.last_checked

        # Allow future timestamps with small tolerance (for clock skew)
        if time_diff < timedelta(minutes=-5):
            raise ValueError("last_checked cannot be significantly in the future")

        # Warn about old data but don't fail validation
        if time_diff > timedelta(hours=24):
            # In a real system, this might be logged as a warning
            pass

        return self

    def is_healthy(self) -> bool:
        """Check if component is healthy."""
        return self.health_status == HealthStatus.HEALTHY

    def is_available_and_healthy(self) -> bool:
        """Check if component is both available and healthy."""
        return self.available and self.is_healthy()

    def has_error(self) -> bool:
        """Check if component has an error message."""
        return self.error_message is not None and len(self.error_message.strip()) > 0

    def is_stale(self, max_age_hours: int = 1) -> bool:
        """Check if the availability data is stale."""
        now = datetime.now(timezone.utc)
        max_age = timedelta(hours=max_age_hours)
        return (now - self.last_checked) > max_age

    def refresh_timestamp(self) -> None:
        """Update last_checked to current time."""
        self.last_checked = datetime.now(timezone.utc)

    def mark_as_unavailable(self, error_message: str) -> None:
        """Mark component as unavailable with error message."""
        self.available = False
        self.health_status = HealthStatus.UNHEALTHY
        self.error_message = error_message
        self.refresh_timestamp()

    def mark_as_available(
        self,
        version: Optional[str] = None,
        installation_path: Optional[Path] = None,
        health_status: HealthStatus = HealthStatus.HEALTHY
    ) -> None:
        """Mark component as available with optional details."""
        self.available = True
        self.health_status = health_status
        self.error_message = None
        if version:
            self.version = version
        if installation_path:
            self.installation_path = installation_path
        self.refresh_timestamp()

    def update_capabilities(self, capabilities: Dict[str, Any]) -> None:
        """Update component capabilities."""
        self.capabilities.update(capabilities)
        self.refresh_timestamp()

    def get_display_status(self) -> str:
        """Get human-readable status for display."""
        if self.available and self.is_healthy():
            version_info = f" (v{self.version})" if self.version else ""
            return f"✅ Available{version_info}"
        elif self.available and self.health_status == HealthStatus.DEGRADED:
            return f"⚠️ Degraded"
        else:
            return f"❌ Not Available"

    def get_status_details(self) -> Dict[str, Any]:
        """Get detailed status information."""
        return {
            "component_type": self.component_type,
            "component_name": self.component_name,
            "available": self.available,
            "health_status": self.health_status,
            "version": self.version,
            "installation_path": str(self.installation_path) if self.installation_path else None,
            "configuration_path": str(self.configuration_path) if self.configuration_path else None,
            "last_checked": self.last_checked.isoformat(),
            "error_message": self.error_message,
            "capabilities": self.capabilities,
            "is_stale": self.is_stale(),
            "display_status": self.get_display_status()
        }

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return self.model_dump(mode='json')

    @classmethod
    def from_dict(cls, data: dict) -> 'ComponentAvailability':
        """Create instance from dictionary."""
        return cls(**data)

    @classmethod
    def create_unavailable(
        cls,
        component_type: ComponentType,
        component_name: str,
        error_message: str
    ) -> 'ComponentAvailability':
        """Create an unavailable component record."""
        return cls(
            component_type=component_type,
            component_name=component_name,
            available=False,
            health_status=HealthStatus.UNHEALTHY,
            error_message=error_message
        )

    @classmethod
    def create_available(
        cls,
        component_type: ComponentType,
        component_name: str,
        version: Optional[str] = None,
        installation_path: Optional[Path] = None,
        configuration_path: Optional[Path] = None,
        capabilities: Optional[Dict[str, Any]] = None
    ) -> 'ComponentAvailability':
        """Create an available component record."""
        return cls(
            component_type=component_type,
            component_name=component_name,
            available=True,
            version=version,
            installation_path=installation_path,
            configuration_path=configuration_path,
            health_status=HealthStatus.HEALTHY,
            capabilities=capabilities or {}
        )