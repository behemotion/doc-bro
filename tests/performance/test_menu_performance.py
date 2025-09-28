"""Performance tests for interactive menu responsiveness."""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from rich.console import Console

pytestmark = [pytest.mark.performance, pytest.mark.setup]


class TestMenuResponsiveness:
    """Test that interactive menu meets performance requirements."""

    @pytest.fixture
    def mock_console(self):
        """Mock Rich console for testing."""
        console = Mock(spec=Console)
        console.print = Mock()
        console.clear = Mock()
        return console

    def test_menu_render_under_100ms(self, mock_console):
        """Test that menu renders in <100ms."""
        from src.logic.setup.core.menu import InteractiveMenu

        menu = InteractiveMenu(console=mock_console)
        menu.options = ["Option 1", "Option 2", "Option 3", "Exit"]
        menu.current_index = 0

        start_time = time.perf_counter()
        menu.render()
        end_time = time.perf_counter()

        elapsed_ms = (end_time - start_time) * 1000

        assert elapsed_ms < 100, f"Menu render took {elapsed_ms:.2f}ms"
        mock_console.print.assert_called()

    def test_arrow_key_response_under_50ms(self, mock_console):
        """Test that arrow key navigation responds in <50ms."""
        from src.logic.setup.core.menu import InteractiveMenu

        menu = InteractiveMenu(console=mock_console)
        menu.options = ["Option 1", "Option 2", "Option 3"]
        menu.current_index = 0

        start_time = time.perf_counter()
        menu.handle_key("down")
        end_time = time.perf_counter()

        elapsed_ms = (end_time - start_time) * 1000

        assert elapsed_ms < 50, f"Arrow key response took {elapsed_ms:.2f}ms"
        assert menu.current_index == 1

    def test_menu_selection_instant(self, mock_console):
        """Test that menu selection is instant (<10ms)."""
        from src.logic.setup.core.menu import InteractiveMenu

        menu = InteractiveMenu(console=mock_console)
        menu.options = ["Option 1", "Option 2", "Option 3"]
        menu.current_index = 1

        start_time = time.perf_counter()
        selected = menu.handle_key("enter")
        end_time = time.perf_counter()

        elapsed_ms = (end_time - start_time) * 1000

        assert elapsed_ms < 10, f"Selection took {elapsed_ms:.2f}ms"
        assert selected == "Option 2"

    def test_validation_feedback_under_200ms(self, mock_console):
        """Test that validation feedback appears in <200ms."""
        from src.logic.setup.core.menu import InteractiveMenu

        menu = InteractiveMenu(console=mock_console)

        test_input = "invalid-url"

        start_time = time.perf_counter()
        is_valid = menu.validate_url(test_input)
        if not is_valid:
            menu.show_error("Invalid URL format")
        end_time = time.perf_counter()

        elapsed_ms = (end_time - start_time) * 1000

        assert elapsed_ms < 200, f"Validation feedback took {elapsed_ms:.2f}ms"
        assert not is_valid
        mock_console.print.assert_called()

    def test_menu_navigation_history_performance(self, mock_console):
        """Test menu navigation history doesn't degrade performance."""
        from src.logic.setup.core.menu import InteractiveMenu

        menu = InteractiveMenu(console=mock_console)

        # Navigate through many menus
        for i in range(100):
            menu.enter_submenu(f"menu_{i}")

        # Should still respond quickly even with deep history
        start_time = time.perf_counter()
        menu.handle_key("escape")  # Go back
        end_time = time.perf_counter()

        elapsed_ms = (end_time - start_time) * 1000

        assert elapsed_ms < 50, f"Back navigation took {elapsed_ms:.2f}ms with deep history"

    def test_large_option_list_performance(self, mock_console):
        """Test menu handles large option lists efficiently."""
        from src.logic.setup.core.menu import InteractiveMenu

        menu = InteractiveMenu(console=mock_console)
        # Create a large list of options
        menu.options = [f"Option {i}" for i in range(1000)]
        menu.current_index = 500

        start_time = time.perf_counter()
        menu.render()
        end_time = time.perf_counter()

        elapsed_ms = (end_time - start_time) * 1000

        # Even with 1000 options, should render quickly
        assert elapsed_ms < 200, f"Large list render took {elapsed_ms:.2f}ms"

    def test_menu_help_toggle_performance(self, mock_console):
        """Test that help toggle is instant."""
        from src.logic.setup.core.menu import InteractiveMenu

        menu = InteractiveMenu(console=mock_console)
        menu.help_visible = False

        start_time = time.perf_counter()
        menu.handle_key("?")
        end_time = time.perf_counter()

        elapsed_ms = (end_time - start_time) * 1000

        assert elapsed_ms < 10, f"Help toggle took {elapsed_ms:.2f}ms"
        assert menu.help_visible is True

    def test_menu_search_responsiveness(self, mock_console):
        """Test menu search/filter responsiveness."""
        from src.logic.setup.core.menu import InteractiveMenu

        menu = InteractiveMenu(console=mock_console)
        menu.options = [f"Option {i}" for i in range(100)]

        start_time = time.perf_counter()
        filtered = menu.filter_options("Option 5")
        end_time = time.perf_counter()

        elapsed_ms = (end_time - start_time) * 1000

        assert elapsed_ms < 50, f"Search took {elapsed_ms:.2f}ms"
        assert len(filtered) == 11  # Option 5, 50-59

    def test_menu_state_save_performance(self, mock_console):
        """Test that menu state operations are fast."""
        from src.logic.setup.models.menu_state import MenuState

        state = MenuState(
            current_menu="configuration",
            selected_index=5,
            menu_stack=["main", "configuration"],
            pending_changes={"key": "value"},
            help_visible=True
        )

        # Test state serialization performance
        start_time = time.perf_counter()
        state_dict = state.model_dump()
        end_time = time.perf_counter()

        elapsed_ms = (end_time - start_time) * 1000

        assert elapsed_ms < 10, f"State serialization took {elapsed_ms:.2f}ms"

        # Test state restoration performance
        start_time = time.perf_counter()
        restored = MenuState(**state_dict)
        end_time = time.perf_counter()

        elapsed_ms = (end_time - start_time) * 1000

        assert elapsed_ms < 10, f"State restoration took {elapsed_ms:.2f}ms"


class TestMenuMemoryUsage:
    """Test memory usage of interactive menu."""

    @pytest.fixture
    def mock_console(self):
        """Mock Rich console."""
        return Mock(spec=Console)

    def test_menu_memory_footprint(self, mock_console):
        """Test that menu has reasonable memory footprint."""
        import psutil
        import os
        from src.logic.setup.core.menu import InteractiveMenu

        process = psutil.Process(os.getpid())
        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        # Create menu with many options
        menu = InteractiveMenu(console=mock_console)
        menu.options = [f"Option {i}" for i in range(10000)]

        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = memory_after - memory_before

        # Should not use excessive memory even with many options
        assert memory_increase < 10, f"Menu used {memory_increase:.2f} MB for 10k options"

    def test_menu_navigation_no_memory_leak(self, mock_console):
        """Test that menu navigation doesn't leak memory."""
        import psutil
        import os
        from src.logic.setup.core.menu import InteractiveMenu

        process = psutil.Process(os.getpid())
        menu = InteractiveMenu(console=mock_console)

        memory_before = process.memory_info().rss / 1024 / 1024  # MB

        # Navigate through many menus
        for i in range(1000):
            menu.enter_submenu(f"menu_{i}")
            if i % 10 == 0:
                menu.handle_key("escape")  # Go back occasionally

        memory_after = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = memory_after - memory_before

        # Should not leak memory during navigation
        assert memory_increase < 5, f"Navigation leaked {memory_increase:.2f} MB"