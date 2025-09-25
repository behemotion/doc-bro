"""Data model for critical decision points during installation."""

from datetime import datetime
from typing import Optional
import re

from pydantic import BaseModel, Field, field_validator, model_validator, ConfigDict


class CriticalDecisionPoint(BaseModel):
    """Model for tracking critical decisions during installation process.

    This model represents decision points that require user input during
    the installation process, such as choosing installation location,
    service ports, or data directories.
    """

    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        json_encoders={
            datetime: lambda v: v.isoformat()
        }
    )

    decision_id: str = Field(..., description="Unique decision identifier")
    prompt_text: str = Field(..., description="Text prompt shown to user")
    decision_type: str = Field(..., description="Type of decision being made")
    default_value: Optional[str] = Field(None, description="Default value for this decision")
    user_value: Optional[str] = Field(None, description="Value provided by user")
    required: bool = Field(default=True, description="Whether this decision is required")
    validation_pattern: Optional[str] = Field(None, description="Regex pattern for validating user input")
    created_at: datetime = Field(default_factory=datetime.now, description="When decision point was created")
    resolved_at: Optional[datetime] = Field(None, description="When decision was resolved")

    @field_validator('decision_type')
    @classmethod
    def validate_decision_type(cls, v: str) -> str:
        """Validate decision_type is one of allowed values."""
        allowed_types = {"install_location", "service_port", "data_directory"}
        if v not in allowed_types:
            raise ValueError(f"decision_type must be one of {allowed_types}")
        return v

    @field_validator('validation_pattern')
    @classmethod
    def validate_regex_pattern(cls, v: Optional[str]) -> Optional[str]:
        """Validate that the validation pattern is a valid regex."""
        if v is not None:
            try:
                re.compile(v)
            except re.error as e:
                raise ValueError(f"Invalid regex pattern: {e}")
        return v

    @model_validator(mode='after')
    def validate_user_value_against_pattern(self) -> 'CriticalDecisionPoint':
        """Validate user_value matches validation_pattern if both are provided."""
        if self.user_value is not None and self.validation_pattern is not None:
            try:
                if not re.match(self.validation_pattern, self.user_value):
                    raise ValueError(f"user_value '{self.user_value}' does not match validation pattern '{self.validation_pattern}'")
            except re.error as e:
                raise ValueError(f"Error validating user_value against pattern: {e}")
        return self

    @field_validator('decision_id')
    @classmethod
    def validate_decision_id_format(cls, v: str) -> str:
        """Validate decision_id format - alphanumeric with underscores/hyphens."""
        pattern = r"^[a-zA-Z0-9_-]+$"
        if not re.match(pattern, v):
            raise ValueError("decision_id must contain only alphanumeric characters, underscores, and hyphens")
        return v

    def validate_required(self) -> None:
        """Validate that required decisions have either user_value or default_value."""
        if self.required and not self.user_value and not self.default_value:
            raise ValueError(f"Required decision '{self.decision_id}' must have either user_value or default_value")

    def resolve(self, user_value: str) -> None:
        """Resolve this decision point with a user value."""
        # Validate against pattern if provided
        if self.validation_pattern:
            try:
                if not re.match(self.validation_pattern, user_value):
                    raise ValueError(f"Value '{user_value}' does not match validation pattern '{self.validation_pattern}'")
            except re.error as e:
                raise ValueError(f"Error validating value against pattern: {e}")

        self.user_value = user_value
        self.resolved_at = datetime.now()

    def is_resolved(self) -> bool:
        """Check if this decision point has been resolved."""
        return self.resolved_at is not None

    def get_effective_value(self) -> Optional[str]:
        """Get the effective value - user_value if provided, otherwise default_value.

        For required decisions, this will validate that a value is available.
        """
        if self.required and not self.user_value and not self.default_value:
            raise ValueError(f"Required decision '{self.decision_id}' must have either user_value or default_value")
        return self.user_value if self.user_value is not None else self.default_value