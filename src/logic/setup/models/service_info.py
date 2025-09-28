"""Service information model."""

from datetime import datetime
from enum import Enum

from pydantic import BaseModel, Field, field_validator


class ServiceStatus(str, Enum):
    """Status of an external service."""

    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    UNKNOWN = "unknown"


class ServiceInfo(BaseModel):
    """Information about a detected external service."""

    name: str = Field(
        description="Service identifier (e.g., 'docker', 'qdrant', 'ollama')"
    )
    version: str | None = Field(
        default=None,
        description="Detected version of the service"
    )
    status: ServiceStatus = Field(
        default=ServiceStatus.UNKNOWN,
        description="Current status of the service"
    )
    url: str | None = Field(
        default=None,
        description="Service endpoint URL if applicable"
    )
    last_check: datetime = Field(
        default_factory=datetime.utcnow,
        description="When service was last validated (UTC)"
    )
    error: str | None = Field(
        default=None,
        description="Detection error details if any"
    )

    @field_validator("name")
    @classmethod
    def validate_service_name(cls, v: str) -> str:
        """Validate that service name is known."""
        known_services = [
            "docker",
            "qdrant",
            "ollama",
            "sqlite_vec",
            "python",
            "uv",
            "git"
        ]

        if v not in known_services:
            raise ValueError(
                f"Unknown service: {v}. "
                f"Known services: {', '.join(known_services)}"
            )
        return v

    @field_validator("url")
    @classmethod
    def validate_url_format(cls, v: str | None) -> str | None:
        """Validate URL format if provided."""
        if v is None:
            return v

        if not v.startswith(("http://", "https://", "tcp://", "unix://")):
            raise ValueError(f"Invalid service URL format: {v}")

        return v

    def is_available(self) -> bool:
        """Check if service is available."""
        return self.status == ServiceStatus.AVAILABLE

    def is_required(self) -> bool:
        """Check if this is a required service."""
        # Core required services
        required = ["python", "uv", "sqlite_vec"]
        return self.name in required

    def mark_available(self, version: str | None = None) -> None:
        """Mark service as available."""
        self.status = ServiceStatus.AVAILABLE
        self.error = None
        self.last_check = datetime.utcnow()
        if version:
            self.version = version

    def mark_unavailable(self, error: str | None = None) -> None:
        """Mark service as unavailable."""
        self.status = ServiceStatus.UNAVAILABLE
        self.last_check = datetime.utcnow()
        if error:
            self.error = error

    def needs_recheck(self, max_age_seconds: int = 300) -> bool:
        """Check if service status needs to be rechecked."""
        age = (datetime.utcnow() - self.last_check).total_seconds()
        return age > max_age_seconds

    def to_display_dict(self) -> dict[str, str]:
        """Convert to user-friendly display format."""
        status_emoji = {
            ServiceStatus.AVAILABLE: "✅",
            ServiceStatus.UNAVAILABLE: "❌",
            ServiceStatus.UNKNOWN: "❓"
        }

        display = {
            "Service": self.name.title(),
            "Status": f"{status_emoji[self.status]} {self.status.value}"
        }

        if self.version:
            display["Version"] = self.version

        if self.url:
            display["URL"] = self.url

        if self.error and self.status == ServiceStatus.UNAVAILABLE:
            display["Error"] = self.error

        return display

    def get_setup_instructions(self) -> str | None:
        """Get setup instructions for unavailable service."""
        if self.status != ServiceStatus.UNAVAILABLE:
            return None

        instructions = {
            "docker": (
                "Docker is not available. Please install Docker:\n"
                "  macOS/Windows: https://www.docker.com/products/docker-desktop\n"
                "  Linux: https://docs.docker.com/engine/install/"
            ),
            "qdrant": (
                "Qdrant is not running. Start it with:\n"
                "  docker run -p 6333:6333 qdrant/qdrant"
            ),
            "ollama": (
                "Ollama is not available. Please install and start Ollama:\n"
                "  macOS: brew install ollama && ollama serve\n"
                "  Linux: curl -fsSL https://ollama.com/install.sh | sh"
            ),
            "python": (
                "Python 3.13+ is required. Please install it:\n"
                "  https://www.python.org/downloads/"
            ),
            "uv": (
                "UV is required for installation. Please install it:\n"
                "  curl -fsSL https://github.com/astral-sh/uv/releases/latest/download/install.sh | sh"
            )
        }

        return instructions.get(self.name)

    class Config:
        """Pydantic configuration."""

        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }
