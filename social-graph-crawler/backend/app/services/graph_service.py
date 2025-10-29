"""
Service layer for graph analysis and complex queries.
"""

import logging
from typing import List, Dict, Set, Optional, Tuple
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Node, Edge

logger = logging.getLogger(__name__)


class GraphService:
    """Service for advanced graph operations and analysis."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def calculate_centrality(
        self,
        node_id: UUID,
        centrality_type: str = "degree"
    ) -> float:
        """
        Calculate centrality metrics for a node.
        
        Args:
            node_id: Node UUID
            centrality_type: Type of centrality (degree, betweenness, closeness)
        
        Returns:
            Centrality score
        """
        if centrality_type == "degree":
            return await self._degree_centrality(node_id)
        elif centrality_type == "betweenness":
            return await self._betweenness_centrality(node_id)
        elif centrality_type == "closeness":
            return await self._closeness_centrality(node_id)
        else:
            raise ValueError(f"Unknown centrality type: {centrality_type}")
    
    async def _degree_centrality(self, node_id: UUID) -> float:
        """Calculate degree centrality (normalized)."""
        # Count incoming edges
        in_degree_query = select(func.count()).where(Edge.target_node_id == node_id)
        in_degree_result = await self.db.execute(in_degree_query)
        in_degree = in_degree_result.scalar()
        
        # Count outgoing edges
        out_degree_query = select(func.count()).where(Edge.source_node_id == node_id)
        out_degree_result = await self.db.execute(out_degree_query)
        out_degree = out_degree_result.scalar()
        
        # Get total nodes for normalization
        total_nodes_query = select(func.count(Node.id))
        total_nodes_result = await self.db.execute(total_nodes_query)
        total_nodes = total_nodes_result.scalar()
        
        # Normalized degree centrality
        if total_nodes <= 1:
            return 0.0
        
        degree = in_degree + out_degree
        return degree / (total_nodes - 1)
    
    async def _betweenness_centrality(self, node_id: UUID) -> float:
        """
        Calculate betweenness centrality (simplified version).
        
        Note: Full implementation would require all-pairs shortest paths.
        This is a simplified approximation.
        """
        # For a full implementation, you'd need to:
        # 1. Find all shortest paths between all pairs of nodes
        # 2. Count how many pass through this node
        # 3. Normalize by the total number of pairs
        
        # Simplified: Count edges where this node is a common neighbor
        return 0.0  # Placeholder
    
    async def _closeness_centrality(self, node_id: UUID) -> float:
        """Calculate closeness centrality (average distance to all other nodes)."""
        # Simplified implementation - would need BFS to all reachable nodes
        return 0.0  # Placeholder
    
    async def find_communities(
        self,
        algorithm: str = "louvain"
    ) -> Dict[UUID, int]:
        """
        Detect communities in the graph.
        
        Args:
            algorithm: Community detection algorithm
        
        Returns:
            Dict mapping node IDs to community IDs
        """
        # Placeholder - would integrate networkx or graph-tool
        logger.warning("Community detection not yet implemented")
        return {}
    
    async def get_subgraph(
        self,
        node_ids: List[UUID]
    ) -> Tuple[List[Node], List[Edge]]:
        """
        Extract a subgraph containing specific nodes.
        
        Args:
            node_ids: List of node UUIDs to include
        
        Returns:
            Tuple of (nodes, edges)
        """
        # Get nodes
        nodes_result = await self.db.execute(
            select(Node).where(Node.id.in_(node_ids))
        )
        nodes = nodes_result.scalars().all()
        
        # Get edges between these nodes
        edges_result = await self.db.execute(
            select(Edge).where(
                Edge.source_node_id.in_(node_ids),
                Edge.target_node_id.in_(node_ids)
            )
        )
        edges = edges_result.scalars().all()
        
        return nodes, edges
    
    async def suggest_connections(
        self,
        node_id: UUID,
        limit: int = 10
    ) -> List[Node]:
        """
        Suggest potential connections based on common neighbors.
        
        Args:
            node_id: Node to find suggestions for
            limit: Maximum suggestions
        
        Returns:
            List of suggested nodes
        """
        # Get direct neighbors
        neighbors_query = select(Edge.target_node_id).where(
            Edge.source_node_id == node_id
        )
        neighbors_result = await self.db.execute(neighbors_query)
        direct_neighbors = {row[0] for row in neighbors_result}
        direct_neighbors.add(node_id)
        
        # Find nodes connected to neighbors (2-hop neighbors)
        second_hop_query = select(
            Edge.target_node_id,
            func.count().label("common_count")
        ).where(
            Edge.source_node_id.in_(direct_neighbors),
            ~Edge.target_node_id.in_(direct_neighbors)  # Exclude already connected
        ).group_by(Edge.target_node_id).order_by(
            func.count().desc()
        ).limit(limit)
        
        second_hop_result = await self.db.execute(second_hop_query)
        suggested_ids = [row[0] for row in second_hop_result]
        
        # Get node objects
        if suggested_ids:
            nodes_result = await self.db.execute(
                select(Node).where(Node.id.in_(suggested_ids))
            )
            return nodes_result.scalars().all()
        
        return []
