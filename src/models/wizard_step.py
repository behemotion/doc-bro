"""Wizard step model for defining interactive setup flows."""

from typing import List, Literal, Optional

from pydantic import BaseModel, Field, model_validator


class WizardStep(BaseModel):
    """Defines individual steps within interactive setup wizards."""

    step_number: int = Field(
        description="Order of this step in the wizard"
    )
    wizard_type: str = Field(
        description="Which wizard this step belongs to"
    )
    step_title: str = Field(
        description="Display title for the step"
    )
    prompt_text: str = Field(
        description="Question or instruction for the user"
    )
    input_type: Literal["choice", "text", "boolean", "file_path", "url"] = Field(
        description="Type of input expected"
    )
    choices: Optional[List[str]] = Field(
        default=None,
        description="Available options for choice input"
    )
    validation_rules: List[str] = Field(
        default_factory=list,
        description="Validation patterns or requirements"
    )
    is_optional: bool = Field(
        default=False,
        description="Whether user can skip this step"
    )
    depends_on: Optional[str] = Field(
        default=None,
        description="Previous step that must be completed first"
    )

    @model_validator(mode='after')
    def validate_wizard_step(self) -> 'WizardStep':
        """Validate wizard step logic."""
        # Validate step_number is positive
        if self.step_number <= 0:
            raise ValueError("step_number must be positive integer")

        # Validate wizard_type is supported
        if self.wizard_type not in ["shelf", "box", "mcp"]:
            raise ValueError("wizard_type must be one of: shelf, box, mcp")

        # Validate choices requirement for choice input type
        if self.input_type == "choice" and not self.choices:
            raise ValueError("choices required when input_type='choice'")

        # Validate non-choice inputs don't have choices
        if self.input_type != "choice" and self.choices:
            # Allow choices for boolean type as well (yes/no options)
            if self.input_type != "boolean":
                self.choices = None

        return self

    def format_prompt(self) -> str:
        """Format the prompt text with choices if applicable."""
        prompt = self.prompt_text

        if self.input_type == "choice" and self.choices:
            choice_lines = [f"  {i+1}) {choice}" for i, choice in enumerate(self.choices)]
            prompt += "\n" + "\n".join(choice_lines)

        if self.is_optional:
            prompt += " (optional)"

        return prompt

    def validate_response(self, response: str) -> tuple[bool, str]:
        """Validate user response against step requirements."""
        if not response.strip() and not self.is_optional:
            return False, "Response is required for this step"

        if self.input_type == "choice":
            if response not in self.choices:
                try:
                    # Allow numeric selection for choices
                    choice_index = int(response) - 1
                    if 0 <= choice_index < len(self.choices):
                        return True, self.choices[choice_index]
                except ValueError:
                    pass
                return False, f"Choice must be one of: {', '.join(self.choices)}"

        elif self.input_type == "boolean":
            lower_response = response.lower()
            if lower_response in ["y", "yes", "true", "1"]:
                return True, "true"
            elif lower_response in ["n", "no", "false", "0"]:
                return True, "false"
            else:
                return False, "Response must be yes/no or y/n"

        elif self.input_type == "url":
            if not response.startswith(("http://", "https://")):
                return False, "URL must start with http:// or https://"

        elif self.input_type == "file_path":
            # Basic file path validation
            if not response or response.isspace():
                return False, "File path cannot be empty"

        # Apply additional validation rules
        for rule in self.validation_rules:
            is_valid, error = self._apply_validation_rule(rule, response)
            if not is_valid:
                return False, error

        return True, response

    def _apply_validation_rule(self, rule: str, value: str) -> tuple[bool, str]:
        """Apply a specific validation rule to a value."""
        if rule.startswith("max_length:"):
            try:
                max_len = int(rule.split(":")[1])
                if len(value) > max_len:
                    return False, f"Value must be {max_len} characters or less"
            except (ValueError, IndexError):
                pass

        elif rule.startswith("min_length:"):
            try:
                min_len = int(rule.split(":")[1])
                if len(value) < min_len:
                    return False, f"Value must be at least {min_len} characters"
            except (ValueError, IndexError):
                pass

        elif rule == "required" and not value.strip():
            return False, "This field is required"

        elif rule == "no_special_chars":
            if not value.replace("-", "").replace("_", "").replace(" ", "").isalnum():
                return False, "Value contains invalid characters"

        elif rule == "valid_url":
            import re
            url_pattern = r'^https?://[^\s/$.?#].[^\s]*$'
            if not re.match(url_pattern, value):
                return False, "Invalid URL format"

        elif rule == "csv_format":
            # Allow comma-separated values
            pass  # Any string is valid for CSV

        return True, ""

    model_config = {}