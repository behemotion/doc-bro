"""Contract tests for WizardStep model validation."""

import pytest
from typing import List, Optional

# Import will fail until model is implemented - this is expected for TDD
try:
    from src.models.wizard_step import WizardStep
    MODEL_EXISTS = True
except ImportError:
    MODEL_EXISTS = False


@pytest.mark.contract
class TestWizardStepModel:
    """Test WizardStep model contracts."""

    @pytest.mark.skipif(not MODEL_EXISTS, reason="WizardStep model not yet implemented")
    def test_wizard_step_creation_choice_input(self):
        """Test WizardStep creation with choice input type."""
        step = WizardStep(
            step_number=1,
            wizard_type="shelf",
            step_title="Default Box Type",
            prompt_text="Choose default box type for new boxes:",
            input_type="choice",
            choices=["drag", "rag", "bag"],
            validation_rules=["required"],
            is_optional=False,
            depends_on=None
        )

        assert step.step_number == 1
        assert step.wizard_type == "shelf"
        assert step.step_title == "Default Box Type"
        assert step.prompt_text == "Choose default box type for new boxes:"
        assert step.input_type == "choice"
        assert step.choices == ["drag", "rag", "bag"]
        assert step.validation_rules == ["required"]
        assert step.is_optional is False
        assert step.depends_on is None

    @pytest.mark.skipif(not MODEL_EXISTS, reason="WizardStep model not yet implemented")
    def test_wizard_step_creation_text_input(self):
        """Test WizardStep creation with text input type."""
        step = WizardStep(
            step_number=2,
            wizard_type="box",
            step_title="Description",
            prompt_text="Enter box description (optional):",
            input_type="text",
            choices=None,
            validation_rules=["max_length:500"],
            is_optional=True,
            depends_on=None
        )

        assert step.step_number == 2
        assert step.wizard_type == "box"
        assert step.step_title == "Description"
        assert step.prompt_text == "Enter box description (optional):"
        assert step.input_type == "text"
        assert step.choices is None
        assert step.validation_rules == ["max_length:500"]
        assert step.is_optional is True
        assert step.depends_on is None

    @pytest.mark.skipif(not MODEL_EXISTS, reason="WizardStep model not yet implemented")
    def test_wizard_step_creation_boolean_input(self):
        """Test WizardStep creation with boolean input type."""
        step = WizardStep(
            step_number=3,
            wizard_type="mcp",
            step_title="Enable Admin Server",
            prompt_text="Enable admin server for management operations?",
            input_type="boolean",
            choices=["yes", "no"],
            validation_rules=[],
            is_optional=False,
            depends_on=None
        )

        assert step.step_number == 3
        assert step.wizard_type == "mcp"
        assert step.step_title == "Enable Admin Server"
        assert step.prompt_text == "Enable admin server for management operations?"
        assert step.input_type == "boolean"
        assert step.choices == ["yes", "no"]
        assert step.validation_rules == []
        assert step.is_optional is False
        assert step.depends_on is None

    @pytest.mark.skipif(not MODEL_EXISTS, reason="WizardStep model not yet implemented")
    def test_wizard_step_creation_file_path_input(self):
        """Test WizardStep creation with file_path input type."""
        step = WizardStep(
            step_number=4,
            wizard_type="box",
            step_title="Initial Source",
            prompt_text="Provide initial file path to upload:",
            input_type="file_path",
            choices=None,
            validation_rules=["file_exists", "readable"],
            is_optional=True,
            depends_on="description_complete"
        )

        assert step.step_number == 4
        assert step.wizard_type == "box"
        assert step.step_title == "Initial Source"
        assert step.prompt_text == "Provide initial file path to upload:"
        assert step.input_type == "file_path"
        assert step.choices is None
        assert step.validation_rules == ["file_exists", "readable"]
        assert step.is_optional is True
        assert step.depends_on == "description_complete"

    @pytest.mark.skipif(not MODEL_EXISTS, reason="WizardStep model not yet implemented")
    def test_wizard_step_creation_url_input(self):
        """Test WizardStep creation with url input type."""
        step = WizardStep(
            step_number=5,
            wizard_type="box",
            step_title="Website URL",
            prompt_text="Enter website URL to crawl:",
            input_type="url",
            choices=None,
            validation_rules=["valid_url", "http_or_https"],
            is_optional=False,
            depends_on=None
        )

        assert step.step_number == 5
        assert step.wizard_type == "box"
        assert step.step_title == "Website URL"
        assert step.prompt_text == "Enter website URL to crawl:"
        assert step.input_type == "url"
        assert step.choices is None
        assert step.validation_rules == ["valid_url", "http_or_https"]
        assert step.is_optional is False
        assert step.depends_on is None

    @pytest.mark.skipif(not MODEL_EXISTS, reason="WizardStep model not yet implemented")
    def test_wizard_step_number_validation(self):
        """Test step_number must be positive integer."""
        # Valid step numbers
        for step_number in [1, 2, 5, 10, 100]:
            step = WizardStep(
                step_number=step_number,
                wizard_type="shelf",
                step_title="Test Step",
                prompt_text="Test prompt",
                input_type="text",
                choices=None,
                validation_rules=[],
                is_optional=True,
                depends_on=None
            )
            assert step.step_number == step_number

        # Invalid step numbers should raise validation error
        for step_number in [0, -1, -5]:
            with pytest.raises(ValueError, match="step_number must be positive integer"):
                WizardStep(
                    step_number=step_number,
                    wizard_type="shelf",
                    step_title="Test Step",
                    prompt_text="Test prompt",
                    input_type="text",
                    choices=None,
                    validation_rules=[],
                    is_optional=True,
                    depends_on=None
                )

    @pytest.mark.skipif(not MODEL_EXISTS, reason="WizardStep model not yet implemented")
    def test_wizard_step_wizard_type_validation(self):
        """Test wizard_type validation."""
        # Valid wizard types
        for wizard_type in ["shelf", "box", "mcp"]:
            step = WizardStep(
                step_number=1,
                wizard_type=wizard_type,
                step_title="Test Step",
                prompt_text="Test prompt",
                input_type="text",
                choices=None,
                validation_rules=[],
                is_optional=True,
                depends_on=None
            )
            assert step.wizard_type == wizard_type

        # Invalid wizard type should raise validation error
        with pytest.raises(ValueError):
            WizardStep(
                step_number=1,
                wizard_type="invalid",
                step_title="Test Step",
                prompt_text="Test prompt",
                input_type="text",
                choices=None,
                validation_rules=[],
                is_optional=True,
                depends_on=None
            )

    @pytest.mark.skipif(not MODEL_EXISTS, reason="WizardStep model not yet implemented")
    def test_wizard_step_input_type_validation(self):
        """Test input_type validation."""
        # Valid input types
        for input_type in ["choice", "text", "boolean", "file_path", "url"]:
            step = WizardStep(
                step_number=1,
                wizard_type="shelf",
                step_title="Test Step",
                prompt_text="Test prompt",
                input_type=input_type,
                choices=["a", "b"] if input_type == "choice" else None,
                validation_rules=[],
                is_optional=True,
                depends_on=None
            )
            assert step.input_type == input_type

        # Invalid input type should raise validation error
        with pytest.raises(ValueError):
            WizardStep(
                step_number=1,
                wizard_type="shelf",
                step_title="Test Step",
                prompt_text="Test prompt",
                input_type="invalid",
                choices=None,
                validation_rules=[],
                is_optional=True,
                depends_on=None
            )

    @pytest.mark.skipif(not MODEL_EXISTS, reason="WizardStep model not yet implemented")
    def test_wizard_step_choices_validation(self):
        """Test choices validation for choice input type."""
        # Choice input must have choices
        step = WizardStep(
            step_number=1,
            wizard_type="shelf",
            step_title="Choice Step",
            prompt_text="Select option:",
            input_type="choice",
            choices=["option1", "option2", "option3"],
            validation_rules=[],
            is_optional=False,
            depends_on=None
        )
        assert step.choices == ["option1", "option2", "option3"]

        # Choice input without choices should raise validation error
        with pytest.raises(ValueError, match="choices required when input_type='choice'"):
            WizardStep(
                step_number=1,
                wizard_type="shelf",
                step_title="Choice Step",
                prompt_text="Select option:",
                input_type="choice",
                choices=None,
                validation_rules=[],
                is_optional=False,
                depends_on=None
            )

        # Non-choice inputs should not have choices
        for input_type in ["text", "boolean", "file_path", "url"]:
            step = WizardStep(
                step_number=1,
                wizard_type="shelf",
                step_title="Test Step",
                prompt_text="Test prompt",
                input_type=input_type,
                choices=None,
                validation_rules=[],
                is_optional=True,
                depends_on=None
            )
            assert step.choices is None

    @pytest.mark.skipif(not MODEL_EXISTS, reason="WizardStep model not yet implemented")
    def test_wizard_step_depends_on_validation(self):
        """Test depends_on step reference validation."""
        # Step with valid dependency
        step = WizardStep(
            step_number=3,
            wizard_type="shelf",
            step_title="Dependent Step",
            prompt_text="This depends on previous step",
            input_type="text",
            choices=None,
            validation_rules=[],
            is_optional=False,
            depends_on="step_2_complete"
        )
        assert step.depends_on == "step_2_complete"

        # Step without dependency
        step = WizardStep(
            step_number=1,
            wizard_type="shelf",
            step_title="Independent Step",
            prompt_text="This has no dependencies",
            input_type="text",
            choices=None,
            validation_rules=[],
            is_optional=False,
            depends_on=None
        )
        assert step.depends_on is None

    @pytest.mark.skipif(not MODEL_EXISTS, reason="WizardStep model not yet implemented")
    def test_wizard_step_validation_rules(self):
        """Test validation_rules for different input types."""
        # Text input validation rules
        step = WizardStep(
            step_number=1,
            wizard_type="box",
            step_title="Description",
            prompt_text="Enter description:",
            input_type="text",
            choices=None,
            validation_rules=["max_length:500", "min_length:10", "no_special_chars"],
            is_optional=False,
            depends_on=None
        )
        assert "max_length:500" in step.validation_rules
        assert "min_length:10" in step.validation_rules
        assert "no_special_chars" in step.validation_rules

        # URL input validation rules
        step = WizardStep(
            step_number=2,
            wizard_type="box",
            step_title="Website URL",
            prompt_text="Enter URL:",
            input_type="url",
            choices=None,
            validation_rules=["valid_url", "http_or_https", "reachable"],
            is_optional=False,
            depends_on=None
        )
        assert "valid_url" in step.validation_rules
        assert "http_or_https" in step.validation_rules
        assert "reachable" in step.validation_rules

        # File path validation rules
        step = WizardStep(
            step_number=3,
            wizard_type="box",
            step_title="File Path",
            prompt_text="Enter file path:",
            input_type="file_path",
            choices=None,
            validation_rules=["file_exists", "readable", "supported_format"],
            is_optional=True,
            depends_on=None
        )
        assert "file_exists" in step.validation_rules
        assert "readable" in step.validation_rules
        assert "supported_format" in step.validation_rules

    @pytest.mark.skipif(not MODEL_EXISTS, reason="WizardStep model not yet implemented")
    def test_wizard_step_serialization(self):
        """Test WizardStep serialization to dict."""
        step = WizardStep(
            step_number=2,
            wizard_type="shelf",
            step_title="Auto-fill Setting",
            prompt_text="Auto-fill empty boxes when accessed?",
            input_type="boolean",
            choices=["yes", "no"],
            validation_rules=["required"],
            is_optional=False,
            depends_on=None
        )

        # Should be able to serialize to dict
        step_dict = step.model_dump()
        assert isinstance(step_dict, dict)
        assert step_dict["step_number"] == 2
        assert step_dict["wizard_type"] == "shelf"
        assert step_dict["step_title"] == "Auto-fill Setting"
        assert step_dict["prompt_text"] == "Auto-fill empty boxes when accessed?"
        assert step_dict["input_type"] == "boolean"
        assert step_dict["choices"] == ["yes", "no"]
        assert step_dict["validation_rules"] == ["required"]
        assert step_dict["is_optional"] is False
        assert step_dict["depends_on"] is None

    @pytest.mark.skipif(not MODEL_EXISTS, reason="WizardStep model not yet implemented")
    def test_wizard_step_deserialization(self):
        """Test WizardStep deserialization from dict."""
        step_data = {
            "step_number": 4,
            "wizard_type": "box",
            "step_title": "File Patterns",
            "prompt_text": "Enter file patterns (comma-separated):",
            "input_type": "text",
            "choices": None,
            "validation_rules": ["csv_format", "valid_patterns"],
            "is_optional": True,
            "depends_on": "type_selection"
        }

        step = WizardStep.model_validate(step_data)
        assert step.step_number == 4
        assert step.wizard_type == "box"
        assert step.step_title == "File Patterns"
        assert step.prompt_text == "Enter file patterns (comma-separated):"
        assert step.input_type == "text"
        assert step.choices is None
        assert step.validation_rules == ["csv_format", "valid_patterns"]
        assert step.is_optional is True
        assert step.depends_on == "type_selection"

    @pytest.mark.skipif(not MODEL_EXISTS, reason="WizardStep model not yet implemented")
    def test_wizard_step_uniqueness_within_wizard(self):
        """Test step_number uniqueness within wizard type."""
        # This test would be part of a wizard step collection/manager
        # For now, just test the model accepts unique step numbers
        steps = []

        for i in range(1, 6):
            step = WizardStep(
                step_number=i,
                wizard_type="shelf",
                step_title=f"Step {i}",
                prompt_text=f"Prompt for step {i}",
                input_type="text",
                choices=None,
                validation_rules=[],
                is_optional=True,
                depends_on=None
            )
            steps.append(step)

        # All step numbers should be unique
        step_numbers = [step.step_number for step in steps]
        assert len(step_numbers) == len(set(step_numbers))

        # Step numbers should be sequential
        assert step_numbers == [1, 2, 3, 4, 5]


if not MODEL_EXISTS:
    def test_wizard_step_model_not_implemented():
        """Test that fails until WizardStep model is implemented."""
        assert False, "WizardStep model not yet implemented - this test should fail until T027 is completed"