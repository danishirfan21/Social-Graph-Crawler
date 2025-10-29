"""
Pydantic schemas for Node API validation and serialization.
"""

from datetime import datetime
from typing import Dict, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict


class NodeBase(BaseModel):
    """Base schema for Node with common fields."""
    entity_type: str = Field(..., description="Type of entity", examples=["user", "repo", "subreddit"])
    entity_id: str = Field(..., description="External ID from source platform")
    source: str = Field(..., description="Data source", examples=["reddit", "github", "wikipedia"])
    display_name: str = Field(..., description="Human-readable name")
    metadata: Optional[Dict] = Field(default_factory=dict, description="Source-specific metadata")


class NodeCreate(NodeBase):
    """Schema for creating a new node."""
    pass


class NodeUpdate(BaseModel):
    """Schema for updating an existing node."""
    display_name: Optional[str] = None
    metadata: Optional[Dict] = None
    
    model_config = ConfigDict(extra="forbid")


class NodeResponse(NodeBase):
    """Schema for node response from API."""
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    # Computed fields
    in_degree: Optional[int] = Field(default=0, description="Number of incoming edges")
    out_degree: Optional[int] = Field(default=0, description="Number of outgoing edges")
    
    model_config = ConfigDict(from_attributes=True)


class NodeWithEdges(NodeResponse):
    """Schema for node with related edges."""
    outgoing_edges: list["EdgeResponse"] = []
    incoming_edges: list["EdgeResponse"] = []


class NodeListResponse(BaseModel):
    """Paginated list of nodes."""
    items: list[NodeResponse]
    total: int
    page: int
    page_size: int
    pages: int


# Forward reference resolution
from app.schemas.edge import EdgeResponse
NodeWithEdges.model_rebuild()