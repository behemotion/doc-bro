"""
Integration tests for docbro setup interactive menu.
"""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
import yaml

from src.cli.commands.setup_settings import setup_settings
from src.models.settings import GlobalSettings


class TestSetupMenu:
    """Test docbro setup menu integration."""

    def test_setup_non_interactive_displays_settings(self, tmp_path, monkeypatch):
        """Test setup --non-interactive displays current settings."""
        config_dir = tmp_path / ".config" / "docbro"
        config_dir.mkdir(parents=True)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))

        # Create test settings
        settings_file = config_dir / "settings.yaml"
        test_settings = {
            "version": "1.0.0",
            "settings": GlobalSettings(crawl_depth=5).model_dump()
        }
        with open(settings_file, "w") as f:
            yaml.dump(test_settings, f)

        runner = CliRunner()
        result = runner.invoke(setup_settings, ["--non-interactive"])

        assert result.exit_code == 0
        assert "Current Global Settings" in result.output
        assert "Crawl Depth" in result.output
        assert "5" in result.output  # Our custom value

    def test_setup_reset_flag_creates_backup(self, tmp_path, monkeypatch):
        """Test setup --reset creates backup and resets to defaults."""
        config_dir = tmp_path / ".config" / "docbro"
        config_dir.mkdir(parents=True)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))

        # Create custom settings
        settings_file = config_dir / "settings.yaml"
        custom_settings = {
            "version": "1.0.0",
            "settings": GlobalSettings(crawl_depth=8).model_dump()
        }
        with open(settings_file, "w") as f:
            yaml.dump(custom_settings, f)

        runner = CliRunner()
        # Simulate confirming reset
        result = runner.invoke(setup_settings, ["--reset"], input="y\n")

        assert result.exit_code == 0
        assert "reset to factory defaults" in result.output.lower()

        # Check settings reset to defaults
        with open(settings_file) as f:
            data = yaml.safe_load(f)
            assert data["settings"]["crawl_depth"] == 3  # Default

        # Check backup exists
        backup_files = list(config_dir.glob("*.backup.*"))
        assert len(backup_files) > 0

    @patch('src.cli.commands.setup_settings.Prompt.ask')
    def test_setup_interactive_menu_editing(self, mock_prompt, tmp_path, monkeypatch):
        """Test interactive menu allows editing settings."""
        config_dir = tmp_path / ".config" / "docbro"
        config_dir.mkdir(parents=True)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))

        # Create initial settings
        settings_file = config_dir / "settings.yaml"
        initial_settings = {
            "version": "1.0.0",
            "settings": GlobalSettings().model_dump()
        }
        with open(settings_file, "w") as f:
            yaml.dump(initial_settings, f)

        # Mock user input: edit crawl_depth then quit
        mock_prompt.side_effect = [
            "crawl_depth",  # Select field to edit
            "7",  # New value
            "q"  # Quit
        ]

        runner = CliRunner()
        result = runner.invoke(setup_settings)

        assert result.exit_code == 0
        assert "Settings saved" in result.output

        # Check setting was updated
        with open(settings_file) as f:
            data = yaml.safe_load(f)
            assert data["settings"]["crawl_depth"] == 7

    def test_setup_validates_input_values(self, tmp_path, monkeypatch):
        """Test setup validates user input."""
        config_dir = tmp_path / ".config" / "docbro"
        config_dir.mkdir(parents=True)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))

        # Create settings file
        settings_file = config_dir / "settings.yaml"
        settings_data = {
            "version": "1.0.0",
            "settings": GlobalSettings().model_dump()
        }
        with open(settings_file, "w") as f:
            yaml.dump(settings_data, f)

        runner = CliRunner()
        # Try to set invalid values
        result = runner.invoke(setup_settings, input="crawl_depth\n20\nq\n")

        # Should show error for invalid value (20 > max of 10)
        assert "Error" in result.output or "invalid" in result.output.lower()

    def test_setup_menu_shows_fixed_fields(self, tmp_path, monkeypatch):
        """Test setup menu shows non-editable fields as fixed."""
        config_dir = tmp_path / ".config" / "docbro"
        config_dir.mkdir(parents=True)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))

        # Create settings
        settings_file = config_dir / "settings.yaml"
        settings_data = {
            "version": "1.0.0",
            "settings": GlobalSettings().model_dump()
        }
        with open(settings_file, "w") as f:
            yaml.dump(settings_data, f)

        runner = CliRunner()
        result = runner.invoke(setup_settings, ["--non-interactive"])

        assert result.exit_code == 0
        # Check that fixed fields are marked
        assert "fixed" in result.output.lower()
        assert "Vector Storage" in result.output
        assert "Qdrant URL" in result.output
        assert "Ollama URL" in result.output