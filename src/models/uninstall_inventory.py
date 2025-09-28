"""UninstallInventory model for component cleanup."""
from enum import Enum

from pydantic import BaseModel, ConfigDict, Field


class ComponentType(Enum):
    DOCKER_CONTAINER = "docker_container"
    CONFIG_FILE = "config_file"
    DATA_DIRECTORY = "data_directory"
    CACHE_DIRECTORY = "cache_directory"
    LOG_FILES = "log_files"


class UninstallComponent(BaseModel):
    """Component to be removed during uninstall"""
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(..., description="Component name")
    type: ComponentType = Field(..., description="Component type")
    location: str = Field(..., description="File or directory path")
    size_mb: float = Field(..., description="Size in megabytes")
    contains_user_data: bool = Field(..., description="Whether contains user data")


class UninstallInventory(BaseModel):
    """Complete inventory of components for clean removal"""
    model_config = ConfigDict(str_strip_whitespace=True)

    components: list[UninstallComponent] = Field(default_factory=list)
    estimated_data_size: str = Field(..., description="Total estimated data loss")
    confirmation_required: bool = Field(default=True, description="Requires user confirmation")

    def scan_installed_components(self) -> list[UninstallComponent]:
        """Scan and return all components"""
        return self.components
