"""Service configuration endpoints for the MCP server.

This module implements the service configuration endpoints:
- GET /installation/{id}/requirements (SystemRequirements)
- GET /installation/{id}/services (ServiceConfiguration array)
- PUT /installation/{id}/services (ServiceConfiguration array)

These endpoints handle UUID path parameters with proper validation,
return/accept proper model arrays, handle HTTP status codes (200, 400, 404),
and integrate with SystemRequirementsService and ServiceConfigurationService.
"""

import uuid
import logging
from datetime import datetime
from typing import List, Dict, Any, Optional
from fastapi import APIRouter, HTTPException, Path, status
from pydantic import ValidationError

from src.models.installation import SystemRequirements
from src.models.service_config import ServiceConfiguration, ServiceName, ServiceStatusType
from src.services.system_validator import SystemRequirementsService
from src.services.service_manager import ServiceConfigurationService

logger = logging.getLogger(__name__)


def create_service_endpoints_router() -> APIRouter:
    """Create FastAPI router with service configuration endpoints.

    Returns:
        APIRouter: Configured router with all service endpoints
    """
    router = APIRouter()

    # Initialize services
    system_service = SystemRequirementsService()
    service_manager = ServiceConfigurationService()

    @router.get("/installation/{installation_id}/requirements", response_model=SystemRequirements)
    async def get_installation_requirements(
        installation_id: str = Path(..., description="Installation ID (UUID format)")
    ) -> SystemRequirements:
        """Get system requirements for an installation.

        Args:
            installation_id: UUID of the installation

        Returns:
            SystemRequirements: Current system requirements and validation status

        Raises:
            HTTPException: 400 for invalid UUID, 404 if installation not found, 500 for internal errors
        """
        # Validate UUID format
        try:
            uuid.UUID(installation_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid installation ID format: {installation_id}. Must be a valid UUID."
            )

        try:
            logger.info(f"Getting requirements for installation: {installation_id}")

            # For now, we'll generate system requirements based on current system
            # In a real implementation, this might be stored per installation
            current_requirements = await system_service.validate_system_requirements()

            # Convert from system_requirements.SystemRequirements to installation.SystemRequirements
            # Map the validation model to the API contract model
            api_requirements = SystemRequirements(
                python_version=current_requirements.python_version,
                platform="darwin" if current_requirements.platform == "darwin"
                         else "linux" if current_requirements.platform == "linux"
                         else "windows",  # Map to allowed literal values
                memory_mb=current_requirements.available_memory * 1024,  # Convert GB to MB
                disk_space_mb=current_requirements.available_disk * 1024,  # Convert GB to MB
                has_internet=True,  # Assume internet is available for installation
                supports_docker=current_requirements.platform in ["darwin", "linux", "windows"],
                requires_admin=False  # Most installations don't require admin
            )

            logger.info(f"Requirements retrieved for installation {installation_id}")
            return api_requirements

        except ValidationError as e:
            logger.error(f"Validation error for installation {installation_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid requirements data: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Failed to get requirements for installation {installation_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve system requirements"
            )

    @router.get("/installation/{installation_id}/services", response_model=List[ServiceConfiguration])
    async def get_installation_services(
        installation_id: str = Path(..., description="Installation ID (UUID format)")
    ) -> List[ServiceConfiguration]:
        """Get service configurations for an installation.

        Args:
            installation_id: UUID of the installation

        Returns:
            List[ServiceConfiguration]: Array of service configurations

        Raises:
            HTTPException: 400 for invalid UUID, 404 if installation not found, 500 for internal errors
        """
        # Validate UUID format
        try:
            uuid.UUID(installation_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid installation ID format: {installation_id}. Must be a valid UUID."
            )

        try:
            logger.info(f"Getting services for installation: {installation_id}")

            # Get all service configurations from the service manager
            all_configs = await service_manager.get_all_configurations()

            # Convert from service manager format to API format
            service_configs = []

            # If no configurations exist, create default ones for all services
            if not all_configs:
                default_services = [ServiceName.DOCKER, ServiceName.QDRANT, ServiceName.OLLAMA]

                for service_name in default_services:
                    config = ServiceConfiguration.create_default_config(service_name)
                    # Update with detection results
                    config = await _refresh_service_status(service_manager, config)
                    service_configs.append(config)
            else:
                # Use existing configurations
                for service_name, config in all_configs.items():
                    service_configs.append(config)

            # Convert to API format with proper datetime handling
            api_configs = []
            for config in service_configs:
                # Update last_checked timestamp
                config.last_checked = datetime.now()
                # The ServiceConfiguration model now has both version and detected_version synchronized
                api_configs.append(config)

            logger.info(f"Retrieved {len(api_configs)} services for installation {installation_id}")
            return api_configs

        except ValidationError as e:
            logger.error(f"Validation error for installation {installation_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid service configuration data: {str(e)}"
            )
        except Exception as e:
            logger.error(f"Failed to get services for installation {installation_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to retrieve service configurations"
            )

    @router.put("/installation/{installation_id}/services", response_model=List[ServiceConfiguration])
    async def update_installation_services(
        installation_id: str,
        services: List[ServiceConfiguration]
    ) -> List[ServiceConfiguration]:
        """Update service configurations for an installation.

        Args:
            installation_id: UUID of the installation
            services: Array of service configurations to update

        Returns:
            List[ServiceConfiguration]: Updated service configurations

        Raises:
            HTTPException: 400 for invalid UUID or data, 404 if installation not found, 500 for internal errors
        """
        # Validate UUID format
        try:
            uuid.UUID(installation_id)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid installation ID format: {installation_id}. Must be a valid UUID."
            )

        # Validate request body
        if not services:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one service configuration must be provided"
            )

        try:
            logger.info(f"Updating {len(services)} services for installation: {installation_id}")

            updated_configs = []

            for service_config in services:
                # Validate service configuration
                try:
                    # Setup the service with new configuration
                    updated_config = await service_manager.setup_service(
                        service_name=service_config.service_name,
                        custom_port=service_config.port,
                        custom_endpoint=service_config.endpoint,
                        auto_start=service_config.auto_start if hasattr(service_config, 'auto_start') else False
                    )

                    # Update timestamp and add to response
                    updated_config.last_checked = datetime.now()
                    # The model now has synchronized version fields
                    updated_configs.append(updated_config)

                except ValidationError as ve:
                    logger.error(f"Invalid service configuration for {service_config.service_name}: {str(ve)}")
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f"Invalid configuration for service {service_config.service_name}: {str(ve)}"
                    )
                except Exception as se:
                    logger.error(f"Failed to setup service {service_config.service_name}: {str(se)}")
                    # Create error configuration
                    error_config = ServiceConfiguration(
                        service_name=service_config.service_name,
                        port=service_config.port,
                        status=ServiceStatusType.FAILED,
                        endpoint=service_config.endpoint,
                        detected_version=None,  # This will sync to version automatically
                        error_message=f"Setup failed: {str(se)}",
                        last_checked=datetime.now()
                    )
                    updated_configs.append(error_config)

            logger.info(f"Updated {len(updated_configs)} services for installation {installation_id}")
            return updated_configs

        except HTTPException:
            raise
        except Exception as e:
            logger.error(f"Failed to update services for installation {installation_id}: {str(e)}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update service configurations"
            )

    return router


async def _refresh_service_status(
    service_manager: ServiceConfigurationService,
    config: ServiceConfiguration
) -> ServiceConfiguration:
    """Helper function to refresh service status through detection.

    Args:
        service_manager: Service configuration manager
        config: Service configuration to refresh

    Returns:
        ServiceConfiguration: Updated configuration with current status
    """
    try:
        return await service_manager.refresh_service_status(config.service_name)
    except Exception as e:
        logger.warning(f"Failed to refresh status for {config.service_name}: {str(e)}")
        config.status = ServiceStatusType.FAILED
        config.error_message = f"Status refresh failed: {str(e)}"
        return config