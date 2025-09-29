"""Contract tests for FlagDefinition model validation."""

import pytest
from typing import Any, List, Optional

# Import will fail until model is implemented - this is expected for TDD
try:
    from src.models.flag_definition import FlagDefinition
    MODEL_EXISTS = True
except ImportError:
    MODEL_EXISTS = False


@pytest.mark.contract
class TestFlagDefinitionModel:
    """Test FlagDefinition model contracts."""

    @pytest.mark.skipif(not MODEL_EXISTS, reason="FlagDefinition model not yet implemented")
    def test_flag_definition_creation_boolean(self):
        """Test FlagDefinition creation for boolean flag."""
        flag_def = FlagDefinition(
            long_form="--verbose",
            short_form="-v",
            flag_type="boolean",
            description="Enable verbose output",
            choices=None,
            default_value=False,
            is_global=True
        )

        assert flag_def.long_form == "--verbose"
        assert flag_def.short_form == "-v"
        assert flag_def.flag_type == "boolean"
        assert flag_def.description == "Enable verbose output"
        assert flag_def.choices is None
        assert flag_def.default_value is False
        assert flag_def.is_global is True

    @pytest.mark.skipif(not MODEL_EXISTS, reason="FlagDefinition model not yet implemented")
    def test_flag_definition_creation_choice(self):
        """Test FlagDefinition creation for choice flag."""
        flag_def = FlagDefinition(
            long_form="--format",
            short_form="-f",
            flag_type="choice",
            description="Output format",
            choices=["json", "yaml", "table"],
            default_value="table",
            is_global=True
        )

        assert flag_def.long_form == "--format"
        assert flag_def.short_form == "-f"
        assert flag_def.flag_type == "choice"
        assert flag_def.description == "Output format"
        assert flag_def.choices == ["json", "yaml", "table"]
        assert flag_def.default_value == "table"
        assert flag_def.is_global is True

    @pytest.mark.skipif(not MODEL_EXISTS, reason="FlagDefinition model not yet implemented")
    def test_flag_definition_creation_string(self):
        """Test FlagDefinition creation for string flag."""
        flag_def = FlagDefinition(
            long_form="--config",
            short_form="-c",
            flag_type="string",
            description="Configuration file path",
            choices=None,
            default_value=None,
            is_global=True
        )

        assert flag_def.long_form == "--config"
        assert flag_def.short_form == "-c"
        assert flag_def.flag_type == "string"
        assert flag_def.description == "Configuration file path"
        assert flag_def.choices is None
        assert flag_def.default_value is None
        assert flag_def.is_global is True

    @pytest.mark.skipif(not MODEL_EXISTS, reason="FlagDefinition model not yet implemented")
    def test_flag_definition_creation_integer(self):
        """Test FlagDefinition creation for integer flag."""
        flag_def = FlagDefinition(
            long_form="--depth",
            short_form="-d",
            flag_type="integer",
            description="Maximum crawl depth",
            choices=None,
            default_value=3,
            is_global=False
        )

        assert flag_def.long_form == "--depth"
        assert flag_def.short_form == "-d"
        assert flag_def.flag_type == "integer"
        assert flag_def.description == "Maximum crawl depth"
        assert flag_def.choices is None
        assert flag_def.default_value == 3
        assert flag_def.is_global is False

    @pytest.mark.skipif(not MODEL_EXISTS, reason="FlagDefinition model not yet implemented")
    def test_flag_definition_long_form_validation(self):
        """Test long_form validation rules."""
        # Valid long forms
        valid_long_forms = ["--init", "--verbose", "--max-pages", "--chunk-size", "--rate-limit"]
        for long_form in valid_long_forms:
            flag_def = FlagDefinition(
                long_form=long_form,
                short_form="-i",
                flag_type="boolean",
                description="Test flag",
                choices=None,
                default_value=False,
                is_global=True
            )
            assert flag_def.long_form == long_form

        # Invalid long forms should raise validation error
        invalid_long_forms = ["init", "-init", "verbose", "--", "--init_flag", "--init flag", "--INIT"]
        for long_form in invalid_long_forms:
            with pytest.raises(ValueError, match="long_form must start with '--' and be kebab-case"):
                FlagDefinition(
                    long_form=long_form,
                    short_form="-i",
                    flag_type="boolean",
                    description="Test flag",
                    choices=None,
                    default_value=False,
                    is_global=True
                )

    @pytest.mark.skipif(not MODEL_EXISTS, reason="FlagDefinition model not yet implemented")
    def test_flag_definition_short_form_validation(self):
        """Test short_form validation rules."""
        # Valid short forms
        valid_short_forms = ["-i", "-v", "-h", "-f", "-d", "-R", "-C"]
        for short_form in valid_short_forms:
            flag_def = FlagDefinition(
                long_form="--init",
                short_form=short_form,
                flag_type="boolean",
                description="Test flag",
                choices=None,
                default_value=False,
                is_global=True
            )
            assert flag_def.short_form == short_form

        # Invalid short forms should raise validation error
        invalid_short_forms = ["i", "v", "--i", "-init", "-", "-12", "-iv", ""]
        for short_form in invalid_short_forms:
            with pytest.raises(ValueError, match="short_form must be single letter with '-' prefix"):
                FlagDefinition(
                    long_form="--init",
                    short_form=short_form,
                    flag_type="boolean",
                    description="Test flag",
                    choices=None,
                    default_value=False,
                    is_global=True
                )

    @pytest.mark.skipif(not MODEL_EXISTS, reason="FlagDefinition model not yet implemented")
    def test_flag_definition_flag_type_validation(self):
        """Test flag_type validation."""
        # Valid flag types
        for flag_type in ["boolean", "string", "integer", "choice"]:
            flag_def = FlagDefinition(
                long_form="--test",
                short_form="-t",
                flag_type=flag_type,
                description="Test flag",
                choices=["a", "b"] if flag_type == "choice" else None,
                default_value=False if flag_type == "boolean" else "default",
                is_global=True
            )
            assert flag_def.flag_type == flag_type

        # Invalid flag type should raise validation error
        with pytest.raises(ValueError):
            FlagDefinition(
                long_form="--test",
                short_form="-t",
                flag_type="invalid",
                description="Test flag",
                choices=None,
                default_value=None,
                is_global=True
            )

    @pytest.mark.skipif(not MODEL_EXISTS, reason="FlagDefinition model not yet implemented")
    def test_flag_definition_choices_validation(self):
        """Test choices validation for choice type flags."""
        # Choice type must have choices
        flag_def = FlagDefinition(
            long_form="--format",
            short_form="-f",
            flag_type="choice",
            description="Output format",
            choices=["json", "yaml", "table"],
            default_value="json",
            is_global=True
        )
        assert flag_def.choices == ["json", "yaml", "table"]

        # Choice type without choices should raise validation error
        with pytest.raises(ValueError, match="choices required when flag_type='choice'"):
            FlagDefinition(
                long_form="--format",
                short_form="-f",
                flag_type="choice",
                description="Output format",
                choices=None,
                default_value="json",
                is_global=True
            )

        # Non-choice types should not have choices
        for flag_type in ["boolean", "string", "integer"]:
            flag_def = FlagDefinition(
                long_form="--test",
                short_form="-t",
                flag_type=flag_type,
                description="Test flag",
                choices=None,
                default_value=False if flag_type == "boolean" else "default",
                is_global=True
            )
            assert flag_def.choices is None

    @pytest.mark.skipif(not MODEL_EXISTS, reason="FlagDefinition model not yet implemented")
    def test_flag_definition_default_value_type_validation(self):
        """Test default_value type matches flag_type."""
        # Boolean flag with boolean default
        flag_def = FlagDefinition(
            long_form="--verbose",
            short_form="-v",
            flag_type="boolean",
            description="Enable verbose output",
            choices=None,
            default_value=True,
            is_global=True
        )
        assert flag_def.default_value is True

        # String flag with string default
        flag_def = FlagDefinition(
            long_form="--config",
            short_form="-c",
            flag_type="string",
            description="Config file",
            choices=None,
            default_value="/path/to/config",
            is_global=True
        )
        assert flag_def.default_value == "/path/to/config"

        # Integer flag with integer default
        flag_def = FlagDefinition(
            long_form="--depth",
            short_form="-d",
            flag_type="integer",
            description="Crawl depth",
            choices=None,
            default_value=5,
            is_global=False
        )
        assert flag_def.default_value == 5

        # Choice flag with valid choice default
        flag_def = FlagDefinition(
            long_form="--format",
            short_form="-f",
            flag_type="choice",
            description="Output format",
            choices=["json", "yaml"],
            default_value="yaml",
            is_global=True
        )
        assert flag_def.default_value == "yaml"

        # Choice flag with invalid choice default should raise validation error
        with pytest.raises(ValueError, match="default_value must be one of choices"):
            FlagDefinition(
                long_form="--format",
                short_form="-f",
                flag_type="choice",
                description="Output format",
                choices=["json", "yaml"],
                default_value="invalid",
                is_global=True
            )

    @pytest.mark.skipif(not MODEL_EXISTS, reason="FlagDefinition model not yet implemented")
    def test_flag_definition_serialization(self):
        """Test FlagDefinition serialization to dict."""
        flag_def = FlagDefinition(
            long_form="--verbose",
            short_form="-v",
            flag_type="boolean",
            description="Enable verbose output",
            choices=None,
            default_value=False,
            is_global=True
        )

        # Should be able to serialize to dict
        flag_dict = flag_def.model_dump()
        assert isinstance(flag_dict, dict)
        assert flag_dict["long_form"] == "--verbose"
        assert flag_dict["short_form"] == "-v"
        assert flag_dict["flag_type"] == "boolean"
        assert flag_dict["description"] == "Enable verbose output"
        assert flag_dict["choices"] is None
        assert flag_dict["default_value"] is False
        assert flag_dict["is_global"] is True

    @pytest.mark.skipif(not MODEL_EXISTS, reason="FlagDefinition model not yet implemented")
    def test_flag_definition_deserialization(self):
        """Test FlagDefinition deserialization from dict."""
        flag_data = {
            "long_form": "--format",
            "short_form": "-f",
            "flag_type": "choice",
            "description": "Output format",
            "choices": ["json", "yaml", "table"],
            "default_value": "table",
            "is_global": True
        }

        flag_def = FlagDefinition.model_validate(flag_data)
        assert flag_def.long_form == "--format"
        assert flag_def.short_form == "-f"
        assert flag_def.flag_type == "choice"
        assert flag_def.description == "Output format"
        assert flag_def.choices == ["json", "yaml", "table"]
        assert flag_def.default_value == "table"
        assert flag_def.is_global is True

    @pytest.mark.skipif(not MODEL_EXISTS, reason="FlagDefinition model not yet implemented")
    def test_flag_definition_help_text_generation(self):
        """Test help text generation for CLI usage."""
        # Boolean flag
        flag_def = FlagDefinition(
            long_form="--verbose",
            short_form="-v",
            flag_type="boolean",
            description="Enable verbose output",
            choices=None,
            default_value=False,
            is_global=True
        )

        help_text = flag_def.generate_help_text()
        assert "--verbose, -v" in help_text
        assert "Enable verbose output" in help_text
        assert "default: False" in help_text

        # Choice flag
        flag_def = FlagDefinition(
            long_form="--format",
            short_form="-f",
            flag_type="choice",
            description="Output format",
            choices=["json", "yaml", "table"],
            default_value="table",
            is_global=True
        )

        help_text = flag_def.generate_help_text()
        assert "--format, -f" in help_text
        assert "Output format" in help_text
        assert "choices: json, yaml, table" in help_text
        assert "default: table" in help_text


if not MODEL_EXISTS:
    def test_flag_definition_model_not_implemented():
        """Test that fails until FlagDefinition model is implemented."""
        assert False, "FlagDefinition model not yet implemented - this test should fail until T026 is completed"