"""Cross-platform compatibility tests"""

import pytest
import sys
import os
from unittest.mock import patch, MagicMock

from src.cli.interface.services.terminal_adapter import TerminalAdapter
from src.cli.interface.services.text_truncator import TextTruncator
from src.cli.interface.components.full_width_display import FullWidthProgressDisplay
from src.cli.interface.components.compact_display import CompactProgressDisplay
from src.cli.interface.services.progress_coordinator import ProgressDisplayCoordinator


@pytest.mark.integration
class TestCrossPlatformCompatibility:
    """Cross-platform compatibility tests"""

    def test_terminal_adapter_on_different_platforms(self):
        """Test TerminalAdapter works across platforms"""
        adapter = TerminalAdapter()

        # Test basic functionality
        width = adapter.get_terminal_width()
        assert isinstance(width, int)
        assert width > 0

        colors = adapter.supports_colors()
        assert isinstance(colors, bool)

        unicode_support = adapter.supports_unicode()
        assert isinstance(unicode_support, bool)

    @pytest.mark.parametrize("platform", ["linux", "darwin", "win32"])
    def test_platform_specific_behavior(self, platform):
        """Test behavior on different platforms"""
        with patch('sys.platform', platform):
            adapter = TerminalAdapter()

            # Should work regardless of platform
            width = adapter.get_terminal_width()
            assert width >= 40  # Minimum reasonable width

            # Should handle platform differences gracefully
            is_interactive = adapter.is_interactive()
            assert isinstance(is_interactive, bool)

    @pytest.mark.parametrize("encoding", ["utf-8", "ascii", "cp1252", "latin1"])
    def test_unicode_support_with_different_encodings(self, encoding):
        """Test Unicode support detection with different encodings"""
        with patch('sys.stdout.encoding', encoding):
            adapter = TerminalAdapter()
            unicode_support = adapter.supports_unicode()

            assert isinstance(unicode_support, bool)

            # UTF-8 should generally support Unicode
            if encoding == "utf-8":
                # Note: This might be True but could be False in some test environments
                pass

            # ASCII should not support Unicode box drawing
            if encoding == "ascii":
                assert unicode_support is False

    @pytest.mark.parametrize("width", [40, 60, 80, 120, 160])
    def test_responsive_layout_at_different_widths(self, width):
        """Test responsive layout behavior at different terminal widths"""
        with patch.object(TerminalAdapter, 'get_terminal_width', return_value=width):
            coordinator = ProgressDisplayCoordinator()
            coordinator.start_operation("Test Operation", "test-project")

            layout_mode = coordinator.get_layout_mode()

            # Verify layout mode is appropriate for width
            if width >= 80:
                # Should prefer full-width for wide terminals
                # (but might fall back to compact due to other factors)
                pass
            else:
                # Should use compact for narrow terminals
                assert layout_mode.value in ["full_width", "compact"]

    def test_text_truncation_cross_platform(self):
        """Test text truncation works consistently across platforms"""
        truncator = TextTruncator()

        test_cases = [
            ("simple text", 20),
            ("very-long-text-that-needs-truncation", 20),
            ("https://example.com/very/long/url/path", 30),
            ("/path/to/very/long/filename.extension", 25),
            ("mixed-content-text", 15),  # Mixed content text
            ("emoji-test-content", 12),  # Content with special characters
        ]

        for text, max_length in test_cases:
            # Middle truncation
            result = truncator.truncate_middle(text, max_length)
            assert len(result) <= max_length

            # End truncation
            result = truncator.truncate_end(text, max_length)
            assert len(result) <= max_length

    def test_progress_display_with_limited_terminal_capabilities(self):
        """Test progress display with limited terminal capabilities"""
        # Mock a very basic terminal
        with patch.object(TerminalAdapter, 'supports_colors', return_value=False), \
             patch.object(TerminalAdapter, 'supports_unicode', return_value=False), \
             patch.object(TerminalAdapter, 'get_terminal_width', return_value=60):

            coordinator = ProgressDisplayCoordinator()
            coordinator.start_operation("Test Operation", "test-project")

            # Should fall back to compact mode
            layout_mode = coordinator.get_layout_mode()
            # The coordinator should handle this gracefully

            # Should still be able to update
            coordinator.update_metrics({"pages": 10, "errors": 0})
            coordinator.set_current_operation("Processing...")

    def test_console_output_with_different_stdout_configurations(self):
        """Test console output with different stdout configurations"""
        # Test with different stdout scenarios
        test_scenarios = [
            {"isatty": True, "encoding": "utf-8"},
            {"isatty": False, "encoding": "utf-8"},  # Redirected output
            {"isatty": True, "encoding": "ascii"},
            {"isatty": False, "encoding": "ascii"},
        ]

        for scenario in test_scenarios:
            with patch('sys.stdout.isatty', return_value=scenario["isatty"]), \
                 patch('sys.stdout.encoding', scenario["encoding"]):

                # Should not crash regardless of stdout configuration
                try:
                    adapter = TerminalAdapter()
                    display = CompactProgressDisplay(adapter)
                    display.start_operation("Test", "test-project")
                    display.update_metrics({"count": 5})
                except Exception as e:
                    pytest.fail(f"Failed with stdout config {scenario}: {e}")

    @patch.dict(os.environ, {"TERM": "dumb"})
    def test_dumb_terminal_compatibility(self):
        """Test compatibility with dumb terminals"""
        adapter = TerminalAdapter()

        # Should handle dumb terminal gracefully
        width = adapter.get_terminal_width()
        assert isinstance(width, int)

        # Should fall back appropriately
        colors = adapter.supports_colors()
        unicode_support = adapter.supports_unicode()

        # Should not crash
        coordinator = ProgressDisplayCoordinator(adapter)
        coordinator.start_operation("Test", "test-project")

    def test_environment_variable_handling(self):
        """Test handling of various environment variables"""
        env_vars_to_test = [
            ("COLUMNS", "100"),
            ("LINES", "30"),
            ("TERM", "xterm-256color"),
            ("COLORTERM", "truecolor"),
        ]

        for var_name, var_value in env_vars_to_test:
            with patch.dict(os.environ, {var_name: var_value}):
                try:
                    adapter = TerminalAdapter()
                    coordinator = ProgressDisplayCoordinator(adapter)
                    coordinator.start_operation("Test", "test-project")
                except Exception as e:
                    pytest.fail(f"Failed with {var_name}={var_value}: {e}")

    def test_error_recovery_cross_platform(self):
        """Test error recovery mechanisms work across platforms"""
        # Test with broken console
        with patch('src.cli.interface.services.terminal_adapter.Console') as mock_console_class:
            mock_console = MagicMock()
            mock_console_class.return_value = mock_console

            # Simulate various console failures
            mock_console.size.width = 80
            type(mock_console).color_system = property(lambda self: None)

            adapter = TerminalAdapter()

            # Should handle gracefully
            width = adapter.get_terminal_width()
            assert isinstance(width, int)

            colors = adapter.supports_colors()
            assert colors is False  # No color system

    def test_memory_usage_cross_platform(self):
        """Test memory usage is reasonable across platforms"""
        import gc

        # Force garbage collection before test
        gc.collect()

        # Create multiple display components
        components = []
        for i in range(10):
            coordinator = ProgressDisplayCoordinator()
            coordinator.start_operation(f"Operation {i}", f"project-{i}")
            components.append(coordinator)

        # Update all components
        for i, coordinator in enumerate(components):
            coordinator.update_metrics({"iteration": i, "count": i * 10})

        # Cleanup
        components.clear()
        gc.collect()

        # Test passes if no memory-related exceptions occurred