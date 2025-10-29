"""
Pydantic schemas for Edge API validation and serialization.
"""

from datetime import datetime
from typing import Dict, Optional
from uuid import UUID
from pydantic import BaseModel, Field, ConfigDict, field_validator


class EdgeBase(BaseModel):
    """Base schema for Edge with common fields."""
    source_node_id: UUID = Field(..., description="Source node UUID")
    target_node_id: UUID = Field(..., description="Target node UUID")
    relationship_type: str = Field(..., description="Type of relationship", examples=["follows", "contributes", "links_to"])
    weight: float = Field(default=1.0, ge=0.0, description="Relationship strength")
    metadata: Optional[Dict] = Field(default_factory=dict, description="Relationship-specific metadata")
    
    @field_validator('weight')
    @classmethod
    def validate_weight(cls, v: float) -> float:
        """Ensure weight is non-negative."""
        if v < 0:
            raise ValueError("Weight must be non-negative")
        return v


class EdgeCreate(EdgeBase):
    """Schema for creating a new edge."""
    pass


class EdgeUpdate(BaseModel):
    """Schema for updating an existing edge."""
    relationship_type: Optional[str] = None
    weight: Optional[float] = Field(default=None, ge=0.0)
    metadata: Optional[Dict] = None
    
    model_config = ConfigDict(extra="forbid")


class EdgeResponse(EdgeBase):
    """Schema for edge response from API."""
    id: UUID
    created_at: datetime
    
    model_config = ConfigDict(from_attributes=True)


class EdgeWithNodes(EdgeResponse):
    """Schema for edge with related node information."""
    source_node: "NodeResponse"
    target_node: "NodeResponse"


class EdgeListResponse(BaseModel):
    """Paginated list of edges."""
    items: list[EdgeResponse]
    total: int
    page: int
    page_size: int
    pages: int


# Forward reference resolution
from app.schemas.node import NodeResponse
EdgeWithNodes.model_rebuild()