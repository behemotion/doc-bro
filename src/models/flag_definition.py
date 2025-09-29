"""Flag definition model for standardized CLI flags."""

import re
from typing import Any, List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class FlagDefinition(BaseModel):
    """Defines standard flag patterns and aliases for command consistency."""

    long_form: str = Field(
        description="Primary flag name (e.g., '--init')"
    )
    short_form: str = Field(
        description="Single-letter alias (e.g., '-i')"
    )
    flag_type: Literal["boolean", "string", "integer", "choice"] = Field(
        description="Data type of the flag"
    )
    description: str = Field(
        description="Help text for the flag"
    )
    choices: Optional[List[str]] = Field(
        default=None,
        description="Valid options for choice-type flags"
    )
    default_value: Optional[Any] = Field(
        default=None,
        description="Default value when flag not provided"
    )
    is_global: bool = Field(
        default=False,
        description="Whether flag applies to all commands"
    )

    @model_validator(mode='after')
    def validate_flag_definition(self) -> 'FlagDefinition':
        """Validate flag definition logic."""
        # Validate long_form format
        if not self._is_valid_long_form(self.long_form):
            raise ValueError("long_form must start with '--' and be kebab-case")

        # Validate short_form format
        if not self._is_valid_short_form(self.short_form):
            raise ValueError("short_form must be single letter with '-' prefix")

        # Validate choices requirement for choice type
        if self.flag_type == "choice" and not self.choices:
            raise ValueError("choices required when flag_type='choice'")

        # Validate default_value type matches flag_type
        self._validate_default_value()

        return self

    def _is_valid_long_form(self, long_form: str) -> bool:
        """Check if long_form follows the correct format."""
        # Must start with -- and be kebab-case (lowercase with hyphens)
        pattern = r'^--[a-z][a-z0-9-]*$'
        return bool(re.match(pattern, long_form))

    def _is_valid_short_form(self, short_form: str) -> bool:
        """Check if short_form follows the correct format."""
        # Must be -X where X is a single letter (any case)
        pattern = r'^-[a-zA-Z]$'
        return bool(re.match(pattern, short_form))

    def _validate_default_value(self) -> None:
        """Validate default_value type matches flag_type."""
        if self.default_value is None:
            return

        type_map = {
            "boolean": bool,
            "string": str,
            "integer": int,
            "choice": str
        }

        expected_type = type_map.get(self.flag_type)
        if expected_type and not isinstance(self.default_value, expected_type):
            raise ValueError(f"default_value type must match flag_type")

        # For choice type, validate default_value is in choices
        if self.flag_type == "choice" and self.choices:
            if self.default_value not in self.choices:
                raise ValueError("default_value must be one of choices")

    def generate_help_text(self) -> str:
        """Generate formatted help text for CLI usage."""
        help_parts = [f"{self.long_form}, {self.short_form}"]
        help_parts.append(f"  {self.description}")

        if self.flag_type == "choice" and self.choices:
            choices_str = ", ".join(self.choices)
            help_parts.append(f"  choices: {choices_str}")

        if self.default_value is not None:
            help_parts.append(f"  default: {self.default_value}")

        return "\n".join(help_parts)

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            # Encode choices list as JSON string for database storage
            list: lambda v: v if isinstance(v, list) else None
        }