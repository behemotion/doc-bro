"""Unit tests for CLI short key validation and conflict resolution."""

import pytest
from typing import Dict, List, Set, Optional
from unittest.mock import Mock, patch, MagicMock
import click

from src.cli.utils.short_key_validator import ContextualShortKeyManager, ShortKeyMapping


class TestContextualShortKeyManager:
    """Test ContextualShortKeyManager functionality."""

    @pytest.fixture
    def manager(self):
        """Create ContextualShortKeyManager instance."""
        return ContextualShortKeyManager()

    def test_initialization(self, manager):
        """Test manager initialization with default mappings."""
        assert manager.context_mappings is not None
        assert manager.reverse_mappings is not None
        assert manager.global_options is not None

        # Check some default global options
        assert "--help" in manager.global_options
        assert manager.global_options["--help"] == "-h"

    def test_register_context(self, manager):
        """Test registering a new context with mappings."""
        test_context = "test.command"
        test_mappings = {
            "--name": "-n",
            "--type": "-t"
        }

        manager.register_context(test_context, test_mappings)

        assert test_context in manager.context_mappings
        assert manager.context_mappings[test_context]["--name"] == "-n"
        assert manager.context_mappings[test_context]["--type"] == "-t"

    def test_add_mapping_success(self, manager):
        """Test successfully adding a mapping."""
        result = manager.add_mapping("test.context", "--option", "-o")

        assert result is True
        assert manager.get_short_key("--option", "test.context") == "-o"

    def test_add_mapping_conflict(self, manager):
        """Test adding conflicting mapping."""
        # Add first mapping
        manager.add_mapping("test.context", "--option1", "-o")

        # Try to add conflicting mapping
        result = manager.add_mapping("test.context", "--option2", "-o")

        assert result is False  # Should fail due to conflict

    def test_get_short_key_global(self, manager):
        """Test getting short key for global option."""
        short_key = manager.get_short_key("--help", "any.context")
        assert short_key == "-h"

    def test_get_short_key_context_specific(self, manager):
        """Test getting short key for context-specific option."""
        # Use existing project context
        short_key = manager.get_short_key("--name", "project")
        assert short_key == "-n"

    def test_get_short_key_not_found(self, manager):
        """Test getting short key for non-existent option."""
        short_key = manager.get_short_key("--nonexistent", "project")
        assert short_key is None

    def test_validate_context_success(self, manager):
        """Test validating a context with no conflicts."""
        is_valid, issues = manager.validate_context("project")
        assert is_valid is True
        assert len(issues) == 0

    def test_validate_context_with_conflicts(self, manager):
        """Test validating a context with conflicts."""
        # Create a context with conflicts
        test_context = "test.conflict"
        manager.context_mappings[test_context] = {
            "--option1": "-x",
            "--option2": "-x"  # Conflict!
        }
        manager.reverse_mappings[test_context] = {
            "-x": "--option1"  # Will detect conflict with option2
        }

        is_valid, issues = manager.validate_context(test_context)
        assert is_valid is False
        assert len(issues) > 0

    def test_suggest_short_key(self, manager):
        """Test suggesting a short key for an option."""
        suggestion = manager.suggest_short_key("--example", "test.context")
        assert suggestion.startswith("-")
        assert len(suggestion) >= 2  # At least "-x"


class TestShortKeyGeneration:
    """Test automatic short key generation using ContextualShortKeyManager."""

    @pytest.fixture
    def manager(self):
        """Create ContextualShortKeyManager instance."""
        return ContextualShortKeyManager()

    def test_suggest_short_key_basic(self, manager):
        """Test basic short key suggestion."""
        suggestion = manager.suggest_short_key("--name", "test.context")
        assert suggestion == "-n"

    def test_suggest_short_key_with_conflicts(self, manager):
        """Test short key suggestion when preferred choice is taken."""
        # Add a conflicting mapping
        manager.add_mapping("test.context", "--existing", "-n")

        # Should suggest alternative for --name
        suggestion = manager.suggest_short_key("--name", "test.context")
        assert suggestion != "-n"
        assert suggestion.startswith("-")

    def test_suggest_short_key_with_preferred_chars(self, manager):
        """Test short key suggestion with preferred characters."""
        preferred = ["x", "y", "z"]
        suggestion = manager.suggest_short_key("--option", "test.context", preferred)
        assert suggestion in ["-x", "-y", "-z"]

    def test_context_help_generation(self, manager):
        """Test generating help text for a context."""
        help_text = manager.get_context_help("project")
        assert "Options for project:" in help_text
        assert "--name" in help_text
        assert "-n" in help_text

    def test_get_all_contexts(self, manager):
        """Test getting all registered contexts."""
        contexts = manager.get_all_contexts()
        assert "project" in contexts
        assert "upload" in contexts
        assert len(contexts) > 0

    def test_validate_all_contexts(self, manager):
        """Test validating all contexts."""
        issues = manager.validate_all_contexts()
        # Should be no issues with default configuration
        assert len(issues) == 0


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
        assert create.params[0].opts == ["--name", "-n"]
        assert remove.params[0].opts == ["--name", "-n"]

    def test_contextual_short_key_usage(self):
        """Test using ContextualShortKeyManager with CLI commands."""
        manager = ContextualShortKeyManager()

        # Test getting short keys for project context
        name_key = manager.get_short_key("--name", "project")
        type_key = manager.get_short_key("--type", "project")

        assert name_key == "-n"
        assert type_key == "-t"


class TestShortKeyHelperFunctions:
    """Test helper functions from the short_key_validator module."""

    def test_get_short_key_function(self):
        """Test the convenience get_short_key function."""
        from src.cli.utils.short_key_validator import get_short_key

        # Test getting short key for project name
        short_key = get_short_key("--name", "project", None)
        assert short_key == "-n"

        # Test getting short key for project create context
        short_key = get_short_key("--description", "project", "create")
        assert short_key == "-d"

        # Test non-existent option
        short_key = get_short_key("--nonexistent", "project", None)
        assert short_key == "--nonexistent"  # Returns original if not found

    def test_validate_command_options_function(self):
        """Test the convenience validate_command_options function."""
        from src.cli.utils.short_key_validator import validate_command_options

        # Test valid options
        valid_options = {
            "--name": "-n",
            "--type": "-t"
        }
        is_valid, issues = validate_command_options("test", "cmd", valid_options)
        assert is_valid is True
        assert len(issues) == 0

        # Test conflicting options
        conflicting_options = {
            "--name": "-x",
            "--type": "-x"  # Conflict!
        }
        is_valid, issues = validate_command_options("test", "cmd", conflicting_options)
        assert is_valid is False
        assert len(issues) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])