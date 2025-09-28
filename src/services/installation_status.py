"""Installation status service for tracking installation progress."""

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field

from .installation_wizard import InstallationWizardService


class InstallationStateEnum(str, Enum):
    """Installation status enum for API responses."""
    PENDING = "pending"
    INITIALIZING = "initializing"
    DOWNLOADING = "downloading"
    INSTALLING = "installing"
    CONFIGURING = "configuring"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class InstallationStatusResponse(BaseModel):
    """Response model for installation status endpoint."""
    id: str = Field(..., description="Installation UUID")
    state: InstallationStateEnum = Field(..., description="Current installation state")
    progress: int = Field(ge=0, le=100, description="Installation progress percentage")
    message: str | None = Field(None, description="Status message")
    error: str | None = Field(None, description="Error message if failed")
    started_at: datetime = Field(..., description="Installation start time")
    completed_at: datetime | None = Field(None, description="Installation completion time")
    metadata: dict[str, Any] = Field(default_factory=dict, description="Additional metadata")


class InstallationStatusService:
    """Service for managing installation status tracking."""

    def __init__(self):
        """Initialize installation status service."""
        self.installation_wizard = InstallationWizardService()

    def _map_wizard_state_to_api_state(self, wizard_phase: str) -> InstallationStateEnum:
        """Map wizard phase to API state enum.

        Args:
            wizard_phase: Phase from InstallationWizardService

        Returns:
            Corresponding InstallationStateEnum value
        """
        phase_mapping = {
            "initializing": InstallationStateEnum.INITIALIZING,
            "system_check": InstallationStateEnum.INITIALIZING,
            "service_setup": InstallationStateEnum.INSTALLING,
            "configuration": InstallationStateEnum.CONFIGURING,
            "finalization": InstallationStateEnum.INSTALLING,
            "complete": InstallationStateEnum.COMPLETED,
            "error": InstallationStateEnum.FAILED
        }

        return phase_mapping.get(wizard_phase, InstallationStateEnum.PENDING)

    async def get_installation_status(self, installation_id: str) -> InstallationStatusResponse | None:
        """Get installation status by ID.

        Args:
            installation_id: UUID of the installation

        Returns:
            InstallationStatusResponse if found, None if not found

        Raises:
            ValueError: If installation_id is not a valid UUID format
        """
        # Validate UUID format
        try:
            uuid.UUID(installation_id)
        except ValueError:
            raise ValueError(f"Invalid UUID format: {installation_id}")

        # Load installation state from wizard service
        wizard_state = await self.installation_wizard.load_installation_state()
        wizard_profile = await self.installation_wizard.load_installation_profile()

        # If no installation state or profile, return None (404)
        if not wizard_state or not wizard_profile:
            return None

        # Check if the installation ID matches
        if str(wizard_profile.id) != installation_id:
            return None

        # Map wizard state to API response
        api_state = self._map_wizard_state_to_api_state(wizard_state.current_phase)

        # Calculate progress percentage
        progress = int(wizard_state.progress_percentage)

        # Determine message
        message = wizard_state.status_message

        # Determine error
        error = wizard_state.error_details if wizard_state.error_occurred else None

        # Determine completion time
        completed_at = None
        if wizard_state.current_phase in ["complete", "error"]:
            # Use profile completion time if available
            if hasattr(wizard_profile, 'completed_at') and wizard_profile.completed_at:
                completed_at = wizard_profile.completed_at
            elif wizard_state.current_phase == "complete":
                # If completed but no completion time, use current time
                completed_at = datetime.now()

        # Build metadata
        metadata = {
            "install_method": wizard_profile.install_method,
            "python_version": wizard_profile.python_version,
            "uv_version": wizard_profile.uv_version,
            "services_detected": [],  # Would come from service detection
            "config_validated": wizard_state.current_phase in ["complete"]
        }

        # Adjust state-specific values
        if api_state == InstallationStateEnum.PENDING:
            progress = 0
        elif api_state == InstallationStateEnum.COMPLETED:
            progress = 100
            if not completed_at:
                completed_at = datetime.now()
        elif api_state == InstallationStateEnum.FAILED:
            if not completed_at:
                completed_at = datetime.now()

        return InstallationStatusResponse(
            id=installation_id,
            state=api_state,
            progress=progress,
            message=message,
            error=error,
            started_at=wizard_profile.created_at,
            completed_at=completed_at,
            metadata=metadata
        )

    async def create_mock_installation_status(self, installation_id: str) -> InstallationStatusResponse:
        """Create a mock installation status for testing.

        This method creates a realistic installation status for testing purposes
        when no real installation is found.

        Args:
            installation_id: UUID of the installation

        Returns:
            InstallationStatusResponse with mock data
        """
        # Validate UUID format
        try:
            uuid.UUID(installation_id)
        except ValueError:
            raise ValueError("Invalid UUID format")

        # Create mock installation in progress
        return InstallationStatusResponse(
            id=installation_id,
            state=InstallationStateEnum.INSTALLING,
            progress=45,
            message="Installing dependencies and setting up configuration...",
            error=None,
            started_at=datetime.now(),
            completed_at=None,
            metadata={
                "install_method": "uvx",
                "python_version": "3.13.1",
                "uv_version": "0.4.0",
                "services_detected": ["docker", "ollama"],
                "config_validated": False
            }
        )
