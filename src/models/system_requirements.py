"""System requirements validation model.

This module contains the SystemRequirements model for validating current system status
against installation requirements. This is different from the SystemRequirements model
in installation.py which defines what requirements are needed.

- installation.py SystemRequirements: Specification of what's required
- system_requirements.py SystemRequirements: Validation of current system against requirements
"""


from packaging import version
from pydantic import BaseModel, ConfigDict, Field, field_validator


class SystemRequirements(BaseModel):
    """System requirements validation and status."""

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True
    )

    python_version: str = Field(..., description="Current Python version")
    python_valid: bool = Field(..., description="Whether Python version meets requirements")
    available_memory: int = Field(..., description="Available system memory in GB")
    memory_valid: bool = Field(..., description="Whether memory meets requirements")
    available_disk: int = Field(..., description="Available disk space in GB")
    disk_valid: bool = Field(..., description="Whether disk space meets requirements")
    platform: str = Field(..., description="Operating system platform")
    platform_supported: bool = Field(..., description="Whether platform is supported")
    uv_available: bool = Field(..., description="Whether UV package manager is available")
    uv_version: str | None = Field(None, description="UV version if available")

    @field_validator('python_version')
    @classmethod
    def validate_python_version(cls, v: str) -> str:
        """Validate Python version format."""
        try:
            version.Version(v)
        except version.InvalidVersion:
            raise ValueError("python_version must be a valid semantic version")
        return v

    @field_validator('python_valid')
    @classmethod
    def validate_python_valid(cls, v: bool, info) -> bool:
        """Validate python_valid matches version requirement."""
        if hasattr(info, 'data') and 'python_version' in info.data:
            python_ver = info.data['python_version']
            try:
                is_valid = version.Version(python_ver) >= version.Version("3.13.0")
                if v != is_valid:
                    raise ValueError(
                        f"python_valid={v} doesn't match requirement check for version {python_ver}"
                    )
            except version.InvalidVersion:
                # If version is invalid, python_valid should be False
                if v is True:
                    raise ValueError("python_valid cannot be True with invalid python_version")
        return v

    @field_validator('available_memory')
    @classmethod
    def validate_available_memory(cls, v: int) -> int:
        """Validate available memory is non-negative."""
        if v < 0:
            raise ValueError("available_memory must be non-negative")
        return v

    @field_validator('memory_valid')
    @classmethod
    def validate_memory_valid(cls, v: bool, info) -> bool:
        """Validate memory_valid matches memory requirement."""
        if hasattr(info, 'data') and 'available_memory' in info.data:
            memory_gb = info.data['available_memory']
            is_valid = memory_gb >= 4
            if v != is_valid:
                raise ValueError(
                    f"memory_valid={v} doesn't match requirement check for {memory_gb}GB"
                )
        return v

    @field_validator('available_disk')
    @classmethod
    def validate_available_disk(cls, v: int) -> int:
        """Validate available disk space is non-negative."""
        if v < 0:
            raise ValueError("available_disk must be non-negative")
        return v

    @field_validator('disk_valid')
    @classmethod
    def validate_disk_valid(cls, v: bool, info) -> bool:
        """Validate disk_valid matches disk requirement."""
        if hasattr(info, 'data') and 'available_disk' in info.data:
            disk_gb = info.data['available_disk']
            is_valid = disk_gb >= 2
            if v != is_valid:
                raise ValueError(
                    f"disk_valid={v} doesn't match requirement check for {disk_gb}GB"
                )
        return v

    @field_validator('platform')
    @classmethod
    def validate_platform(cls, v: str) -> str:
        """Validate platform format."""
        if not v.strip():
            raise ValueError("platform cannot be empty")
        return v.lower()

    @field_validator('platform_supported')
    @classmethod
    def validate_platform_supported(cls, v: bool, info) -> bool:
        """Validate platform_supported matches supported platforms."""
        if hasattr(info, 'data') and 'platform' in info.data:
            platform = info.data['platform']
            supported_platforms = {"darwin", "linux", "windows"}
            is_supported = platform.lower() in supported_platforms
            if v != is_supported:
                raise ValueError(
                    f"platform_supported={v} doesn't match support check for platform '{platform}'"
                )
        return v

    @field_validator('uv_version')
    @classmethod
    def validate_uv_version(cls, v: str | None) -> str | None:
        """Validate UV version format if provided."""
        if v is not None:
            try:
                version.Version(v)
            except version.InvalidVersion:
                raise ValueError("uv_version must be a valid semantic version when provided")
        return v

    def is_system_ready(self) -> bool:
        """Check if all system requirements are met."""
        return (
            self.python_valid and
            self.memory_valid and
            self.disk_valid and
            self.platform_supported
        )

    def get_missing_requirements(self) -> list[str]:
        """Get list of missing requirements."""
        missing = []

        if not self.python_valid:
            missing.append(f"Python >= 3.13.0 required (current: {self.python_version})")

        if not self.memory_valid:
            missing.append(f"At least 4GB memory required (available: {self.available_memory}GB)")

        if not self.disk_valid:
            missing.append(f"At least 2GB disk space required (available: {self.available_disk}GB)")

        if not self.platform_supported:
            missing.append(f"Unsupported platform: {self.platform} (supported: darwin, linux, windows)")

        return missing
