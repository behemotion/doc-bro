"""Pydantic models for MCP shelf endpoints."""

from typing import List, Optional, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


class ShelfSummary(BaseModel):
    """Summary information about a shelf."""

    name: str = Field(..., description="Shelf name")
    created_at: datetime = Field(..., description="Creation timestamp")
    updated_at: datetime = Field(..., description="Last update timestamp")
    is_current: bool = Field(..., description="Whether this is the current shelf")
    basket_count: int = Field(..., description="Number of baskets in this shelf")
    baskets: Optional[List[Dict[str, Any]]] = Field(default=None, description="Optional basket details")


class BasketSummary(BaseModel):
    """Summary information about a basket (box)."""

    name: str = Field(..., description="Basket name")
    type: str = Field(..., description="Basket type (drag/rag/bag)")
    status: str = Field(..., description="Basket status")
    files: int = Field(default=0, description="Number of files in basket")


class ShelfStructure(BaseModel):
    """Detailed structure of a shelf."""

    shelf: Dict[str, Any] = Field(..., description="Shelf information")
    baskets: List[Dict[str, Any]] = Field(..., description="List of baskets")
    summary: Dict[str, Any] = Field(..., description="Summary statistics")


class ListShelfsRequest(BaseModel):
    """Request parameters for list_shelfs endpoint."""

    include_baskets: bool = Field(default=False, description="Include basket details")
    include_empty: bool = Field(default=True, description="Include empty shelves")
    current_only: bool = Field(default=False, description="Only return current shelf")
    limit: int = Field(default=50, ge=1, le=1000, description="Maximum results")


class GetShelfStructureRequest(BaseModel):
    """Request parameters for get_shelf_structure endpoint."""

    shelf_name: str = Field(..., description="Name of the shelf")
    include_basket_details: bool = Field(default=True, description="Include detailed basket info")
    include_file_list: bool = Field(default=False, description="Include file lists")


class ListProjectsRequest(BaseModel):
    """Enhanced request parameters for list_projects endpoint."""

    shelf_name: Optional[str] = Field(default=None, description="Filter by shelf name")
    include_shelf_context: bool = Field(default=False, description="Include shelf context")
    status_filter: Optional[str] = Field(default=None, description="Filter by status")
    limit: int = Field(default=25, ge=1, le=1000, description="Maximum results")


class SearchProjectsRequest(BaseModel):
    """Enhanced request parameters for search_projects endpoint."""

    query: str = Field(..., description="Search query")
    shelf_names: Optional[List[str]] = Field(default=None, description="Filter by shelf names")
    basket_types: Optional[List[str]] = Field(default=None, description="Filter by basket types")
    include_shelf_context: bool = Field(default=False, description="Include shelf context")
    limit: int = Field(default=20, ge=1, le=100, description="Maximum results")


class ShelfMetadata(BaseModel):
    """Metadata about shelf listing response."""

    total_shelfs: int = Field(..., description="Total number of shelves")
    current_shelf: Optional[str] = Field(default=None, description="Name of current shelf")
    total_baskets: int = Field(default=0, description="Total baskets across all shelves")


class CurrentShelfInfo(BaseModel):
    """Information about the current shelf."""

    name: str = Field(..., description="Shelf name")
    created_at: datetime = Field(..., description="Creation timestamp")
    basket_count: int = Field(..., description="Number of baskets")
    total_files: int = Field(default=0, description="Total files across baskets")


class CurrentShelfContext(BaseModel):
    """Context information for current shelf."""

    session_id: str = Field(..., description="Session identifier")
    last_context_update: datetime = Field(..., description="Last context update time")