"""
Contract Tests for Exit Codes
These tests define the expected behavior and will fail initially (TDD approach)
"""

import pytest
from unittest.mock import Mock, patch
from click.testing import CliRunner


class TestExitCodes:
    """Contract tests for exit codes"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Import cli dynamically to handle module not existing initially"""
        try:
            from src.cli.main import cli
            self.cli = cli
        except ImportError:
            pytest.skip("CLI module not yet implemented")

    def test_successful_operation_returns_0(self):
        """Successful operations should return exit code 0"""
        runner = CliRunner()
        with patch('src.logic.setup.services.initializer.SetupInitializer.execute', return_value=True):
            result = runner.invoke(self.cli, ['init'], input='y\n')
            assert result.exit_code == 0

    def test_user_cancellation_returns_1(self):
        """User cancellation should return exit code 1"""
        runner = CliRunner()
        result = runner.invoke(self.cli, ['uninstall'], input='n\n')
        assert result.exit_code == 1

    def test_operation_failure_returns_2(self):
        """Failed operations should return exit code 2"""
        runner = CliRunner()
        with patch('src.logic.setup.services.uninstaller.SetupUninstaller.execute', side_effect=Exception("Failed")):
            result = runner.invoke(self.cli, ['uninstall'], input='y\n')
            assert result.exit_code == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])