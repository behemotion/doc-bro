"""Pydantic models for MCP admin shelf endpoints."""

from typing import Optional, Dict, Any, List
from datetime import datetime
from pydantic import BaseModel, Field


class CreateShelfRequest(BaseModel):
    """Request parameters for create_shelf endpoint."""

    name: str = Field(..., description="Shelf name")
    description: Optional[str] = Field(default=None, description="Shelf description")
    set_current: bool = Field(default=False, description="Set as current shelf")
    force: bool = Field(default=False, description="Force creation if exists")


class CreateShelfResponse(BaseModel):
    """Response for create_shelf operation."""

    operation: str = Field(default="create_shelf", description="Operation name")
    shelf_name: str = Field(..., description="Created shelf name")
    result: str = Field(..., description="Result: created or updated")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Operation details")


class AddBasketRequest(BaseModel):
    """Request parameters for add_basket endpoint."""

    shelf_name: str = Field(..., description="Shelf name")
    basket_name: str = Field(..., description="Basket (box) name")
    basket_type: str = Field(default="data", description="Basket type (crawling/data/storage)")
    description: Optional[str] = Field(default=None, description="Basket description")
    force: bool = Field(default=False, description="Force creation if exists")


class AddBasketResponse(BaseModel):
    """Response for add_basket operation."""

    operation: str = Field(default="add_basket", description="Operation name")
    shelf_name: str = Field(..., description="Shelf name")
    basket_name: str = Field(..., description="Basket name")
    result: str = Field(..., description="Result status")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Operation details")


class RemoveBasketRequest(BaseModel):
    """Request parameters for remove_basket endpoint."""

    shelf_name: str = Field(..., description="Shelf name")
    basket_name: str = Field(..., description="Basket name")
    confirm: bool = Field(default=False, description="Confirmation required")
    backup: bool = Field(default=True, description="Create backup before removal")


class RemoveBasketResponse(BaseModel):
    """Response for remove_basket operation."""

    operation: str = Field(default="remove_basket", description="Operation name")
    shelf_name: str = Field(..., description="Shelf name")
    basket_name: str = Field(..., description="Basket name")
    result: str = Field(..., description="Result status")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Removal details")


class SetCurrentShelfRequest(BaseModel):
    """Request parameters for set_current_shelf endpoint."""

    shelf_name: str = Field(..., description="Shelf name to set as current")


class SetCurrentShelfResponse(BaseModel):
    """Response for set_current_shelf operation."""

    operation: str = Field(default="set_current_shelf", description="Operation name")
    shelf_name: str = Field(..., description="New current shelf")
    result: str = Field(..., description="Result status")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Context details")


class DeleteShelfRequest(BaseModel):
    """Request parameters for delete_shelf endpoint (BLOCKED)."""

    name: str = Field(..., description="Shelf name")
    force: bool = Field(default=False, description="Force deletion")
    confirm: bool = Field(default=False, description="Confirmation")


class OperationProhibitedResponse(BaseModel):
    """Response for prohibited operations."""

    success: bool = Field(default=False, description="Always false")
    error: str = Field(default="operation_prohibited", description="Error code")
    message: str = Field(..., description="Explanation message")
    details: Optional[Dict[str, Any]] = Field(default=None, description="Alternative methods")