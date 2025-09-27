"""Data models for DocBro."""

from .project import Project, ProjectStatus
# CrawlSession moved to src.logic.crawler.models.session
from src.logic.crawler.models.session import CrawlSession, CrawlStatus
# Page moved to src.logic.crawler.models.page
from src.logic.crawler.models.page import Page, PageStatus
from .query_result import QueryResult, QueryResponse
from .installation import (
    InstallationContext,
    ServiceStatus,
    SetupWizardState,
    PackageMetadata,
    InstallationRequest,
    InstallationResponse,
    SystemRequirements as InstallationSystemRequirements,
    CriticalDecisionPoint,
)
from .system_requirements import SystemRequirements
from .installation_state import InstallationState
from .installation_profile import InstallationProfile
from .service_config import (
    ServiceConfiguration,
    ServiceName,
    ServiceStatusType,
)
from .vector_store_types import VectorStoreProvider
from .setup_session import SetupSession

__all__ = [
    "Project",
    "ProjectStatus",
    "CrawlSession",
    "CrawlStatus",
    "Page",
    "PageStatus",
    "QueryResult",
    "QueryResponse",
    "InstallationContext",
    "ServiceStatus",
    "SetupWizardState",
    "PackageMetadata",
    "InstallationRequest",
    "InstallationResponse",
    "InstallationSystemRequirements",
    "SystemRequirements",
    "CriticalDecisionPoint",
    "InstallationState",
    "InstallationProfile",
    "ServiceConfiguration",
    "ServiceName",
    "ServiceStatusType",
    "VectorStoreProvider",
    "SetupSession",
]