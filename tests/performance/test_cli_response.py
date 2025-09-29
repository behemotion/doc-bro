"""Performance tests for CLI response time."""

import pytest
import time
from click.testing import CliRunner
from unittest.mock import patch, MagicMock
from src.cli.main import main


class TestCliResponsePerformance:
    """Test CLI response time performance."""

    def test_help_response_time(self):
        """Test that help command responds in < 100ms."""
        runner = CliRunner()

        start_time = time.perf_counter()
        result = runner.invoke(main, ["--help"])
        end_time = time.perf_counter()

        response_time = (end_time - start_time) * 1000  # Convert to ms

        assert result.exit_code == 0
        assert response_time < 100, f"Help response took {response_time:.2f}ms (expected < 100ms)"

    def test_bare_command_response_time(self):
        """Test that bare command responds in < 100ms."""
        runner = CliRunner()

        start_time = time.perf_counter()
        result = runner.invoke(main, [])
        end_time = time.perf_counter()

        response_time = (end_time - start_time) * 1000

        assert result.exit_code == 0
        assert response_time < 100, f"Bare command response took {response_time:.2f}ms"

    def test_list_command_response_time(self):
        """Test that list command initial response is < 100ms."""
        runner = CliRunner()

        with patch('src.cli.main.run_async') as mock_run:
            # Mock to avoid actual async initialization
            mock_run.return_value = None

            start_time = time.perf_counter()
            result = runner.invoke(main, ["list"])
            end_time = time.perf_counter()

            response_time = (end_time - start_time) * 1000

            assert response_time < 100, f"List command took {response_time:.2f}ms"

    def test_command_help_response_times(self):
        """Test that all command help responses are < 100ms."""
        runner = CliRunner()
        commands = ["create", "crawl", "list", "search", "remove", "serve", "status"]

        for cmd in commands:
            start_time = time.perf_counter()
            result = runner.invoke(main, [cmd, "--help"])
            end_time = time.perf_counter()

            response_time = (end_time - start_time) * 1000

            assert response_time < 100, f"{cmd} --help took {response_time:.2f}ms"

    def test_debug_flag_overhead(self):
        """Test that debug flag doesn't significantly impact response time."""
        runner = CliRunner()

        # Normal help
        start_normal = time.perf_counter()
        result_normal = runner.invoke(main, ["--help"])
        time_normal = (time.perf_counter() - start_normal) * 1000

        # Debug help
        start_debug = time.perf_counter()
        result_debug = runner.invoke(main, ["--debug", "--help"])
        time_debug = (time.perf_counter() - start_debug) * 1000

        # Debug shouldn't add more than 20ms overhead
        overhead = time_debug - time_normal
        assert overhead < 20, f"Debug flag added {overhead:.2f}ms overhead"

    def test_multiple_flags_response_time(self):
        """Test response time with multiple flags."""
        runner = CliRunner()

        # Test shelf list with multiple valid flags
        start_time = time.perf_counter()
        result = runner.invoke(main, [
            "shelf", "list", "--verbose", "--limit", "10"
        ])
        end_time = time.perf_counter()

        response_time = (end_time - start_time) * 1000

        # Command should execute quickly even with no shelves
        assert response_time < 150, f"Multiple flags took {response_time:.2f}ms"

    @pytest.mark.skip(reason="pytest-benchmark not installed - optional performance tool")
    def test_cli_startup_benchmark(self):
        """Benchmark CLI startup time (skipped without pytest-benchmark)."""
        # This test requires pytest-benchmark plugin
        # Install with: pip install pytest-benchmark
        pass

    def test_error_response_time(self):
        """Test that error responses are fast."""
        runner = CliRunner()

        # Invalid command
        start_time = time.perf_counter()
        result = runner.invoke(main, ["nonexistent"])
        end_time = time.perf_counter()

        response_time = (end_time - start_time) * 1000

        assert response_time < 100, f"Error response took {response_time:.2f}ms"

    def test_version_response_time(self):
        """Test that version command responds quickly."""
        runner = CliRunner()

        start_time = time.perf_counter()
        result = runner.invoke(main, ["--version"])
        end_time = time.perf_counter()

        response_time = (end_time - start_time) * 1000

        assert result.exit_code == 0
        assert response_time < 50, f"Version response took {response_time:.2f}ms"

    def test_wizard_initial_response(self):
        """Test that wizard initial response is fast."""
        runner = CliRunner()

        with patch('src.logic.wizard.orchestrator.WizardOrchestrator') as mock_wizard:
            mock_wizard.return_value.start_wizard.return_value = {}

            start_time = time.perf_counter()
            # Test shelf create with --init flag (wizard invocation)
            result = runner.invoke(main, ["shelf", "create", "test-shelf", "--init"])
            end_time = time.perf_counter()

            response_time = (end_time - start_time) * 1000

            # Wizard initialization should be fast
            assert response_time < 150, f"Wizard init took {response_time:.2f}ms"