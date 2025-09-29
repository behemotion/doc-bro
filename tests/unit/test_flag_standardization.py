"""Unit tests for flag standardization logic (T056)."""

import pytest
from src.services.flag_standardizer import FlagStandardizer, FlagMapping


pytestmark = pytest.mark.unit


class TestFlagStandardization:
    """Test flag standardization service."""

    @pytest.fixture
    def standardizer(self):
        """Create FlagStandardizer instance for testing."""
        return FlagStandardizer()

    def test_global_flags_initialized(self, standardizer):
        """Test that global flags are properly initialized."""
        global_flags = standardizer.get_global_flags()

        # Verify expected global flags exist
        assert "help" in global_flags
        assert "verbose" in global_flags
        assert "quiet" in global_flags
        assert "init" in global_flags
        assert "force" in global_flags

    def test_global_flag_structure(self, standardizer):
        """Test that global flags have correct structure."""
        global_flags = standardizer.get_global_flags()

        for flag_name, flag_mapping in global_flags.items():
            assert isinstance(flag_mapping, FlagMapping)
            assert flag_mapping.long_form.startswith("--")
            assert flag_mapping.short_form.startswith("-")
            assert len(flag_mapping.short_form) == 2  # "-" + single letter
            assert flag_mapping.is_global is True

    def test_command_specific_flags_shelf(self, standardizer):
        """Test shelf command specific flags."""
        shelf_flags = standardizer.get_command_flags("shelf")

        assert "description" in shelf_flags
        assert "set_current" in shelf_flags
        assert "create" in shelf_flags

        # Verify shelf description uses -d
        assert shelf_flags["description"].short_form == "-d"

    def test_command_specific_flags_box(self, standardizer):
        """Test box command specific flags."""
        box_flags = standardizer.get_command_flags("box")

        assert "type" in box_flags
        assert "shelf" in box_flags
        assert "description" in box_flags

        # Verify box type uses -T
        assert box_flags["type"].short_form == "-T"
        # Verify box shelf uses -B
        assert box_flags["shelf"].short_form == "-B"

    def test_command_specific_flags_fill(self, standardizer):
        """Test fill command specific flags."""
        fill_flags = standardizer.get_command_flags("fill")

        assert "source" in fill_flags
        assert "max_pages" in fill_flags
        assert "rate_limit" in fill_flags
        assert "depth" in fill_flags
        assert "chunk_size" in fill_flags
        assert "overlap" in fill_flags
        assert "recursive" in fill_flags
        assert "pattern" in fill_flags

        # Verify fill source uses -S (capital to avoid conflict)
        assert fill_flags["source"].short_form == "-S"
        # Verify fill recursive uses -x (not -r)
        assert fill_flags["recursive"].short_form == "-x"

    def test_command_specific_flags_serve(self, standardizer):
        """Test serve command specific flags."""
        serve_flags = standardizer.get_command_flags("serve")

        assert "host" in serve_flags
        assert "port" in serve_flags
        assert "admin" in serve_flags
        assert "foreground" in serve_flags

        # Verify serve host uses -H (capital to avoid conflict with --help)
        assert serve_flags["host"].short_form == "-H"
        # Verify serve admin uses -A
        assert serve_flags["admin"].short_form == "-A"

    def test_no_short_form_conflicts_global(self, standardizer):
        """Test that global flags have no short form conflicts."""
        global_flags = standardizer.get_global_flags()

        short_forms = [flag.short_form for flag in global_flags.values()]

        # Verify no duplicates
        assert len(short_forms) == len(set(short_forms)), "Duplicate short forms found in global flags"

    def test_no_short_form_conflicts_within_command(self, standardizer):
        """Test that each command has no internal short form conflicts."""
        commands = ["shelf", "box", "fill", "serve", "setup"]

        for command in commands:
            command_flags = standardizer.get_command_flags(command)
            global_flags = standardizer.get_global_flags()

            # Combine command-specific and global flags
            all_flags = {**global_flags, **command_flags}

            short_forms = [flag.short_form for flag in all_flags.values()]

            # Verify no duplicates within this command
            assert len(short_forms) == len(set(short_forms)), \
                f"Duplicate short forms found in {command} command"

    def test_flag_type_validation(self, standardizer):
        """Test that flag types are valid."""
        valid_types = ["boolean", "string", "integer", "choice"]

        all_commands = ["shelf", "box", "fill", "serve", "setup"]

        for command in all_commands:
            flags = standardizer.get_command_flags(command)

            for flag_name, flag_mapping in flags.items():
                assert flag_mapping.flag_type in valid_types, \
                    f"Invalid flag type '{flag_mapping.flag_type}' for {command}.{flag_name}"

    def test_choice_flags_have_choices(self, standardizer):
        """Test that choice-type flags have choices defined."""
        all_commands = ["shelf", "box", "fill", "serve", "setup"]

        for command in all_commands:
            flags = {**standardizer.get_global_flags(), **standardizer.get_command_flags(command)}

            for flag_name, flag_mapping in flags.items():
                if flag_mapping.flag_type == "choice":
                    assert flag_mapping.choices is not None, \
                        f"Choice flag {command}.{flag_name} missing choices"
                    assert len(flag_mapping.choices) > 0, \
                        f"Choice flag {command}.{flag_name} has empty choices"

    def test_boolean_flags_have_default_false(self, standardizer):
        """Test that boolean flags default to false when specified."""
        all_commands = ["shelf", "box", "fill", "serve", "setup"]

        for command in all_commands:
            flags = {**standardizer.get_global_flags(), **standardizer.get_command_flags(command)}

            for flag_name, flag_mapping in flags.items():
                if flag_mapping.flag_type == "boolean" and flag_mapping.default_value is not None:
                    assert flag_mapping.default_value == "false", \
                        f"Boolean flag {command}.{flag_name} should default to 'false'"

    def test_long_form_naming_convention(self, standardizer):
        """Test that long forms follow kebab-case convention."""
        all_commands = ["shelf", "box", "fill", "serve", "setup"]

        for command in all_commands:
            flags = {**standardizer.get_global_flags(), **standardizer.get_command_flags(command)}

            for flag_name, flag_mapping in flags.items():
                long_form = flag_mapping.long_form
                assert long_form.startswith("--"), \
                    f"Long form {long_form} should start with '--'"

                # Check kebab-case (lowercase with hyphens)
                flag_part = long_form[2:]  # Remove "--"
                assert flag_part.islower() or "-" in flag_part, \
                    f"Long form {long_form} should be kebab-case"

    def test_short_form_single_letter(self, standardizer):
        """Test that short forms are single letters."""
        all_commands = ["shelf", "box", "fill", "serve", "setup"]

        for command in all_commands:
            flags = {**standardizer.get_global_flags(), **standardizer.get_command_flags(command)}

            for flag_name, flag_mapping in flags.items():
                short_form = flag_mapping.short_form
                assert short_form.startswith("-"), \
                    f"Short form {short_form} should start with '-'"
                assert len(short_form) == 2, \
                    f"Short form {short_form} should be exactly 2 characters (-X)"

    def test_flag_descriptions_exist(self, standardizer):
        """Test that all flags have descriptions."""
        all_commands = ["shelf", "box", "fill", "serve", "setup"]

        for command in all_commands:
            flags = {**standardizer.get_global_flags(), **standardizer.get_command_flags(command)}

            for flag_name, flag_mapping in flags.items():
                assert flag_mapping.description, \
                    f"Flag {command}.{flag_name} missing description"
                assert len(flag_mapping.description) > 0, \
                    f"Flag {command}.{flag_name} has empty description"

    def test_validate_flag_consistency(self, standardizer):
        """Test overall flag consistency validation."""
        result = standardizer.validate_flag_consistency()

        assert result["has_conflicts"] is False, \
            f"Flag conflicts found: {result.get('conflicts', [])}"

    def test_get_all_flags_for_command(self, standardizer):
        """Test getting complete flag set for a command."""
        shelf_flags = standardizer.get_all_flags("shelf")

        # Should include both global and command-specific
        assert "--init" in [f.long_form for f in shelf_flags.values()]
        assert "--shelf-description" in [f.long_form for f in shelf_flags.values()]

    def test_flag_mapping_serialization(self, standardizer):
        """Test that flag mappings can be serialized."""
        global_flags = standardizer.get_global_flags()

        for flag_name, flag_mapping in global_flags.items():
            # Should be able to convert to dict
            flag_dict = {
                "long_form": flag_mapping.long_form,
                "short_form": flag_mapping.short_form,
                "flag_type": flag_mapping.flag_type,
                "description": flag_mapping.description,
                "choices": flag_mapping.choices,
                "default_value": flag_mapping.default_value,
                "is_global": flag_mapping.is_global
            }

            assert flag_dict["long_form"] is not None
            assert flag_dict["short_form"] is not None