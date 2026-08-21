"""
Pydantic schemas for Graph API queries and responses.
"""

from typing import List, Dict, Optional
from uuid import UUID
from pydantic import BaseModel, Field

from app.schemas.node import NodeResponse
from app.schemas.edge import EdgeResponse


class GraphQuery(BaseModel):
    """Query parameters for graph traversal."""
    start_node_id: UUID = Field(..., description="Starting node UUID")
    depth: int = Field(default=2, ge=1, le=5, description="Traversal depth (max 5)")
    max_nodes: int = Field(default=100, ge=1, le=5000, description="Maximum nodes to return")
    relationship_types: Optional[List[str]] = Field(default=None, description="Filter by relationship types")
    direction: str = Field(default="both", pattern="^(outgoing|incoming|both)$", description="Edge direction")


class GraphResponse(BaseModel):
    """Graph data structure for visualization."""
    nodes: List[NodeResponse]
    edges: List[EdgeResponse]
    metadata: Dict = Field(default_factory=dict, description="Graph-level metadata")
    
    @property
    def node_count(self) -> int:
        return len(self.nodes)
    
    @property
    def edge_count(self) -> int:
        return len(self.edges)


class GraphStats(BaseModel):
    """Statistical information about the graph."""
    total_nodes: int
    total_edges: int
    nodes_by_type: Dict[str, int]
    edges_by_type: Dict[str, int]
    nodes_by_source: Dict[str, int]
    average_degree: float
    density: float
    connected_components: int


class PathQuery(BaseModel):
    """Query parameters for shortest path."""
    source_node_id: UUID
    target_node_id: UUID
    max_depth: int = Field(default=5, ge=1, le=10)


class PathResponse(BaseModel):
    """Shortest path between two nodes."""
    path: List[NodeResponse]
    edges: List[EdgeResponse]
    length: int
    total_weight: float


class NeighborsQuery(BaseModel):
    """Query parameters for getting node neighbors."""
    node_id: UUID
    relationship_types: Optional[List[str]] = None
    direction: str = Field(default="both", pattern="^(outgoing|incoming|both)$")
    max_neighbors: int = Field(default=50, ge=1, le=500)


class NeighborsResponse(BaseModel):
    """Response containing node neighbors."""
    node: NodeResponse
    neighbors: List[NodeResponse]
    edges: List[EdgeResponse]
    count: int