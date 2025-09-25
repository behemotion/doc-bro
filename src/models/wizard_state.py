"""WizardState model for interactive CLI wizards."""

from typing import Dict, Any, List, Optional
from enum import Enum
from pydantic import ConfigDict, BaseModel, Field, field_validator


class WizardType(str, Enum):
    """Type of wizard being executed."""
    CREATE_PROJECT = "CREATE_PROJECT"
    CONFIGURE_SERVICE = "CONFIGURE_SERVICE"
    SETUP_ENVIRONMENT = "SETUP_ENVIRONMENT"
    IMPORT_DATA = "IMPORT_DATA"


class WizardStep(BaseModel):
    """Individual wizard step."""
    name: str
    prompt: str
    field_name: str
    required: bool = True
    default: Optional[Any] = None
    validator: Optional[str] = None  # Name of validation function
    help_text: Optional[str] = None


class WizardState(BaseModel):
    """State management for interactive CLI wizards."""

    wizard_type: WizardType
    current_step: int = Field(default=1, ge=1)
    total_steps: int = Field(ge=1)
    collected_inputs: Dict[str, Any] = Field(default_factory=dict)
    validation_errors: List[str] = Field(default_factory=list)
    can_proceed: bool = Field(default=True)
    can_go_back: bool = Field(default=False)
    completed: bool = Field(default=False)
    cancelled: bool = Field(default=False)
    steps: List[WizardStep] = Field(default_factory=list)

    @field_validator('current_step')
    @classmethod
    def validate_current_step(cls, v: int, info) -> int:
        """Validate that current_step <= total_steps."""
        if 'total_steps' in info.data and v > info.data['total_steps']:
            raise ValueError(f"Current step ({v}) cannot exceed total steps ({info.data['total_steps']})")
        return v

    def add_step(self, step: WizardStep) -> None:
        """Add a step to the wizard.

        Args:
            step: Step to add
        """
        self.steps.append(step)
        self.total_steps = len(self.steps)

    def get_current_step(self) -> Optional[WizardStep]:
        """Get the current step.

        Returns:
            Current step or None if invalid
        """
        if 0 < self.current_step <= len(self.steps):
            return self.steps[self.current_step - 1]
        return None

    def collect_input(self, value: Any) -> None:
        """Collect input for current step.

        Args:
            value: Input value to collect
        """
        current = self.get_current_step()
        if current:
            self.collected_inputs[current.field_name] = value

    def advance_step(self) -> bool:
        """Move to next step.

        Returns:
            True if advanced, False if at end
        """
        if self.current_step < self.total_steps:
            self.current_step += 1
            self.can_go_back = True
            return True
        else:
            self.completed = True
            return False

    def go_back(self) -> bool:
        """Move to previous step.

        Returns:
            True if moved back, False if at beginning
        """
        if self.current_step > 1:
            self.current_step -= 1
            self.can_go_back = self.current_step > 1
            return True
        return False

    def add_validation_error(self, error: str) -> None:
        """Add a validation error.

        Args:
            error: Error message
        """
        self.validation_errors.append(error)
        self.can_proceed = False

    def clear_validation_errors(self) -> None:
        """Clear all validation errors."""
        self.validation_errors.clear()
        self.can_proceed = True

    def cancel(self) -> None:
        """Cancel the wizard."""
        self.cancelled = True
        self.can_proceed = False

    def reset(self) -> None:
        """Reset wizard to initial state."""
        self.current_step = 1
        self.collected_inputs.clear()
        self.validation_errors.clear()
        self.can_proceed = True
        self.can_go_back = False
        self.completed = False
        self.cancelled = False

    def get_progress(self) -> float:
        """Get completion progress as percentage.

        Returns:
            Progress (0-100)
        """
        if self.total_steps == 0:
            return 0.0
        return (self.current_step / self.total_steps) * 100

    def get_progress_text(self) -> str:
        """Get progress as text.

        Returns:
            Progress text like "Step 2/5"
        """
        return f"Step {self.current_step}/{self.total_steps}"

    def validate_current_input(self, value: Any) -> bool:
        """Validate input for current step.

        Args:
            value: Value to validate

        Returns:
            True if valid
        """
        current = self.get_current_step()
        if not current:
            return False

        # Check required
        if current.required and not value:
            self.add_validation_error(f"{current.name} is required")
            return False

        # Run custom validator if specified
        if current.validator:
            # This would call the actual validator function
            # For now, just return True
            pass

        self.clear_validation_errors()
        return True

    def get_summary(self) -> dict:
        """Get summary of collected inputs.

        Returns:
            Summary dictionary
        """
        summary = {
            "wizard_type": self.wizard_type.value,
            "completed": self.completed,
            "cancelled": self.cancelled,
            "progress": f"{self.get_progress():.0f}%",
            "inputs": self.collected_inputs
        }

        if self.validation_errors:
            summary["errors"] = self.validation_errors

        return summary

    def is_complete(self) -> bool:
        """Check if wizard is complete.

        Returns:
            True if all steps completed
        """
        return self.completed and not self.cancelled

    model_config = ConfigDict(
        use_enum_values = False
    )