"""Data models for setup operations."""

from src.logic.setup.models.operation import SetupOperation, OperationType, OperationStatus
from src.logic.setup.models.configuration import SetupConfiguration
from src.logic.setup.models.menu_state import MenuState
from src.logic.setup.models.service_info import ServiceInfo, ServiceStatus
from src.logic.setup.models.uninstall_manifest import UninstallManifest

__all__ = [
    "SetupOperation",
    "OperationType",
    "OperationStatus",
    "SetupConfiguration",
    "MenuState",
    "ServiceInfo",
    "ServiceStatus",
    "UninstallManifest",
]