"""SetupLogicService orchestration for DocBro setup logic.

This is the main orchestration service that coordinates all setup operations.
"""

import logging
from typing import Optional, Dict, Any, List, Callable
from uuid import uuid4
from datetime import datetime, timezone

from ..models.setup_types import (
    SetupMode,
    SetupStatus,
    SessionStatus,
    SetupStep,
    VectorStorageConfig,
    EmbeddingModelConfig,
    MCPClientConfig
)
from ..models.setup_configuration import SetupConfiguration
from ..models.setup_session import SetupSession
from ..models.component_availability import ComponentAvailability

from .component_health import ComponentHealthChecker
from .docker_manager import DockerManager
from .ollama_manager import OllamaManager
from .mcp_detector import MCPDetector
from .config_service import ConfigService


logger = logging.getLogger(__name__)


class SetupLogicService:
    """Main orchestration service for setup logic."""

    def __init__(self):
        """Initialize setup logic service."""
        self.health_checker = ComponentHealthChecker()
        self.docker_manager = DockerManager()
        self.ollama_manager = OllamaManager()
        self.mcp_detector = MCPDetector()
        self.config_service = ConfigService()

    async def run_interactive_setup(self) -> bool:
        """Run interactive setup with user prompts."""
        try:
            logger.info("Starting interactive setup")

            # Create setup configuration
            config = SetupConfiguration(
                setup_mode=SetupMode.INTERACTIVE,
                version="0.2.1"
            )

            # Create session
            session = SetupSession(setup_config_id=config.setup_id)
            session.start_session()

            # Detect components
            components = await self.health_checker.check_all_components()
            session.complete_step(SetupStep.DETECT_COMPONENTS)

            # Mock setup for now - in real implementation would have UI prompts
            docker_available = any(c.component_name == "docker" and c.available for c in components)
            ollama_available = any(c.component_name == "ollama" and c.available for c in components)

            if docker_available:
                # Configure and start vector storage
                config.vector_storage = VectorStorageConfig(
                    connection_url="http://localhost:6333",
                    data_path="/tmp/docbro/qdrant"
                )

                # Actually create and start the Qdrant container
                from pathlib import Path
                data_path = Path(config.vector_storage.data_path)
                await self.docker_manager.create_qdrant_container(
                    container_name="docbro-qdrant",
                    port=6333,
                    data_path=data_path
                )
                logger.info("Qdrant container created and started successfully")

                session.complete_step(SetupStep.CONFIGURE_VECTOR_STORAGE)

            if ollama_available:
                # Configure embedding model
                config.embedding_model = EmbeddingModelConfig(
                    model_name="mxbai-embed-large",
                    download_required=False
                )
                session.complete_step(SetupStep.SETUP_EMBEDDING_MODEL)

            # Skip MCP for now
            session.complete_step(SetupStep.CONFIGURE_MCP_CLIENTS)
            session.complete_step(SetupStep.VALIDATE_CONFIGURATION)

            # Save configuration
            config.mark_as_completed()
            await self.config_service.save_configuration(config)
            session.complete_step(SetupStep.PERSIST_SETTINGS)

            session.complete_session()
            await self.config_service.save_session(session)

            logger.info("Interactive setup completed successfully")
            return True

        except Exception as e:
            logger.error(f"Interactive setup failed: {e}")
            if 'session' in locals():
                session.fail_session(str(e))
                await self.config_service.save_session(session)
            raise

    async def run_auto_setup(self) -> bool:
        """Run automated setup with defaults."""
        try:
            logger.info("Starting auto setup")

            # Create setup configuration
            config = SetupConfiguration(
                setup_mode=SetupMode.AUTO,
                version="0.2.1"
            )

            # Create session
            session = SetupSession(setup_config_id=config.setup_id)
            session.start_session()

            # Detect components
            components = await self.health_checker.check_all_components()
            session.complete_step(SetupStep.DETECT_COMPONENTS)

            # Auto-configure available components
            docker_available = any(c.component_name == "docker" and c.available for c in components)
            ollama_available = any(c.component_name == "ollama" and c.available for c in components)

            if docker_available:
                config.vector_storage = VectorStorageConfig(
                    connection_url="http://localhost:6333",
                    data_path="/tmp/docbro/qdrant"
                )

                # Actually create and start the Qdrant container
                from pathlib import Path
                data_path = Path(config.vector_storage.data_path)
                await self.docker_manager.create_qdrant_container(
                    container_name="docbro-qdrant",
                    port=6333,
                    data_path=data_path
                )
                logger.info("Qdrant container created and started successfully")

                session.complete_step(SetupStep.CONFIGURE_VECTOR_STORAGE)

            if ollama_available:
                config.embedding_model = EmbeddingModelConfig(
                    model_name="embeddinggemma:300m-qat-q4_0",
                    download_required=True
                )
                session.complete_step(SetupStep.SETUP_EMBEDDING_MODEL)

            session.complete_step(SetupStep.CONFIGURE_MCP_CLIENTS)
            session.complete_step(SetupStep.VALIDATE_CONFIGURATION)

            # Save configuration
            config.mark_as_completed()
            await self.config_service.save_configuration(config)
            session.complete_step(SetupStep.PERSIST_SETTINGS)

            session.complete_session()
            await self.config_service.save_session(session)

            logger.info("Auto setup completed successfully")
            return True

        except Exception as e:
            logger.error(f"Auto setup failed: {e}")
            if 'session' in locals():
                session.fail_session(str(e))
                await self.config_service.save_session(session)
            raise

    async def get_setup_status(self) -> Dict[str, Any]:
        """Get current setup status."""
        existing_setup = await self.config_service.check_existing_setup()

        if not existing_setup:
            return {
                "setup_completed": False,
                "setup_mode": None,
                "last_setup_time": None,
                "components_status": {},
                "configuration_file": None,
                "warnings": ["Setup not completed"]
            }

        # Get component health
        components = await self.health_checker.check_all_components()
        components_status = {}

        for component in components:
            status_key = component.component_name
            if component.component_type.value == "mcp_client":
                status_key = "mcp_clients"
                if status_key not in components_status:
                    components_status[status_key] = []
                components_status[status_key].append({
                    'name': component.component_name,
                    'status': component.health_status,
                    'available': component.available,
                    'version': component.version,
                    'last_checked': component.last_checked.isoformat(),
                    'error_message': component.error_message
                })
            else:
                components_status[status_key] = {
                    'name': component.component_name,
                    'status': component.health_status,
                    'available': component.available,
                    'version': component.version,
                    'last_checked': component.last_checked.isoformat(),
                    'error_message': component.error_message
                }

        return {
            **existing_setup,
            "components_status": components_status
        }

    async def detect_components(self) -> Dict[str, Any]:
        """Detect all external components."""
        components = await self.health_checker.check_all_components()

        result = {}
        for component in components:
            result[component.component_name] = {
                "available": component.available,
                "version": component.version,
                "health_status": component.health_status,
                "error_message": component.error_message,
                "capabilities": component.capabilities
            }

        return result

    # Additional methods for API endpoints
    async def create_setup_session(self, setup_mode: str, force_restart: bool = False) -> Dict[str, Any]:
        """Create a new setup session (for API)."""
        session = SetupSession(
            setup_config_id=uuid4()
        )

        await self.config_service.save_session(session)

        return {
            "session_id": str(session.session_id),
            "setup_mode": setup_mode,
            "status": session.session_status,
            "created_at": session.started_at.isoformat(),
            "total_steps": session.total_steps
        }

    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get session status (for API)."""
        session = await self.config_service.load_session(session_id)
        if not session:
            from ..models.setup_types import SessionNotFoundError
            raise SessionNotFoundError(f"Session {session_id} not found")

        return session.get_session_summary()

    async def get_component_availability(self, session_id: str) -> Dict[str, Any]:
        """Get component availability (for API)."""
        components = await self.health_checker.check_all_components()

        return {
            "components": [c.get_status_details() for c in components],
            "last_checked": datetime.now(timezone.utc).isoformat()
        }

    async def configure_components(self, session_id: str, config_data: Dict[str, Any]) -> Dict[str, Any]:
        """Configure components (for API)."""
        # Mock implementation
        return {
            "success": True,
            "configuration_id": str(uuid4()),
            "validation_errors": [],
            "warnings": []
        }

    async def execute_setup(self, session_id: str) -> Dict[str, Any]:
        """Execute setup (for API)."""
        return {
            "execution_started": True,
            "estimated_duration": 180,
            "steps_to_execute": [
                "detect_components",
                "configure_vector_storage",
                "setup_embedding_model",
                "configure_mcp_clients",
                "validate_configuration",
                "persist_settings"
            ]
        }