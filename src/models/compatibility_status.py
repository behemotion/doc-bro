"""Compatibility status enumeration for unified project schema."""

from enum import Enum


class CompatibilityStatus(Enum):
    """Project compatibility with current schema version."""

    COMPATIBLE = "compatible"       # Current schema version, full functionality
    INCOMPATIBLE = "incompatible"   # Old schema, needs recreation for modification
    MIGRATING = "migrating"         # In process of recreation/migration

    def __str__(self) -> str:
        """String representation using the enum value."""
        return self.value

    @classmethod
    def from_schema_version(cls, schema_version: int, current_version: int = 3) -> "CompatibilityStatus":
        """Determine compatibility status from schema version."""
        if schema_version == current_version:
            return cls.COMPATIBLE
        elif schema_version < current_version:
            return cls.INCOMPATIBLE
        else:
            # Future schema version - treat as incompatible for safety
            return cls.INCOMPATIBLE

    @property
    def allows_modification(self) -> bool:
        """Whether this status allows project modifications."""
        return self == CompatibilityStatus.COMPATIBLE

    @property
    def needs_recreation(self) -> bool:
        """Whether this status requires project recreation."""
        return self == CompatibilityStatus.INCOMPATIBLE

    @property
    def is_transitional(self) -> bool:
        """Whether this status represents a temporary migration state."""
        return self == CompatibilityStatus.MIGRATING