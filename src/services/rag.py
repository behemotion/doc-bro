"""RAG (Retrieval-Augmented Generation) search service - DEPRECATED.

DEPRECATION WARNING:
    This module has been moved to src.logic.rag.core.search_service.

    Please update your imports:
    OLD: from src.services.rag import RAGSearchService
    NEW: from src.logic.rag.core.search_service import RAGSearchService

    This module will be removed in a future version.
"""

import warnings

# Issue deprecation warning
warnings.warn(
    "src.services.rag is deprecated and will be removed in a future version. "
    "Please use src.logic.rag.core.search_service instead.",
    DeprecationWarning,
    stacklevel=2,
)

# Re-export from new location for backward compatibility
from src.logic.rag.core.search_service import RAGSearchService, RAGError

__all__ = ["RAGSearchService", "RAGError"]