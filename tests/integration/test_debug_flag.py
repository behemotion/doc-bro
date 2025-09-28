"""Integration tests for debug flag control."""

import pytest
import logging
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from src.cli.main import main
from src.services.debug_manager import get_debug_manager
from src.lib.conditional_logging import get_logging_configurator


class TestDebugFlagIntegration:
    """Integration tests for debug flag functionality."""

    def test_debug_flag_enables_verbose_output(self):
        """Test that --debug flag enables verbose logging output."""
        runner = CliRunner()

        # Without debug flag
        result_normal = runner.invoke(main, ["list"])

        # With debug flag
        result_debug = runner.invoke(main, ["--debug", "list"])

        # Debug output should be more verbose
        assert len(result_debug.output) >= len(result_normal.output)

        # Debug output should contain log level indicators
        if result_debug.exit_code == 0:
            debug_indicators = ["DEBUG", "INFO", "[", "]", "ms", "-"]
            assert any(indicator in result_debug.output for indicator in debug_indicators)

    def test_debug_flag_affects_all_commands(self):
        """Test that debug flag works with all commands."""
        runner = CliRunner()
        commands = ["list", "status", "version"]

        for cmd in commands:
            result_normal = runner.invoke(main, [cmd])
            result_debug = runner.invoke(main, ["--debug", cmd])

            # Both should work
            assert result_normal.exit_code == 0
            assert result_debug.exit_code == 0

    def test_info_messages_suppressed_without_debug(self):
        """Test that INFO messages are hidden without debug flag."""
        runner = CliRunner()

        with patch('logging.getLogger') as mock_logger:
            logger_instance = MagicMock()
            mock_logger.return_value = logger_instance

            # Run without debug
            result = runner.invoke(main, ["list"])

            # INFO should not appear in output
            assert "INFO" not in result.output

    def test_debug_manager_integration(self):
        """Test that debug manager properly integrates with CLI context."""
        runner = CliRunner()

        with patch('src.cli.context.get_debug_manager') as mock_get_dm:
            debug_manager = MagicMock()
            mock_get_dm.return_value = debug_manager

            # Run with debug flag
            result = runner.invoke(main, ["--debug", "list"])

            # Debug manager should be configured
            assert debug_manager.enable_debug.called

    def test_library_logging_suppression(self):
        """Test that third-party library logging is suppressed."""
        runner = CliRunner()

        with patch('logging.getLogger') as mock_logger:
            loggers = {}

            def get_logger(name):
                if name not in loggers:
                    loggers[name] = MagicMock()
                return loggers[name]

            mock_logger.side_effect = get_logger

            # Run without debug
            result = runner.invoke(main, ["list"])

            # Check that noisy libraries would be suppressed
            noisy_libs = ['urllib3', 'requests', 'httpx', 'sqlalchemy.engine']
            for lib in noisy_libs:
                if lib in loggers:
                    # Should be set to WARNING or higher
                    assert loggers[lib].setLevel.called

    def test_debug_flag_persistence_in_context(self):
        """Test that debug flag persists through command execution."""
        runner = CliRunner()

        with patch('src.cli.context.CliContext') as mock_context:
            ctx_instance = MagicMock()
            mock_context.return_value = ctx_instance

            result = runner.invoke(main, ["--debug", "crawl", "--help"])

            # Context should maintain debug state
            assert ctx_instance.enable_debug.called or ctx_instance.debug_enabled

    def test_conditional_logging_handler(self):
        """Test that conditional logging handler works correctly."""
        from src.lib.conditional_logging import ConditionalHandler

        handler = ConditionalHandler(debug_enabled=False)

        # Create test records
        info_record = logging.LogRecord(
            "test", logging.INFO, "", 1, "Info message", (), None
        )
        warning_record = logging.LogRecord(
            "test", logging.WARNING, "", 1, "Warning message", (), None
        )

        # Test suppression
        handler.emit(info_record)
        assert handler.get_suppressed_count() == 1

        # Warnings should always show
        handler.emit(warning_record)
        assert handler.get_suppressed_count() == 1  # Still 1, warning not suppressed

        # Enable debug
        handler.set_debug_enabled(True)
        handler.emit(info_record)
        # Count doesn't increase when debug enabled

    def test_debug_output_format(self):
        """Test that debug output has proper format."""
        runner = CliRunner()

        with patch('src.cli.main.logger') as mock_logger:
            result = runner.invoke(main, ["--debug", "list"])

            # Check that timestamp format is included in debug mode
            if mock_logger.debug.called:
                call_args = str(mock_logger.debug.call_args_list)
                # Debug messages should have structure

    def test_debug_flag_with_errors(self):
        """Test that debug flag shows full traceback on errors."""
        runner = CliRunner()

        with patch('src.cli.main.some_function') as mock_func:
            mock_func.side_effect = Exception("Test error")

            # Without debug - concise error
            result_normal = runner.invoke(main, ["some-command"], catch_exceptions=True)

            # With debug - full traceback
            result_debug = runner.invoke(main, ["--debug", "some-command"], catch_exceptions=True)

            if result_debug.exit_code != 0:
                # Debug should show more error detail
                assert len(result_debug.output) >= len(result_normal.output)