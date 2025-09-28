"""System info entity model."""


from pydantic import BaseModel, Field, field_validator


class SystemInfo(BaseModel):
    """System requirement validation status."""

    python_version: str = Field(..., description="Detected Python version")
    uv_version: str | None = Field(None, description="Detected UV version if available")
    memory_gb: float = Field(..., gt=0, description="Available system memory in GB")
    disk_space_gb: float = Field(..., gt=0, description="Available disk space in GB")
    platform: str = Field(..., description="Operating system platform")
    requirements_met: bool = Field(..., description="Whether all system requirements are satisfied")

    @field_validator('python_version')
    @classmethod
    def validate_python_version_format(cls, v):
        """Validate Python version follows semantic version format."""
        import re
        # Basic semantic version pattern (e.g., "3.13.1", "3.13.0")
        pattern = r'^(\d+)\.(\d+)\.(\d+).*$'
        if not re.match(pattern, v):
            raise ValueError("Python version must follow semantic version format (e.g., '3.13.1')")
        return v

    @field_validator('platform')
    @classmethod
    def validate_platform_identifier(cls, v):
        """Validate platform is a valid platform identifier."""
        valid_platforms = ['darwin', 'linux', 'win32', 'cygwin', 'msys']
        if v.lower() not in valid_platforms:
            raise ValueError(f"Platform must be one of: {', '.join(valid_platforms)}")
        return v

    @property
    def python_major_minor(self) -> tuple[int, int]:
        """Get Python major and minor version numbers."""
        import re
        match = re.match(r'^(\d+)\.(\d+)', self.python_version)
        if match:
            return int(match.group(1)), int(match.group(2))
        return 0, 0

    @property
    def meets_python_requirement(self) -> bool:
        """Check if Python version meets minimum requirement (3.13+)."""
        major, minor = self.python_major_minor
        return major > 3 or (major == 3 and minor >= 13)

    @property
    def meets_memory_requirement(self) -> bool:
        """Check if memory meets minimum requirement (1GB)."""
        return self.memory_gb >= 1.0

    @property
    def meets_disk_requirement(self) -> bool:
        """Check if disk space meets minimum requirement (1GB)."""
        return self.disk_space_gb >= 1.0

    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization."""
        return {
            "python_version": self.python_version,
            "uv_version": self.uv_version,
            "memory_gb": self.memory_gb,
            "disk_space_gb": self.disk_space_gb,
            "platform": self.platform,
            "requirements_met": self.requirements_met
        }

    model_config = {}


