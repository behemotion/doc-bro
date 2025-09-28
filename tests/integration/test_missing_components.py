"""Integration tests for component missing scenarios.

Based on quickstart.md Scenario 3: Component Missing - Graceful Degradation
Tests setup behavior when external dependencies are unavailable.
"""

import pytest
from unittest.mock import AsyncMock, patch
from click.testing import CliRunner

from src.cli.main import main

pytestmark = [pytest.mark.integration, pytest.mark.async_test]


class TestMissingComponentsFlow:
    """Integration tests for missing component scenarios."""

    @pytest.fixture
    def cli_runner(self):
        """CLI runner for integration testing."""
        return CliRunner()

    @pytest.fixture
    def mock_docker_unavailable(self):
        """Mock Docker as unavailable."""
        return {
            'docker': {
                'available': False,
                'version': None,
                'health_status': 'unhealthy',
                'error_message': 'Docker daemon not running or not installed'
            },
            'ollama': {
                'available': True,
                'version': '0.1.17',
                'health_status': 'healthy'
            },
            'claude_code': {
                'available': False,
                'version': None,
                'health_status': 'unknown',
                'error_message': 'Claude Code not detected'
            }
        }

    @pytest.fixture
    def mock_ollama_unavailable(self):
        """Mock Ollama as unavailable."""
        return {
            'docker': {
                'available': True,
                'version': '24.0.5',
                'health_status': 'healthy'
            },
            'ollama': {
                'available': False,
                'version': None,
                'health_status': 'unhealthy',
                'error_message': 'Ollama service not running or not installed'
            },
            'claude_code': {
                'available': False,
                'version': None,
                'health_status': 'unknown',
                'error_message': 'Claude Code not detected'
            }
        }

    @pytest.fixture
    def mock_all_unavailable(self):
        """Mock all components as unavailable."""
        return {
            'docker': {
                'available': False,
                'version': None,
                'health_status': 'unhealthy',
                'error_message': 'Docker not installed'
            },
            'ollama': {
                'available': False,
                'version': None,
                'health_status': 'unhealthy',
                'error_message': 'Ollama not installed'
            },
            'claude_code': {
                'available': False,
                'version': None,
                'health_status': 'unknown',
                'error_message': 'Claude Code not detected'
            }
        }

    @pytest.fixture
    def mock_setup_services(self):
        """Mock setup services for missing component tests."""
        mocks = {}

        with patch('src.services.setup_logic_service.SetupLogicService') as service_mock:
            service_instance = AsyncMock()
            service_mock.return_value = service_instance
            mocks['setup_service'] = service_instance

        yield mocks

    async def test_docker_unavailable_graceful_degradation(self, cli_runner, mock_docker_unavailable, mock_setup_services):
        """Test graceful handling when Docker is not available."""
        setup_service = mock_setup_services['setup_service']
        setup_service.detect_components.return_value = mock_docker_unavailable

        # Mock setup service to handle missing Docker
        from src.models.setup_types import ExternalDependencyError
        setup_service.run_interactive_setup.side_effect = ExternalDependencyError(
            "Docker is required for vector storage but is not available"
        )

        result = cli_runner.invoke(main, ['setup'])

        # Should return appropriate error code for missing dependency
        assert result.exit_code == 3  # External dependency error

        # Should clearly indicate Docker is missing
        output = result.output.lower()
        assert "docker" in output
        assert "not available" in output or "❌" in result.output

    async def test_docker_unavailable_error_messages(self, cli_runner, mock_docker_unavailable, mock_setup_services):
        """Test clear error messages when Docker is unavailable."""
        setup_service = mock_setup_services['setup_service']
        setup_service.detect_components.return_value = mock_docker_unavailable

        from src.models.setup_types import ExternalDependencyError
        setup_service.run_interactive_setup.side_effect = ExternalDependencyError(
            "Docker is required for Qdrant vector storage"
        )

        result = cli_runner.invoke(main, ['setup'])

        assert result.exit_code == 3

        # Should provide actionable error messages
        output = result.output.lower()
        assert "docker" in output
        assert "install" in output or "start" in output or "required" in output

    async def test_docker_unavailable_recovery_instructions(self, cli_runner, mock_docker_unavailable, mock_setup_services):
        """Test recovery instructions are provided when Docker is missing."""
        setup_service = mock_setup_services['setup_service']
        setup_service.detect_components.return_value = mock_docker_unavailable

        from src.models.setup_types import ExternalDependencyError
        setup_service.run_interactive_setup.side_effect = ExternalDependencyError(
            "Docker daemon not running"
        )

        result = cli_runner.invoke(main, ['setup'])

        assert result.exit_code == 3

        # Should suggest specific recovery actions
        output = result.output
        recovery_suggestions = [
            "start docker",
            "install docker",
            "docker desktop",
            "systemctl start docker",
            "brew install docker"
        ]

        # At least one recovery suggestion should be present
        assert any(suggestion in output.lower() for suggestion in recovery_suggestions)

    async def test_ollama_unavailable_graceful_degradation(self, cli_runner, mock_ollama_unavailable, mock_setup_services):
        """Test graceful handling when Ollama is not available."""
        setup_service = mock_setup_services['setup_service']
        setup_service.detect_components.return_value = mock_ollama_unavailable

        from src.models.setup_types import ExternalDependencyError
        setup_service.run_interactive_setup.side_effect = ExternalDependencyError(
            "Ollama is required for embedding models but is not available"
        )

        result = cli_runner.invoke(main, ['setup'])

        # Should return appropriate error code
        assert result.exit_code == 3

        # Should clearly indicate Ollama is missing
        output = result.output.lower()
        assert "ollama" in output
        assert "not available" in output or "❌" in result.output

    async def test_ollama_unavailable_installation_guidance(self, cli_runner, mock_ollama_unavailable, mock_setup_services):
        """Test installation guidance when Ollama is unavailable."""
        setup_service = mock_setup_services['setup_service']
        setup_service.detect_components.return_value = mock_ollama_unavailable

        from src.models.setup_types import ExternalDependencyError
        setup_service.run_interactive_setup.side_effect = ExternalDependencyError(
            "Ollama service not running"
        )

        result = cli_runner.invoke(main, ['setup'])

        assert result.exit_code == 3

        # Should provide Ollama-specific installation instructions
        output = result.output.lower()
        ollama_instructions = [
            "install ollama",
            "brew install ollama",
            "ollama serve",
            "start ollama"
        ]

        assert any(instruction in output for instruction in ollama_instructions)

    async def test_all_components_unavailable(self, cli_runner, mock_all_unavailable, mock_setup_services):
        """Test handling when all external components are unavailable."""
        setup_service = mock_setup_services['setup_service']
        setup_service.detect_components.return_value = mock_all_unavailable

        from src.models.setup_types import ExternalDependencyError
        setup_service.run_interactive_setup.side_effect = ExternalDependencyError(
            "No required external components are available"
        )

        result = cli_runner.invoke(main, ['setup'])

        assert result.exit_code == 3

        # Should indicate multiple missing components
        output = result.output.lower()
        assert "docker" in output
        assert "ollama" in output

    async def test_component_detection_display_missing(self, cli_runner, mock_docker_unavailable, mock_setup_services):
        """Test component detection properly displays missing components."""
        setup_service = mock_setup_services['setup_service']
        setup_service.detect_components.return_value = mock_docker_unavailable

        from src.models.setup_types import ExternalDependencyError
        setup_service.run_interactive_setup.side_effect = ExternalDependencyError("Dependencies missing")

        result = cli_runner.invoke(main, ['setup'])

        # Should show component detection results with clear status
        output = result.output
        assert "❌" in output or "not available" in output.lower()
        assert "✅" in output or "available" in output.lower()  # Ollama is available

    async def test_partial_setup_when_some_components_missing(self, cli_runner, mock_docker_unavailable, mock_setup_services):
        """Test partial setup completion when some components are missing."""
        setup_service = mock_setup_services['setup_service']
        setup_service.detect_components.return_value = mock_docker_unavailable

        # Mock partial setup completion (Ollama available, Docker not)
        setup_service.run_interactive_setup.return_value = False  # Partial completion

        result = cli_runner.invoke(main, ['setup'])

        # May succeed with warnings or fail gracefully
        assert result.exit_code in [0, 1, 3]  # Allow different handling strategies

        # Should indicate what was/wasn't configured
        output = result.output.lower()
        assert "docker" in output or "vector storage" in output

    async def test_rerun_setup_after_fixing_issues(self, cli_runner, mock_setup_services):
        """Test that setup can be rerun after fixing component issues."""
        setup_service = mock_setup_services['setup_service']

        # First run: Docker unavailable
        docker_unavailable = {
            'docker': {'available': False, 'error_message': 'Docker not running'},
            'ollama': {'available': True, 'health_status': 'healthy'},
            'claude_code': {'available': False}
        }

        setup_service.detect_components.return_value = docker_unavailable
        from src.models.setup_types import ExternalDependencyError
        setup_service.run_interactive_setup.side_effect = ExternalDependencyError("Docker not available")

        result1 = cli_runner.invoke(main, ['setup'])
        assert result1.exit_code == 3

        # Second run: Docker now available (user fixed the issue)
        docker_available = {
            'docker': {'available': True, 'version': '24.0.5', 'health_status': 'healthy'},
            'ollama': {'available': True, 'health_status': 'healthy'},
            'claude_code': {'available': False}
        }

        setup_service.detect_components.return_value = docker_available
        setup_service.run_interactive_setup.side_effect = None
        setup_service.run_interactive_setup.return_value = True

        result2 = cli_runner.invoke(main, ['setup'])
        assert result2.exit_code == 0

        # Should complete successfully after fixing issues
        assert "success" in result2.output.lower() or "✅" in result2.output

    async def test_component_health_degraded_handling(self, cli_runner, mock_setup_services):
        """Test handling of degraded but available components."""
        setup_service = mock_setup_services['setup_service']

        # Mock degraded Docker (old version, limited functionality)
        degraded_components = {
            'docker': {
                'available': True,
                'version': '20.10.8',  # Older version
                'health_status': 'degraded',
                'error_message': 'Docker version is outdated, some features may not work'
            },
            'ollama': {
                'available': True,
                'health_status': 'healthy'
            },
            'claude_code': {
                'available': False
            }
        }

        setup_service.detect_components.return_value = degraded_components
        setup_service.run_interactive_setup.return_value = True  # Can proceed with degraded components

        result = cli_runner.invoke(main, ['setup'])

        # Should complete but show warnings
        assert result.exit_code == 0
        output = result.output.lower()
        assert "warning" in output or "degraded" in output or "⚠️" in result.output

    async def test_auto_mode_missing_components(self, cli_runner, mock_docker_unavailable, mock_setup_services):
        """Test auto mode behavior with missing components."""
        setup_service = mock_setup_services['setup_service']
        setup_service.detect_components.return_value = mock_docker_unavailable

        from src.models.setup_types import ExternalDependencyError
        setup_service.run_auto_setup.side_effect = ExternalDependencyError(
            "Required components not available for auto setup"
        )

        result = cli_runner.invoke(main, ['setup', '--auto'])

        # Auto mode should also handle missing components gracefully
        assert result.exit_code == 3

        # Should not prompt user in auto mode
        assert "[Y/n]" not in result.output
        assert "docker" in result.output.lower()


# This test file should initially FAIL as the missing component handling is not yet implemented.
# Tests will pass once graceful degradation and error handling are properly implemented.