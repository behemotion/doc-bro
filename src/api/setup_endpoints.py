"""Setup API endpoints for DocBro.

FastAPI router for setup-related API endpoints.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import Dict, Any
from uuid import UUID

from ..services.setup_logic_service import SetupLogicService
from ..models.setup_types import SessionNotFoundError


setup_router = APIRouter(prefix="/setup", tags=["setup"])


def get_setup_service() -> SetupLogicService:
    """Get setup service instance."""
    return SetupLogicService()


@setup_router.post("/start")
async def start_setup(
    request: Dict[str, Any],
    setup_service: SetupLogicService = Depends(get_setup_service)
) -> Dict[str, Any]:
    """Start a new setup session."""
    setup_mode = request.get("setup_mode", "interactive")
    force_restart = request.get("force_restart", False)

    if setup_mode not in ["interactive", "auto"]:
        raise HTTPException(status_code=400, detail="Invalid setup mode")

    return await setup_service.create_setup_session(setup_mode, force_restart)


@setup_router.get("/session/{session_id}/status")
async def get_setup_status(
    session_id: str,
    setup_service: SetupLogicService = Depends(get_setup_service)
) -> Dict[str, Any]:
    """Get setup session status."""
    try:
        return await setup_service.get_session_status(session_id)
    except SessionNotFoundError:
        raise HTTPException(status_code=404, detail="Session not found")


@setup_router.get("/session/{session_id}/components")
async def get_component_availability(
    session_id: str,
    setup_service: SetupLogicService = Depends(get_setup_service)
) -> Dict[str, Any]:
    """Get component availability."""
    return await setup_service.get_component_availability(session_id)


@setup_router.put("/session/{session_id}/configure")
async def configure_components(
    session_id: str,
    config_data: Dict[str, Any],
    setup_service: SetupLogicService = Depends(get_setup_service)
) -> Dict[str, Any]:
    """Configure setup components."""
    return await setup_service.configure_components(session_id, config_data)


@setup_router.post("/session/{session_id}/execute")
async def execute_setup(
    session_id: str,
    setup_service: SetupLogicService = Depends(get_setup_service)
) -> Dict[str, Any]:
    """Execute setup steps."""
    return await setup_service.execute_setup(session_id)