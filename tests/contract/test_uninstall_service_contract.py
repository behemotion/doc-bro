"""
Contract test for UninstallServiceContract interface.
These tests define the interface for uninstall service implementation.
They MUST FAIL initially before implementation is created.
"""
import pytest
from unittest.mock import Mock, MagicMock
from typing import Dict, List, Any
from dataclasses import dataclass

# Expected interface contracts that implementation must satisfy
@dataclass
class UninstallComponent:
    name: str
    type: str
    location: str
    size_mb: float
    contains_user_data: bool

@dataclass
class UninstallWarning:
    message: str
    data_types: List[str]
    is_irreversible: bool
    estimated_data_loss: str

class UninstallServiceContract:
    """Contract interface for the uninstall service implementation"""

    def scan_installed_components(self) -> List[UninstallComponent]:
        """Scan and inventory all DocBro components for removal (FR-009)"""
        raise NotImplementedError

    def check_running_services(self) -> List[str]:
        """Check for running DocBro services (for automatic shutdown)"""
        raise NotImplementedError

    def generate_uninstall_warning(self) -> UninstallWarning:
        """Generate single confirmation warning (FR-007, FR-008)"""
        raise NotImplementedError

    def stop_all_services(self) -> bool:
        """Automatically stop all running services (clarification answer)"""
        raise NotImplementedError

    def execute_uninstall(self, confirmed: bool) -> bool:
        """Execute complete uninstall after confirmation (FR-010)"""
        raise NotImplementedError

    def rollback_uninstall(self) -> bool:
        """Rollback partial uninstall if process fails"""
        raise NotImplementedError

class ConfirmationDialogContract:
    """Contract for user confirmation dialog"""

    def show_warning(self, warning: UninstallWarning) -> bool:
        """Show warning and get user confirmation"""
        raise NotImplementedError

class TestUninstallServiceContract:
    """Contract tests that UninstallService implementation must pass"""

    @pytest.fixture
    def uninstall_service(self):
        """This will be overridden with actual implementation"""
        try:
            from src.services.uninstall_service import UninstallService
            return UninstallService()
        except ImportError:
            # Should FAIL initially - no implementation exists yet
            pytest.fail("UninstallService implementation not found - create src/services/uninstall_service.py")

    def test_component_scanning_comprehensive(self, uninstall_service):
        """Test complete inventory of all DocBro components"""
        components = uninstall_service.scan_installed_components()

        assert isinstance(components, list)
        assert len(components) > 0

        # Must identify all major component types
        component_types = {comp.type for comp in components}
        expected_types = {"docker_container", "data_directory", "config_file", "cache_directory"}
        assert expected_types.issubset(component_types)

        # Must identify user data components (per FR-009)
        user_data_components = [comp for comp in components if comp.contains_user_data]
        assert len(user_data_components) > 0

        # Must include crawl data and embeddings specifically
        component_names = [comp.name.lower() for comp in components]
        crawl_found = any("crawl" in name or "doc" in name for name in component_names)
        embed_found = any("embed" in name or "vector" in name for name in component_names)
        assert crawl_found or embed_found  # At least one type of user data

    def test_running_service_detection(self, uninstall_service):
        """Test detection of running services for automatic shutdown"""
        services = uninstall_service.check_running_services()
        assert isinstance(services, list)

    def test_single_confirmation_warning(self, uninstall_service):
        """Test FR-007: Single confirmation prompt with clear consequences"""
        warning = uninstall_service.generate_uninstall_warning()

        assert isinstance(warning, UninstallWarning)

        # Must clearly state irreversibility (FR-008)
        assert warning.is_irreversible is True
        message_lower = warning.message.lower()
        assert "irreversible" in message_lower or "permanent" in message_lower

        # Must mention specific data loss (FR-009)
        data_keywords = ["crawl", "embed", "data", "document"]
        assert any(keyword in message_lower for keyword in data_keywords)

        # Must provide size estimate
        assert warning.estimated_data_loss is not None
        assert len(warning.estimated_data_loss) > 0

    def test_automatic_service_shutdown(self, uninstall_service):
        """Test clarification: automatically stop services before uninstall"""
        result = uninstall_service.stop_all_services()
        assert isinstance(result, bool)

    def test_complete_component_removal(self, uninstall_service):
        """Test FR-010: Clean removal of all components"""
        # Must require confirmation
        result_confirmed = uninstall_service.execute_uninstall(confirmed=True)
        assert isinstance(result_confirmed, bool)

        # Must handle denial appropriately
        result_denied = uninstall_service.execute_uninstall(confirmed=False)
        assert isinstance(result_denied, bool)

    def test_qdrant_container_removal(self, uninstall_service):
        """Test removal of standardized Qdrant container"""
        components = uninstall_service.scan_installed_components()

        # Should find Docker containers
        container_components = [c for c in components if c.type == "docker_container"]

        # If Qdrant is installed, must find standardized name
        qdrant_containers = [c for c in container_components if "qdrant" in c.name.lower()]
        if qdrant_containers:
            standard_name_found = any("docbro-memory-qdrant" in c.name for c in qdrant_containers)
            assert standard_name_found, "Qdrant container must use standard 'docbro-memory-qdrant' name"

    def test_data_loss_estimation(self, uninstall_service):
        """Test that data loss is quantified for user awareness"""
        warning = uninstall_service.generate_uninstall_warning()

        assert isinstance(warning.estimated_data_loss, str)
        assert len(warning.estimated_data_loss) > 0

        # Should contain size information (GB, MB, etc.)
        size_indicators = ["gb", "mb", "kb", "byte"]
        loss_str = warning.estimated_data_loss.lower()
        assert any(indicator in loss_str for indicator in size_indicators)

    def test_rollback_capability(self, uninstall_service):
        """Test rollback for failed uninstall operations"""
        result = uninstall_service.rollback_uninstall()
        assert isinstance(result, bool)

    def test_configuration_cleanup(self, uninstall_service):
        """Test removal of configuration files and MCP settings"""
        components = uninstall_service.scan_installed_components()
        config_files = [c for c in components if c.type == "config_file"]

        # Must identify configuration files for removal
        assert len(config_files) > 0
        config_names = [c.name.lower() for c in config_files]
        assert any("config" in name or "mcp" in name for name in config_names)

class TestConfirmationDialogContract:
    """Contract tests for confirmation dialog implementation"""

    @pytest.fixture
    def dialog(self):
        """This will be overridden with actual implementation"""
        try:
            from src.services.confirmation_dialog import ConfirmationDialog
            return ConfirmationDialog()
        except ImportError:
            pytest.fail("ConfirmationDialog implementation not found - create src/services/confirmation_dialog.py")

    def test_single_prompt_requirement(self, dialog):
        """Test FR-007: Only one confirmation prompt"""
        warning = UninstallWarning(
            message="Test warning message about irreversible data loss",
            data_types=["test_data"],
            is_irreversible=True,
            estimated_data_loss="1 GB"
        )

        result = dialog.show_warning(warning)
        assert isinstance(result, bool)

class TestUninstallPerformanceContract:
    """Performance requirements for uninstall operations"""

    @pytest.fixture
    def uninstall_service(self):
        try:
            from src.services.uninstall_service import UninstallService
            return UninstallService()
        except ImportError:
            pytest.fail("UninstallService implementation not found")

    @pytest.mark.performance
    def test_confirmation_under_3_seconds(self, uninstall_service):
        """Test performance: <3s uninstall confirmation (from Technical Context)"""
        import time

        start_time = time.time()
        warning = uninstall_service.generate_uninstall_warning()
        duration = time.time() - start_time

        assert duration < 3.0, f"Uninstall confirmation took {duration:.2f}s, required <3s"
        assert isinstance(warning, UninstallWarning)

    @pytest.mark.performance
    def test_component_scanning_efficient(self, uninstall_service):
        """Test that component scanning is reasonably fast"""
        import time

        start_time = time.time()
        components = uninstall_service.scan_installed_components()
        duration = time.time() - start_time

        assert duration < 10.0, f"Component scanning took {duration:.2f}s, should be <10s"
        assert isinstance(components, list)

class TestUninstallIntegrationContract:
    """Integration contract requirements"""

    @pytest.fixture
    def uninstall_service(self):
        try:
            from src.services.uninstall_service import UninstallService
            return UninstallService()
        except ImportError:
            pytest.fail("UninstallService implementation not found")

    def test_service_shutdown_before_removal(self, uninstall_service):
        """Test that services are stopped before component removal"""
        # This contract ensures the sequence is correct
        services = uninstall_service.check_running_services()
        assert isinstance(services, list)

        # If services are running, must be able to stop them
        if services:
            stop_result = uninstall_service.stop_all_services()
            assert isinstance(stop_result, bool)

    def test_no_partial_uninstall_state(self, uninstall_service):
        """Test that system doesn't remain in broken partial state"""
        # Contract ensures either complete success or complete rollback
        # Actual validation through integration testing
        rollback_result = uninstall_service.rollback_uninstall()
        assert isinstance(rollback_result, bool)