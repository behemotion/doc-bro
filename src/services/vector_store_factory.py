"""Vector store factory for creating appropriate vector store services."""

from typing import Union
from src.core.config import DocBroConfig
from src.models.vector_store_types import VectorStoreProvider
from src.services.sqlite_vec_service import SQLiteVecService
from src.services.vector_store import VectorStoreService
from src.models.settings import GlobalSettings
from src.services.settings_service import SettingsService


class VectorStoreFactory:
    """Factory for creating vector store services based on configuration."""

    @staticmethod
    def create_vector_store(config: DocBroConfig = None, provider: VectorStoreProvider = None) -> Union[VectorStoreService, SQLiteVecService]:
        """Create appropriate vector store service based on provider."""

        # If provider not specified, get from settings
        if provider is None:
            settings_service = SettingsService()
            if settings_service.global_settings_path.exists():
                settings = settings_service.get_global_settings()
                provider = settings.vector_store_provider
            else:
                # Default to SQLite-vec if no settings
                provider = VectorStoreProvider.SQLITE_VEC

        # Create appropriate service
        if provider == VectorStoreProvider.SQLITE_VEC:
            return SQLiteVecService(config or DocBroConfig())
        elif provider == VectorStoreProvider.QDRANT:
            return VectorStoreService(config or DocBroConfig())
        else:
            raise ValueError(f"Unsupported vector store provider: {provider}")

    @staticmethod
    def get_current_provider() -> VectorStoreProvider:
        """Get the currently configured vector store provider."""
        settings_service = SettingsService()
        if settings_service.global_settings_path.exists():
            settings = settings_service.get_global_settings()
            return settings.vector_store_provider
        else:
            return VectorStoreProvider.SQLITE_VEC