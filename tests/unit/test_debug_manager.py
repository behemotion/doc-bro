"""Unit tests for DebugManager."""

import pytest
import logging
from unittest.mock import MagicMock, patch
from src.services.debug_manager import DebugManager, get_debug_manager


class TestDebugManager:
    """Test DebugManager functionality."""

    def test_initialization(self):
        """Test DebugManager initialization."""
        manager = DebugManager()
        assert not manager.debug_enabled
        assert manager._original_log_level == logging.INFO
        assert len(manager._suppressed_loggers) == 0

    def test_enable_debug(self):
        """Test enabling debug mode."""
        manager = DebugManager()
        manager.enable_debug()

        assert manager.debug_enabled
        assert logging.root.level == logging.DEBUG

    def test_disable_debug(self):
        """Test disabling debug mode."""
        manager = DebugManager()
        manager.enable_debug()
        manager.disable_debug()

        assert not manager.debug_enabled
        assert logging.root.level == manager._original_log_level

    def test_suppress_logger(self):
        """Test suppressing a logger."""
        manager = DebugManager()
        test_logger = logging.getLogger("test_logger")
        test_logger.addHandler(logging.StreamHandler())

        manager.suppress_logger("test_logger")

        assert "test_logger" in manager._suppressed_loggers
        assert len(test_logger.handlers) == 0

    def test_restore_logger(self):
        """Test restoring a suppressed logger."""
        manager = DebugManager()
        test_logger = logging.getLogger("test_restore")
        handler = logging.StreamHandler()
        test_logger.addHandler(handler)

        manager.suppress_logger("test_restore")
        assert len(test_logger.handlers) == 0

        manager.restore_logger("test_restore")
        assert "test_restore" not in manager._suppressed_loggers
        assert len(test_logger.handlers) == 1

    def test_restore_all_loggers(self):
        """Test restoring all suppressed loggers."""
        manager = DebugManager()

        manager.suppress_logger("logger1")
        manager.suppress_logger("logger2")
        assert len(manager._suppressed_loggers) == 2

        manager.restore_all_loggers()
        assert len(manager._suppressed_loggers) == 0

    def test_conditional_output_context(self):
        """Test conditional output context manager."""
        manager = DebugManager()

        # Without debug
        with manager.conditional_output() as should_output:
            assert not should_output

        # With debug
        manager.enable_debug()
        with manager.conditional_output() as should_output:
            assert should_output

        # With force
        manager.disable_debug()
        with manager.conditional_output(force=True) as should_output:
            assert should_output

    def test_format_debug_info(self):
        """Test debug info formatting."""
        manager = DebugManager()

        # Without debug
        info = {"key1": "value1", "key2": "value2"}
        result = manager.format_debug_info(info)
        assert result == ""

        # With debug
        manager.enable_debug()
        result = manager.format_debug_info(info)
        assert "DEBUG INFO:" in result
        assert "key1: value1" in result
        assert "key2: value2" in result

    def test_should_show_traceback(self):
        """Test traceback visibility check."""
        manager = DebugManager()

        assert not manager.should_show_traceback()

        manager.enable_debug()
        assert manager.should_show_traceback()

    def test_get_log_level(self):
        """Test getting effective log level."""
        manager = DebugManager()

        assert manager.get_log_level() == logging.WARNING

        manager.enable_debug()
        assert manager.get_log_level() == logging.DEBUG

    def test_configure_library_logging(self):
        """Test library logging configuration."""
        manager = DebugManager()

        with patch('logging.getLogger') as mock_get_logger:
            mock_logger = MagicMock()
            mock_get_logger.return_value = mock_logger

            manager.configure_library_logging()

            # Should configure multiple libraries
            assert mock_get_logger.called
            mock_logger.setLevel.assert_called_with(logging.WARNING)

            # With debug
            manager.enable_debug()
            manager.configure_library_logging()
            mock_logger.setLevel.assert_called_with(logging.DEBUG)

    def test_singleton_pattern(self):
        """Test singleton pattern for get_debug_manager."""
        manager1 = get_debug_manager()
        manager2 = get_debug_manager()

        assert manager1 is manager2