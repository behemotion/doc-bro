"""
Integration tests for docbro init command.
"""

import pytest
from click.testing import CliRunner
from pathlib import Path
import yaml

from src.cli.commands.init import init
from src.models.settings import GlobalSettings


class TestInitCommand:
    """Test docbro init command integration."""

    def test_init_creates_default_settings(self, tmp_path, monkeypatch):
        """Test init command creates default settings."""
        config_dir = tmp_path / ".config" / "docbro"
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))

        runner = CliRunner()
        result = runner.invoke(init)

        assert result.exit_code == 0
        assert "Initializing DocBro" in result.output
        assert "Settings initialized" in result.output

        # Check settings file created
        settings_file = config_dir / "settings.yaml"
        assert settings_file.exists()

        # Verify default values
        with open(settings_file) as f:
            data = yaml.safe_load(f)
            assert data["settings"]["embedding_model"] == "mxbai-embed-large"
            assert data["settings"]["crawl_depth"] == 3

    def test_init_with_config_overrides(self, tmp_path, monkeypatch):
        """Test init command with --config overrides."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))

        runner = CliRunner()
        result = runner.invoke(init, [
            "--config", "crawl_depth=5",
            "--config", "chunk_size=2000"
        ])

        assert result.exit_code == 0

        # Check overrides applied
        settings_file = tmp_path / ".config" / "docbro" / "settings.yaml"
        with open(settings_file) as f:
            data = yaml.safe_load(f)
            assert data["settings"]["crawl_depth"] == 5
            assert data["settings"]["chunk_size"] == 2000

    def test_init_force_flag_overwrites_existing(self, tmp_path, monkeypatch):
        """Test init --force overwrites existing installation."""
        config_dir = tmp_path / ".config" / "docbro"
        config_dir.mkdir(parents=True)
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))

        # Create existing settings
        settings_file = config_dir / "settings.yaml"
        with open(settings_file, "w") as f:
            yaml.dump({"settings": {"crawl_depth": 7}}, f)

        runner = CliRunner()
        result = runner.invoke(init, ["--force"])

        assert result.exit_code == 0
        assert "Backed up to" in result.output

        # Check settings reset to defaults
        with open(settings_file) as f:
            data = yaml.safe_load(f)
            assert data["settings"]["crawl_depth"] == 3  # Default value

    def test_init_checks_services(self, tmp_path, monkeypatch):
        """Test init command checks for Qdrant and Ollama services."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))

        runner = CliRunner()
        result = runner.invoke(init)

        assert result.exit_code == 0
        assert "Checking services" in result.output
        # Service status will depend on actual services running
        assert "Qdrant:" in result.output
        assert "Ollama:" in result.output

    def test_init_creates_required_directories(self, tmp_path, monkeypatch):
        """Test init creates XDG directories."""
        monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / ".config"))
        monkeypatch.setenv("XDG_DATA_HOME", str(tmp_path / ".local/share"))
        monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / ".cache"))

        runner = CliRunner()
        result = runner.invoke(init)

        assert result.exit_code == 0
        assert (tmp_path / ".config" / "docbro").exists()
        assert (tmp_path / ".local/share" / "docbro").exists()
        assert (tmp_path / ".cache" / "docbro").exists()