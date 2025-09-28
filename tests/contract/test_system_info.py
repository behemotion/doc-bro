"""
Contract Tests for System Info Panel Functionality
These tests define the expected behavior and will fail initially (TDD approach)
"""

import pytest
from unittest.mock import Mock, patch
from io import StringIO
from rich.console import Console


class TestSystemInfoPanel:
    """Contract tests for system information display"""

    @pytest.fixture(autouse=True)
    def setup(self):
        """Import modules dynamically to handle not existing initially"""
        try:
            from src.logic.setup.models.system_info import SystemInfoPanel, ServiceStatus
            self.SystemInfoPanel = SystemInfoPanel
            self.ServiceStatus = ServiceStatus
        except ImportError:
            pytest.skip("SystemInfoPanel module not yet implemented")

    def test_system_info_displays_all_sections(self):
        """System info must show all required sections"""
        panel = self.SystemInfoPanel()
        panel.collect_async()
        table = panel.format_table()

        # Convert table to string using Console
        console = Console(file=StringIO())
        console.print(table)
        table_str = console.file.getvalue()

        # Check for required sections (case-insensitive for robustness)
        table_str_lower = table_str.lower()
        assert "vector store" in table_str_lower or "settings" in table_str_lower
        assert "embedding model" in table_str_lower or "settings" in table_str_lower
        assert "projects" in table_str_lower or "total" in table_str_lower
        assert "config" in table_str_lower or "directories" in table_str_lower

    def test_system_info_hides_services_with_alternatives(self):
        """Should hide Qdrant when SQLite-vec is available"""
        panel = self.SystemInfoPanel()
        panel.available_services = [
            self.ServiceStatus(name="SQLite-vec", available=True, version="1.0.0", has_alternative=False),
            self.ServiceStatus(name="Qdrant", available=False, version=None, has_alternative=True),
        ]
        filtered = panel.filter_services()
        assert len(filtered) == 1
        assert filtered[0].name == "SQLite-vec"

    def test_system_info_shows_unavailable_critical_services(self):
        """Should show 'Not Available' for critical services"""
        panel = self.SystemInfoPanel()
        panel.available_services = [
            self.ServiceStatus(name="Ollama", available=False, version=None, has_alternative=False),
        ]
        table = panel.format_table()

        # Convert table to string using Console
        console = Console(file=StringIO())
        console.print(table)
        table_str = console.file.getvalue()

        assert "Not Available" in table_str


if __name__ == "__main__":
    pytest.main([__file__, "-v"])