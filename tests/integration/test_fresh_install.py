"""Integration test for fresh installation scenario."""

import pytest
import tempfile
import shutil
import asyncio
from pathlib import Path
from datetime import datetime
from unittest.mock import patch, Mock, AsyncMock

from src.services.config import ConfigService
from src.services.detection import ServiceDetectionService
from src.services.setup import SetupWizardService
from src.models.installation import InstallationContext, ServiceStatus


@pytest.mark.integration
class TestFreshInstallScenario:
    """Test complete fresh installation workflow."""

    @pytest.fixture
    def temp_home(self):
        """Create temporary home directory for testing."""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def mock_platformdirs(self, temp_home):
        """Mock platformdirs to use temp directory."""
        with patch('platformdirs.user_config_dir') as mock_config, \
             patch('platformdirs.user_data_dir') as mock_data, \
             patch('platformdirs.user_cache_dir') as mock_cache:

            mock_config.return_value = str(temp_home / ".config" / "docbro")
            mock_data.return_value = str(temp_home / ".local" / "share" / "docbro")
            mock_cache.return_value = str(temp_home / ".cache" / "docbro")
            yield

    def test_config_service_directory_creation(self, mock_platformdirs, temp_home):
        """Test that ConfigService creates proper XDG directories."""
        config_service = ConfigService()

        # Ensure directories
        config_service.ensure_directories()

        # Verify directories exist
        assert config_service.config_dir.exists()
        assert config_service.data_dir.exists()
        assert config_service.cache_dir.exists()

        # Verify directory permissions (700 - user only)
        assert oct(config_service.config_dir.stat().st_mode)[-3:] == '700'
        assert oct(config_service.data_dir.stat().st_mode)[-3:] == '700'
        assert oct(config_service.cache_dir.stat().st_mode)[-3:] == '700'

    def test_installation_context_creation_and_persistence(self, mock_platformdirs, temp_home):
        """Test installation context creation and file persistence."""
        config_service = ConfigService()

        # Create installation context
        context = config_service.create_installation_context(
            install_method="uvx",
            version="1.0.0",
            python_version="3.13.1",
            uv_version="0.4.0"
        )

        # Verify context fields
        assert context.install_method == "uvx"
        assert context.version == "1.0.0"
        assert context.python_version == "3.13.1"
        assert context.uv_version == "0.4.0"
        assert context.is_global is True

        # Verify configuration file was created
        assert config_service.installation_config_path.exists()

        # Verify we can load it back
        loaded_context = config_service.load_installation_context()
        assert loaded_context is not None
        assert loaded_context.install_method == "uvx"
        assert loaded_context.version == "1.0.0"

    @pytest.mark.asyncio
    async def test_service_detection_integration(self):
        """Test that service detection works with real service checks."""
        detection_service = ServiceDetectionService(timeout=1)

        # Test Docker detection (should work even if Docker not available)
        docker_status = detection_service.check_docker()
        assert isinstance(docker_status, ServiceStatus)
        assert docker_status.name == "docker"
        assert docker_status.last_checked is not None

        # Test async service detection (Redis removed)
        services = await detection_service.check_all_services()
        assert "docker" in services
        assert "ollama" in services
        assert "redis" not in services  # Redis should not be checked
        assert "qdrant" in services

        for service_name, status in services.items():
            assert isinstance(status, ServiceStatus)
            assert status.name == service_name
            assert isinstance(status.available, bool)

    def test_setup_wizard_state_management(self, mock_platformdirs, temp_home):
        """Test setup wizard state persistence and loading."""
        wizard = SetupWizardService()

        # Create new wizard state
        state = wizard.create_wizard_state()
        assert state.current_step == "welcome"
        assert state.setup_start_time is not None
        assert len(state.completed_steps) == 0

        # Save state
        wizard.save_wizard_state(state)

        # Load state back
        loaded_state = wizard.load_wizard_state()
        assert loaded_state is not None
        assert loaded_state.current_step == "welcome"
        assert loaded_state.setup_start_time == state.setup_start_time

        # Update and save state
        state.current_step = "python_check"
        state.completed_steps.append("welcome")
        wizard.save_wizard_state(state)

        # Verify updates
        updated_state = wizard.load_wizard_state()
        assert updated_state.current_step == "python_check"
        assert "welcome" in updated_state.completed_steps

    def test_setup_status_checking(self, mock_platformdirs, temp_home):
        """Test setup status detection before and after setup."""
        wizard = SetupWizardService()

        # Initially, setup should be required
        assert wizard.check_setup_required() is True

        status = wizard.get_setup_status()
        assert status["setup_completed"] is False
        assert status["setup_required"] is True
        assert status["in_progress"] is False

        # Create installation context (simulating completed setup)
        config_service = ConfigService()
        config_service.create_installation_context(
            install_method="uvx",
            version="1.0.0",
            python_version="3.13.1"
        )

        # Now setup should not be required
        assert wizard.check_setup_required() is False

        status = wizard.get_setup_status()
        assert status["setup_completed"] is True
        assert status["setup_required"] is False

    @patch('shutil.which')
    @patch('src.services.config.subprocess.run')
    def test_installation_method_detection(self, mock_subprocess, mock_which, mock_platformdirs, temp_home):
        """Test detection of installation method."""
        config_service = ConfigService()

        # Test uvx installation detection
        mock_which.return_value = "/home/user/.local/bin/docbro"
        mock_subprocess.return_value = Mock(returncode=0, stdout="uv 0.4.0")

        context = config_service.create_installation_context()
        assert context.install_method == "uvx"
        assert context.uv_version == "0.4.0"

        # Test manual installation detection
        mock_which.return_value = "/usr/local/bin/docbro"
        mock_subprocess.return_value = Mock(returncode=1, stdout="")  # UV not found

        context = config_service.create_installation_context()
        assert context.install_method == "manual"
        assert context.uv_version is None

    def test_configuration_file_backup_and_recovery(self, mock_platformdirs, temp_home):
        """Test that configuration files are backed up and can be recovered."""
        config_service = ConfigService()

        # Create initial configuration
        context1 = config_service.create_installation_context(
            install_method="uvx",
            version="1.0.0",
            python_version="3.13.1"
        )

        # Verify backup doesn't exist initially
        backup_path = config_service.installation_config_path.with_suffix('.json.backup')
        assert not backup_path.exists()

        # Save again (should create backup of previous)
        context2 = config_service.create_installation_context(
            install_method="manual",
            version="1.0.1",
            python_version="3.13.1"
        )

        # Now backup should exist
        assert backup_path.exists()

        # Test repair functionality
        # Corrupt the main file
        with open(config_service.installation_config_path, 'w') as f:
            f.write("invalid json")

        # Attempt repair
        results = config_service.repair_configuration()
        assert results["installation"] is True

        # Verify repair worked
        restored_context = config_service.load_installation_context()
        assert restored_context is not None
        assert restored_context.install_method == "uvx"  # Should be from backup

    def test_installation_performance_target(self):
        """Test that core installation operations meet performance targets."""
        import time

        # Test directory creation performance
        start_time = time.time()

        with tempfile.TemporaryDirectory() as temp_dir:
            temp_home = Path(temp_dir)

            with patch('platformdirs.user_config_dir', return_value=str(temp_home / ".config" / "docbro")), \
                 patch('platformdirs.user_data_dir', return_value=str(temp_home / ".local" / "share" / "docbro")), \
                 patch('platformdirs.user_cache_dir', return_value=str(temp_home / ".cache" / "docbro")):

                config_service = ConfigService()
                config_service.ensure_directories()

                # Create and save installation context
                context = config_service.create_installation_context(
                    install_method="uvx",
                    version="1.0.0",
                    python_version="3.13.1"
                )

                # Load it back
                loaded_context = config_service.load_installation_context()
                assert loaded_context is not None

        end_time = time.time()
        duration = end_time - start_time

        # Core configuration operations should complete in well under 1 second
        assert duration < 1.0, f"Installation operations took {duration:.2f}s, should be under 1.0s"

    @pytest.mark.asyncio
    async def test_setup_wizard_skips_redis(self, mock_platformdirs, temp_home):
        """Test that setup wizard doesn't check for Redis."""
        wizard = SetupWizardService()
        detection_service = ServiceDetectionService()

        # Get services to check
        services = await detection_service.check_all_services()

        # Redis should not be in the list of services to check
        assert "redis" not in services

        # Verify setup prompts don't include Redis
        # This would be in the actual wizard flow
        service_prompts = wizard.get_service_prompts()
        assert "redis" not in str(service_prompts).lower()

    def test_fresh_install_without_redis_config(self, mock_platformdirs, temp_home):
        """Test fresh installation doesn't create Redis configuration."""
        config_service = ConfigService()

        # Create installation context
        context = config_service.create_installation_context(
            install_method="uvx",
            version="2.0.0",  # Version after Redis removal
            python_version="3.13.1"
        )

        # Load configuration
        from src.core.config import DocBroConfig
        config = DocBroConfig()

        # Verify no Redis configuration exists
        assert not hasattr(config, 'redis_url')
        assert not hasattr(config, 'redis_password')
        assert not hasattr(config, 'redis_deployment')