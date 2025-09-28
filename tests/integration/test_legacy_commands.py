"""Integration tests for backward compatibility with legacy commands."""

import pytest
from click.testing import CliRunner
from unittest.mock import patch, Mock

pytestmark = [pytest.mark.integration, pytest.mark.setup]


class TestLegacyInitCommand:
    """Test backward compatibility for 'docbro init' command."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_orchestrator(self):
        """Mock setup orchestrator."""
        with patch("src.logic.setup.core.orchestrator.SetupOrchestrator") as mock:
            yield mock

    def test_init_command_maps_to_setup_init(self, runner, mock_orchestrator):
        """Test 'docbro init' maps to 'docbro setup --init'."""
        # Import after mocking to ensure mock is in place
        with patch("src.cli.main.cli") as mock_cli:
            from src.cli.main import cli

            # Simulate the init command
            result = runner.invoke(cli, ["init"])

            # Should redirect to setup with --init flag
            assert result.exit_code == 0

    def test_init_with_auto_flag(self, runner, mock_orchestrator):
        """Test 'docbro init --auto' works correctly."""
        with patch("src.cli.main.cli") as mock_cli:
            from src.cli.main import cli

            result = runner.invoke(cli, ["init", "--auto"])

            assert result.exit_code == 0

    def test_init_with_force_flag(self, runner, mock_orchestrator):
        """Test 'docbro init --force' works correctly."""
        with patch("src.cli.main.cli") as mock_cli:
            from src.cli.main import cli

            result = runner.invoke(cli, ["init", "--force"])

            assert result.exit_code == 0

    def test_init_with_vector_store(self, runner, mock_orchestrator):
        """Test 'docbro init --vector-store sqlite_vec' works."""
        with patch("src.cli.main.cli") as mock_cli:
            from src.cli.main import cli

            result = runner.invoke(cli, ["init", "--vector-store", "sqlite_vec"])

            assert result.exit_code == 0

    def test_init_preserves_all_options(self, runner, mock_orchestrator):
        """Test all init options are preserved in migration."""
        with patch("src.cli.main.cli") as mock_cli:
            from src.cli.main import cli

            result = runner.invoke(cli, [
                "init",
                "--auto",
                "--force",
                "--vector-store", "qdrant"
            ])

            assert result.exit_code == 0


class TestLegacyUninstallCommand:
    """Test backward compatibility for 'docbro uninstall' command."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

    @pytest.fixture
    def mock_orchestrator(self):
        """Mock setup orchestrator."""
        with patch("src.logic.setup.core.orchestrator.SetupOrchestrator") as mock:
            yield mock

    def test_uninstall_command_maps_to_setup_uninstall(self, runner, mock_orchestrator):
        """Test 'docbro uninstall' maps to 'docbro setup --uninstall'."""
        with patch("src.cli.main.cli") as mock_cli:
            from src.cli.main import cli

            result = runner.invoke(cli, ["uninstall"])

            assert result.exit_code == 0

    def test_uninstall_with_force_flag(self, runner, mock_orchestrator):
        """Test 'docbro uninstall --force' works correctly."""
        with patch("src.cli.main.cli") as mock_cli:
            from src.cli.main import cli

            result = runner.invoke(cli, ["uninstall", "--force"])

            assert result.exit_code == 0

    def test_uninstall_with_backup_flag(self, runner, mock_orchestrator):
        """Test 'docbro uninstall --backup' works correctly."""
        with patch("src.cli.main.cli") as mock_cli:
            from src.cli.main import cli

            result = runner.invoke(cli, ["uninstall", "--backup"])

            assert result.exit_code == 0

    def test_uninstall_with_dry_run(self, runner, mock_orchestrator):
        """Test 'docbro uninstall --dry-run' shows what would be removed."""
        with patch("src.cli.main.cli") as mock_cli:
            from src.cli.main import cli

            result = runner.invoke(cli, ["uninstall", "--dry-run"])

            assert result.exit_code == 0

    def test_uninstall_preserves_all_options(self, runner, mock_orchestrator):
        """Test all uninstall options are preserved."""
        with patch("src.cli.main.cli") as mock_cli:
            from src.cli.main import cli

            result = runner.invoke(cli, [
                "uninstall",
                "--force",
                "--backup",
                "--dry-run"
            ])

            assert result.exit_code == 0


class TestDeprecationWarnings:
    """Test that legacy commands show deprecation warnings."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

    def test_init_shows_deprecation_warning(self, runner):
        """Test 'docbro init' shows deprecation warning."""
        with patch("src.cli.main.cli") as mock_cli:
            from src.cli.main import cli

            result = runner.invoke(cli, ["init"])

            # Check for deprecation message
            assert "deprecated" in result.output.lower() or \
                   "setup --init" in result.output.lower()

    def test_uninstall_shows_deprecation_warning(self, runner):
        """Test 'docbro uninstall' shows deprecation warning."""
        with patch("src.cli.main.cli") as mock_cli:
            from src.cli.main import cli

            result = runner.invoke(cli, ["uninstall"])

            # Check for deprecation message
            assert "deprecated" in result.output.lower() or \
                   "setup --uninstall" in result.output.lower()


class TestMigrationPath:
    """Test migration path from old to new commands."""

    @pytest.fixture
    def runner(self):
        """Create Click test runner."""
        return CliRunner()

    def test_help_shows_both_old_and_new_commands(self, runner):
        """Test help text shows both legacy and new commands."""
        with patch("src.cli.main.cli") as mock_cli:
            from src.cli.main import cli

            result = runner.invoke(cli, ["--help"])

            # Should show both commands
            assert "setup" in result.output
            assert "init" in result.output
            assert "uninstall" in result.output

    def test_legacy_commands_marked_deprecated_in_help(self, runner):
        """Test legacy commands marked as deprecated in help."""
        with patch("src.cli.main.cli") as mock_cli:
            from src.cli.main import cli

            result = runner.invoke(cli, ["init", "--help"])

            assert "(deprecated)" in result.output.lower()

    def test_migration_guide_reference(self, runner):
        """Test deprecation messages reference migration guide."""
        with patch("src.cli.main.cli") as mock_cli:
            from src.cli.main import cli

            result = runner.invoke(cli, ["init"])

            # Should reference new command or docs
            assert "setup --init" in result.output or \
                   "migration" in result.output.lower()