"""Unit tests for CLI short key validation and conflict resolution."""

import pytest
from typing import Dict, List, Set, Optional
from unittest.mock import Mock, patch, MagicMock
import click

from src.cli.utils.short_key_validator import ShortKeyValidator, ShortKeyMapper


class TestShortKeyValidation:
    """Test short key validation and conflict detection."""

    @pytest.fixture
    def validator(self):
        """Create ShortKeyValidator instance."""
        return ShortKeyValidator()

    @pytest.fixture
    def sample_options(self):
        """Sample CLI options for testing."""
        return [
            {"name": "name", "short": "n", "description": "Project name"},
            {"name": "type", "short": "t", "description": "Project type"},
            {"name": "status", "short": "s", "description": "Project status"},
            {"name": "verbose", "short": "v", "description": "Verbose output"},
            {"name": "help", "short": "h", "description": "Show help"},
            {"name": "config", "short": "c", "description": "Config file"},
        ]

    def test_validate_unique_short_keys(self, validator, sample_options):
        """Test validation of unique short keys."""
        result = validator.validate_options(sample_options)

        assert result["valid"] is True
        assert len(result["conflicts"]) == 0
        assert len(result["short_keys"]) == 6

    def test_detect_short_key_conflicts(self, validator):
        """Test detection of short key conflicts."""
        conflicting_options = [
            {"name": "name", "short": "n"},
            {"name": "new", "short": "n"},  # Conflict!
            {"name": "status", "short": "s"},
            {"name": "size", "short": "s"},  # Conflict!
        ]

        result = validator.validate_options(conflicting_options)

        assert result["valid"] is False
        assert len(result["conflicts"]) == 2
        assert "n" in result["conflicts"]
        assert "s" in result["conflicts"]

    def test_global_uniqueness_check(self, validator):
        """Test global uniqueness across command contexts."""
        # Define options for different commands
        project_options = [
            {"name": "name", "short": "n", "context": "project"},
            {"name": "type", "short": "t", "context": "project"},
        ]

        upload_options = [
            {"name": "name", "short": "n", "context": "upload"},  # OK if scoped
            {"name": "source", "short": "s", "context": "upload"},
        ]

        # Test with global uniqueness required
        result = validator.validate_global_uniqueness(
            project_options + upload_options,
            enforce_global=True
        )

        assert result["valid"] is False  # 'n' used in both contexts
        assert "n" in result["global_conflicts"]

        # Test with context scoping allowed
        result = validator.validate_global_uniqueness(
            project_options + upload_options,
            enforce_global=False
        )

        assert result["valid"] is True  # Contexts allow reuse

    def test_reserved_short_keys(self, validator):
        """Test that reserved short keys are not used."""
        reserved = ["h", "?", "-"]  # Common reserved keys

        options_with_reserved = [
            {"name": "host", "short": "h"},  # Reserved for help
            {"name": "query", "short": "?"},  # Reserved for help
            {"name": "minus", "short": "-"},  # Invalid character
        ]

        for option in options_with_reserved:
            result = validator.validate_single_option(option, reserved)
            assert result["valid"] is False
            assert "reserved" in result["reason"].lower()

    def test_short_key_case_sensitivity(self, validator):
        """Test case sensitivity in short key validation."""
        options = [
            {"name": "name", "short": "n"},
            {"name": "Name", "short": "N"},  # Different case
        ]

        # Case sensitive validation (default)
        result = validator.validate_options(options, case_sensitive=True)
        assert result["valid"] is True  # 'n' and 'N' are different

        # Case insensitive validation
        result = validator.validate_options(options, case_sensitive=False)
        assert result["valid"] is False  # 'n' and 'N' conflict


class TestShortKeyGeneration:
    """Test automatic short key generation."""

    @pytest.fixture
    def mapper(self):
        """Create ShortKeyMapper instance."""
        return ShortKeyMapper()

    def test_generate_short_key_from_name(self, mapper):
        """Test generating short key from option name."""
        test_cases = [
            ("name", "n"),
            ("type", "t"),
            ("status", "s"),
            ("verbose", "v"),
            ("output-format", "o"),  # First letter of first word
            ("max-size", "m"),
        ]

        for name, expected in test_cases:
            short_key = mapper.generate_short_key(name)
            assert short_key == expected

    def test_generate_unique_short_key(self, mapper):
        """Test generating unique short key when first choice is taken."""
        used_keys = {"n", "s", "t"}

        # First letter taken, try second
        short_key = mapper.generate_unique_key("name", used_keys)
        assert short_key == "a"  # Second letter

        # Multiple letters taken
        used_keys.update({"a", "m", "e"})
        short_key = mapper.generate_unique_key("name", used_keys)
        assert short_key not in used_keys
        assert len(short_key) == 1

    def test_two_character_fallback(self, mapper):
        """Test two-character key generation when single chars exhausted."""
        # Simulate all single letters taken
        used_keys = set("abcdefghijklmnopqrstuvwxyz")

        short_key = mapper.generate_unique_key(
            "name",
            used_keys,
            allow_two_char=True
        )

        assert len(short_key) == 2
        assert short_key[0] == "n"  # First letter of name
        assert short_key not in used_keys

    def test_generate_keys_for_option_set(self, mapper):
        """Test generating keys for a complete option set."""
        options = [
            "name", "new", "next",  # All start with 'n'
            "status", "size", "sort",  # All start with 's'
            "type", "test",  # Start with 't'
            "verbose",
        ]

        key_map = mapper.generate_key_map(options)

        # All options should have unique keys
        assert len(key_map) == len(options)
        assert len(set(key_map.values())) == len(options)

        # Check specific assignments
        assert key_map["name"] == "n"  # Gets first 'n'
        assert key_map["verbose"] == "v"  # No conflict

        # Others get alternatives
        assert key_map["new"] != "n"
        assert key_map["status"] == "s"  # Gets first 's'
        assert key_map["size"] != "s"

    def test_prioritized_key_assignment(self, mapper):
        """Test that important options get priority for short keys."""
        options = [
            {"name": "name", "priority": 1},
            {"name": "new", "priority": 2},
            {"name": "next", "priority": 3},
        ]

        key_map = mapper.generate_with_priority(options)

        # Highest priority gets first choice
        assert key_map["name"] == "n"
        # Lower priorities get alternatives
        assert key_map["new"] != "n"
        assert key_map["next"] != "n"


class TestCLIShortKeyIntegration:
    """Test integration with Click CLI framework."""

    def test_click_option_with_short_key(self):
        """Test Click option decoration with short keys."""

        @click.command()
        @click.option("--name", "-n", help="Project name")
        @click.option("--type", "-t", help="Project type")
        @click.option("--verbose", "-v", is_flag=True, help="Verbose output")
        def sample_command(name, type, verbose):
            return {"name": name, "type": type, "verbose": verbose}

        # Test that options are properly configured
        assert len(sample_command.params) == 3

        # Check short forms exist
        name_param = sample_command.params[0]
        assert "-n" in name_param.opts

        type_param = sample_command.params[1]
        assert "-t" in type_param.opts

        verbose_param = sample_command.params[2]
        assert "-v" in verbose_param.opts

    def test_command_group_short_keys(self):
        """Test short keys across command group."""

        @click.group()
        def cli():
            pass

        @cli.command()
        @click.option("--name", "-n")
        def create(name):
            return name

        @cli.command()
        @click.option("--name", "-n")  # Same short key in different command
        def remove(name):
            return name

        # Both commands can use -n in their context
        assert create.params[0].opts == ("--name", "-n")
        assert remove.params[0].opts == ("--name", "-n")

    def test_dynamic_short_key_assignment(self):
        """Test dynamic assignment of short keys at runtime."""
        mapper = ShortKeyMapper()

        # Simulate dynamic command construction
        command_options = {
            "create": ["name", "type", "config"],
            "list": ["status", "type", "limit"],
            "remove": ["name", "force", "confirm"],
        }

        # Generate keys for each command
        key_maps = {}
        for cmd, options in command_options.items():
            key_maps[cmd] = mapper.generate_key_map(options)

        # Verify each command has unique internal keys
        for cmd, key_map in key_maps.items():
            assert len(key_map) == len(command_options[cmd])
            assert len(set(key_map.values())) == len(key_map)


class TestShortKeyConflictResolution:
    """Test strategies for resolving short key conflicts."""

    @pytest.fixture
    def resolver(self):
        """Create conflict resolver."""
        return ShortKeyValidator()

    def test_automatic_conflict_resolution(self, resolver):
        """Test automatic resolution of conflicts."""
        conflicting_options = [
            {"name": "name", "short": "n"},
            {"name": "new", "short": "n"},
            {"name": "next", "short": "n"},
        ]

        resolved = resolver.resolve_conflicts(conflicting_options)

        # All should have unique keys after resolution
        short_keys = [opt["short"] for opt in resolved]
        assert len(short_keys) == len(set(short_keys))

        # First option keeps original
        assert resolved[0]["short"] == "n"

        # Others get new keys
        assert resolved[1]["short"] != "n"
        assert resolved[2]["short"] != "n"
        assert resolved[1]["short"] != resolved[2]["short"]

    def test_manual_conflict_resolution(self, resolver):
        """Test manual override of conflicting keys."""
        options = [
            {"name": "name", "short": "n"},
            {"name": "new", "short": "n", "override": "w"},  # Manual override
        ]

        resolved = resolver.resolve_conflicts(
            options,
            allow_override=True
        )

        assert resolved[0]["short"] == "n"
        assert resolved[1]["short"] == "w"  # Uses override

    def test_conflict_resolution_with_constraints(self, resolver):
        """Test resolution with additional constraints."""
        options = [
            {"name": "name", "short": "n"},
            {"name": "new", "short": "n"},
        ]

        forbidden_keys = {"e", "w"}  # Can't use these

        resolved = resolver.resolve_conflicts(
            options,
            forbidden=forbidden_keys
        )

        # Resolution avoids forbidden keys
        for opt in resolved:
            assert opt["short"] not in forbidden_keys


class TestShortKeyDocumentation:
    """Test generation of short key documentation."""

    @pytest.fixture
    def doc_generator(self):
        """Create documentation generator."""
        return ShortKeyMapper()

    def test_generate_help_text(self, doc_generator):
        """Test generation of help text with short keys."""
        options = [
            {"name": "name", "short": "n", "description": "Project name"},
            {"name": "type", "short": "t", "description": "Project type"},
            {"name": "verbose", "short": "v", "description": "Verbose output"},
        ]

        help_text = doc_generator.generate_help(options)

        assert "-n, --name" in help_text
        assert "-t, --type" in help_text
        assert "-v, --verbose" in help_text

        # Descriptions included
        assert "Project name" in help_text
        assert "Project type" in help_text

    def test_generate_usage_examples(self, doc_generator):
        """Test generation of usage examples with short keys."""
        command_name = "docbro project"
        options = [
            {"name": "name", "short": "n", "required": True},
            {"name": "type", "short": "t", "required": True},
            {"name": "verbose", "short": "v", "required": False},
        ]

        examples = doc_generator.generate_examples(command_name, options)

        # Should include both long and short form examples
        assert f"{command_name} --name test --type data" in examples
        assert f"{command_name} -n test -t data" in examples

        # Optional parameters shown separately
        assert "-v" in examples or "--verbose" in examples

    def test_generate_conflict_report(self, doc_generator):
        """Test generation of conflict resolution report."""
        original = [
            {"name": "name", "short": "n"},
            {"name": "new", "short": "n"},
        ]

        resolved = [
            {"name": "name", "short": "n"},
            {"name": "new", "short": "e"},  # Changed
        ]

        report = doc_generator.generate_conflict_report(original, resolved)

        assert "Conflict resolved" in report
        assert "name: n (unchanged)" in report
        assert "new: n → e" in report  # Shows change


class TestShortKeyPersistence:
    """Test saving and loading short key mappings."""

    @pytest.fixture
    def mapper(self):
        """Create ShortKeyMapper instance."""
        return ShortKeyMapper()

    def test_save_key_mappings(self, mapper, tmp_path):
        """Test saving key mappings to file."""
        mappings = {
            "project": {
                "name": "n",
                "type": "t",
                "status": "s"
            },
            "upload": {
                "source": "s",
                "type": "t",
                "recursive": "r"
            }
        }

        mapping_file = tmp_path / "key_mappings.json"
        mapper.save_mappings(mappings, mapping_file)

        assert mapping_file.exists()

        loaded = mapper.load_mappings(mapping_file)
        assert loaded == mappings

    def test_validate_loaded_mappings(self, mapper):
        """Test validation of loaded mappings."""
        # Valid mappings
        valid_mappings = {
            "command": {
                "option1": "a",
                "option2": "b"
            }
        }

        assert mapper.validate_mappings(valid_mappings) is True

        # Invalid: duplicate values
        invalid_mappings = {
            "command": {
                "option1": "a",
                "option2": "a"  # Duplicate!
            }
        }

        assert mapper.validate_mappings(invalid_mappings) is False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])