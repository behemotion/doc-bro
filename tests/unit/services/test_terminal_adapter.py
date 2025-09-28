"""Unit tests for TerminalAdapter terminal width detection"""

import pytest
import os
from unittest.mock import patch, MagicMock

from src.cli.interface.services.terminal_adapter import TerminalAdapter


class TestTerminalAdapter:
    """Unit tests for TerminalAdapter"""

    def test_terminal_adapter_initialization(self):
        """Test TerminalAdapter initializes correctly"""
        adapter = TerminalAdapter()
        assert adapter.console is not None

    def test_get_terminal_width_returns_positive_integer(self):
        """Test that terminal width detection returns positive integer"""
        adapter = TerminalAdapter()
        width = adapter.get_terminal_width()

        assert isinstance(width, int)
        assert width > 0
        assert width >= 40  # Minimum reasonable terminal width

    @patch.dict(os.environ, {'COLUMNS': '120'})
    def test_get_terminal_width_with_environment_variable(self):
        """Test terminal width detection with COLUMNS environment variable"""
        with patch('src.cli.interface.services.terminal_adapter.Console') as mock_console_class:
            # Mock console that raises exception to test fallback
            mock_console = MagicMock()
            mock_console.size.width = None
            mock_console_class.return_value = mock_console

            # Make accessing .width raise an exception to trigger fallback
            type(mock_console.size).width = PropertyMock(side_effect=AttributeError())

            adapter = TerminalAdapter()
            width = adapter.get_terminal_width()

            assert width == 120

    def test_get_terminal_width_fallback_to_default(self):
        """Test terminal width fallback to default when detection fails"""
        with patch('src.cli.interface.services.terminal_adapter.Console') as mock_console_class:
            # Mock console that raises exception
            mock_console = MagicMock()
            mock_console_class.return_value = mock_console

            # Make accessing .size raise an exception
            type(mock_console).size = PropertyMock(side_effect=OSError())

            with patch.dict(os.environ, {}, clear=True):  # Clear COLUMNS env var
                adapter = TerminalAdapter()
                width = adapter.get_terminal_width()

                assert width == 80  # Default fallback

    def test_supports_colors_returns_boolean(self):
        """Test that color support detection returns boolean"""
        adapter = TerminalAdapter()
        colors = adapter.supports_colors()

        assert isinstance(colors, bool)

    def test_supports_unicode_returns_boolean(self):
        """Test that Unicode support detection returns boolean"""
        adapter = TerminalAdapter()
        unicode_support = adapter.supports_unicode()

        assert isinstance(unicode_support, bool)

    def test_is_width_sufficient_for_boxes(self):
        """Test terminal width sufficiency checking"""
        adapter = TerminalAdapter()

        # Mock different terminal widths
        with patch.object(adapter, 'get_terminal_width', return_value=120):
            assert adapter.is_width_sufficient_for_boxes(80) is True
            assert adapter.is_width_sufficient_for_boxes(100) is True
            assert adapter.is_width_sufficient_for_boxes(150) is False

        with patch.object(adapter, 'get_terminal_width', return_value=60):
            assert adapter.is_width_sufficient_for_boxes(80) is False
            assert adapter.is_width_sufficient_for_boxes(50) is True

    def test_get_max_content_width(self):
        """Test maximum content width calculation"""
        adapter = TerminalAdapter()

        with patch.object(adapter, 'get_terminal_width', return_value=100):
            # Default border width is 4
            content_width = adapter.get_max_content_width()
            assert content_width == 96

            # Custom border width
            content_width = adapter.get_max_content_width(border_width=6)
            assert content_width == 94

        # Test minimum content width enforcement
        with patch.object(adapter, 'get_terminal_width', return_value=30):
            content_width = adapter.get_max_content_width()
            assert content_width == 40  # Minimum enforced

    def test_is_interactive(self):
        """Test interactive terminal detection"""
        adapter = TerminalAdapter()
        is_interactive = adapter.is_interactive()

        assert isinstance(is_interactive, bool)

    def test_get_console(self):
        """Test console instance retrieval"""
        adapter = TerminalAdapter()
        console = adapter.get_console()

        assert console is not None
        assert console is adapter.console

    @patch('sys.stdout.encoding', 'utf-8')
    def test_supports_unicode_with_utf8_encoding(self):
        """Test Unicode support detection with UTF-8 encoding"""
        adapter = TerminalAdapter()
        unicode_support = adapter.supports_unicode()

        # Should return True for UTF-8 encoding
        assert unicode_support is True

    @patch('sys.stdout.encoding', 'ascii')
    def test_supports_unicode_with_ascii_encoding(self):
        """Test Unicode support detection with ASCII encoding"""
        with patch('src.cli.interface.services.terminal_adapter.sys.stdout') as mock_stdout:
            mock_stdout.encoding = 'ascii'

            adapter = TerminalAdapter()
            unicode_support = adapter.supports_unicode()

            # Should return False for ASCII encoding due to UnicodeEncodeError
            assert unicode_support is False


# Import PropertyMock for the patch
from unittest.mock import PropertyMock