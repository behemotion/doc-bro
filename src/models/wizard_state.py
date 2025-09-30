"""Wizard state model for tracking interactive setup sessions."""

import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Literal

from pydantic import BaseModel, Field, model_validator


class WizardState(BaseModel):
    """Tracks the current state and progress of interactive setup wizards."""

    wizard_id: str = Field(
        description="Unique identifier for the wizard session"
    )
    wizard_type: Literal["shelf", "box", "mcp"] = Field(
        description="Type of wizard being run"
    )
    target_entity: str = Field(
        description="Name of the entity being configured"
    )
    current_step: int = Field(
        description="Current step number in the wizard flow"
    )
    total_steps: int = Field(
        description="Total number of steps in this wizard"
    )
    collected_data: Dict[str, Any] = Field(
        description="User responses collected so far"
    )
    start_time: datetime = Field(
        description="When the wizard session started"
    )
    last_activity: datetime = Field(
        description="Last user interaction timestamp"
    )
    is_complete: bool = Field(
        default=False,
        description="Whether wizard has finished successfully"
    )

    @model_validator(mode='after')
    def validate_wizard_state(self) -> 'WizardState':
        """Validate wizard state logic."""
        # Validate wizard_id is UUID format
        try:
            uuid.UUID(self.wizard_id)
        except ValueError:
            raise ValueError("wizard_id must be UUID format")

        # Validate step numbers
        if self.current_step <= 0 or self.total_steps <= 0:
            raise ValueError("step numbers must be positive integers")

        if self.current_step > self.total_steps:
            raise ValueError("current_step must be <= total_steps")

        # Validate collected_data against wizard type schema
        self._validate_collected_data()

        return self

    def _validate_collected_data(self) -> None:
        """Validate collected_data against wizard type schema."""
        # Define valid fields for each wizard type
        schema_map = {
            "shelf": {
                "description": str,
                "auto_fill": bool,
                "default_box_type": str,
                "tags": list
            },
            "box": {
                "box_type": str,
                "description": str,
                "auto_process": bool,
                "file_patterns": list
            },
            "mcp": {
                "enable_read_only": bool,
                "read_only_port": int,
                "enable_admin": bool,
                "admin_port": int
            }
        }

        expected_schema = schema_map.get(self.wizard_type, {})

        # Validate each field in collected_data matches expected types
        for key, value in self.collected_data.items():
            if key in expected_schema:
                expected_type = expected_schema[key]
                if not isinstance(value, expected_type):
                    raise ValueError(f"collected_data[{key}] must be {expected_type.__name__}")

        # Validate specific constraints
        if self.wizard_type == "box" and "box_type" in self.collected_data:
            if self.collected_data["box_type"] not in ["drag", "rag", "bag"]:
                raise ValueError("box_type must be one of: drag, rag, bag")

        if self.wizard_type == "shelf" and "default_box_type" in self.collected_data:
            if self.collected_data["default_box_type"] not in ["drag", "rag", "bag"]:
                raise ValueError("default_box_type must be one of: drag, rag, bag")

    def is_expired(self) -> bool:
        """Check if wizard session has expired (>30 minutes of inactivity)."""
        if self.is_complete:
            return False

        # Session expires after 30 minutes of inactivity
        expiry_time = self.last_activity + timedelta(minutes=30)
        return datetime.now(timezone.utc) > expiry_time

    def update_activity(self) -> None:
        """Update last activity timestamp to current time."""
        self.last_activity = datetime.now(timezone.utc)

    def advance_step(self) -> bool:
        """Advance to next step if not at end."""
        if self.current_step < self.total_steps:
            self.current_step += 1
            self.update_activity()
            return True
        return False

    def complete_wizard(self) -> None:
        """Mark wizard as completed."""
        self.is_complete = True
        self.update_activity()

    model_config = {}