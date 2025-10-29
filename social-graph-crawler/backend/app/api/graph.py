"""
API routes for Graph queries and analysis.
"""

from typing import Dict, List, Set
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select, func, text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Node, Edge
from app.schemas.graph import (
    GraphQuery,
    GraphResponse,
    GraphStats,
    PathQuery,
    PathResponse,
    NeighborsQuery,
    NeighborsResponse
)
from app.schemas.node import NodeResponse
from app.schemas.edge import EdgeResponse


router = APIRouter()


@router.post("/query", response_model=GraphResponse)
async def query_graph(
    query: GraphQuery,
    db: AsyncSession = Depends(get_db)
):
    """
    Query a subgraph starting from a node.
    
    Uses BFS traversal to explore the graph up to specified depth.
    Returns nodes and edges within the subgraph.
    """
    # Validate start node exists
    start_result = await db.execute(
        select(Node).where(Node.id == query.start_node_id)
    )
    start_node = start_result.scalar_one_or_none()
    
    if not start_node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Start node {query.start_node_id} not found"
        )
    
    # BFS traversal
    visited_nodes: Set[UUID] = {query.start_node_id}
    visited_edges: Set[UUID] = set()
    queue: List[tuple[UUID, int]] = [(query.start_node_id, 0)]
    
    nodes_result = []
    edges_result = []
    
    while queue and len(visited_nodes) < query.max_nodes:
        current_id, current_depth = queue.pop(0)
        
        # Get current node
        node_query = select(Node).where(Node.id == current_id)
        node_data = await db.execute(node_query)
        current_node = node_data.scalar_one()
        nodes_result.append(current_node)
        
        if current_depth >= query.depth:
            continue
        
        # Build edge query based on direction
        edge_query = select(Edge)
        
        if query.direction in ["outgoing", "both"]:
            outgoing_query = select(Edge).where(Edge.source_node_id == current_id)
            if query.relationship_types:
                outgoing_query = outgoing_query.where(
                    Edge.relationship_type.in_(query.relationship_types)
                )
            edge_query = outgoing_query
        
        if query.direction in ["incoming", "both"]:
            incoming_query = select(Edge).where(Edge.target_node_id == current_id)
            if query.relationship_types:
                incoming_query = incoming_query.where(
                    Edge.relationship_type.in_(query.relationship_types)
                )
            
            if query.direction == "both":
                edge_query = edge_query.union(incoming_query)
            else:
                edge_query = incoming_query
        
        # Get edges
        edges_data = await db.execute(edge_query)
        edges = edges_data.scalars().all()
        
        for edge in edges:
            if edge.id in visited_edges:
                continue
            
            visited_edges.add(edge.id)
            edges_result.append(edge)
            
            # Get next node
            next_node_id = (
                edge.target_node_id
                if query.direction == "outgoing" or edge.source_node_id == current_id
                else edge.source_node_id
            )
            
            if next_node_id not in visited_nodes:
                visited_nodes.add(next_node_id)
                queue.append((next_node_id, current_depth + 1))
    
    return GraphResponse(
        nodes=nodes_result,
        edges=edges_result,
        metadata={
            "start_node_id": str(query.start_node_id),
            "depth": query.depth,
            "direction": query.direction
        }
    )


@router.get("/stats", response_model=GraphStats)
async def get_graph_stats(db: AsyncSession = Depends(get_db)):
    """
    Get overall graph statistics.
    """
    # Total counts
    node_count_result = await db.execute(select(func.count(Node.id)))
    total_nodes = node_count_result.scalar()
    
    edge_count_result = await db.execute(select(func.count(Edge.id)))
    total_edges = edge_count_result.scalar()
    
    # Nodes by type
    nodes_by_type_query = select(
        Node.entity_type,
        func.count(Node.id).label("count")
    ).group_by(Node.entity_type)
    nodes_by_type_result = await db.execute(nodes_by_type_query)
    nodes_by_type = {row[0]: row[1] for row in nodes_by_type_result}
    
    # Nodes by source
    nodes_by_source_query = select(
        Node.source,
        func.count(Node.id).label("count")
    ).group_by(Node.source)
    nodes_by_source_result = await db.execute(nodes_by_source_query)
    nodes_by_source = {row[0]: row[1] for row in nodes_by_source_result}
    
    # Edges by type
    edges_by_type_query = select(
        Edge.relationship_type,
        func.count(Edge.id).label("count")
    ).group_by(Edge.relationship_type)
    edges_by_type_result = await db.execute(edges_by_type_query)
    edges_by_type = {row[0]: row[1] for row in edges_by_type_result}
    
    # Calculate average degree and density
    avg_degree = (2 * total_edges / total_nodes) if total_nodes > 0 else 0
    max_possible_edges = total_nodes * (total_nodes - 1) / 2
    density = (total_edges / max_possible_edges) if max_possible_edges > 0 else 0
    
    # Connected components (simplified - just counting isolated nodes)
    # A proper implementation would use Union-Find or DFS
    connected_components = total_nodes  # Placeholder
    
    return GraphStats(
        total_nodes=total_nodes,
        total_edges=total_edges,
        nodes_by_type=nodes_by_type,
        edges_by_type=edges_by_type,
        nodes_by_source=nodes_by_source,
        average_degree=avg_degree,
        density=density,
        connected_components=connected_components
    )


@router.post("/neighbors", response_model=NeighborsResponse)
async def get_neighbors(
    query: NeighborsQuery,
    db: AsyncSession = Depends(get_db)
):
    """
    Get direct neighbors of a node.
    """
    # Validate node exists
    node_result = await db.execute(
        select(Node).where(Node.id == query.node_id)
    )
    node = node_result.scalar_one_or_none()
    
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node {query.node_id} not found"
        )
    
    # Get edges based on direction
    edges = []
    neighbor_ids = set()
    
    if query.direction in ["outgoing", "both"]:
        outgoing_query = select(Edge).where(Edge.source_node_id == query.node_id)
        if query.relationship_types:
            outgoing_query = outgoing_query.where(
                Edge.relationship_type.in_(query.relationship_types)
            )
        outgoing_result = await db.execute(outgoing_query.limit(query.max_neighbors))
        outgoing_edges = outgoing_result.scalars().all()
        edges.extend(outgoing_edges)
        neighbor_ids.update(edge.target_node_id for edge in outgoing_edges)
    
    if query.direction in ["incoming", "both"]:
        incoming_query = select(Edge).where(Edge.target_node_id == query.node_id)
        if query.relationship_types:
            incoming_query = incoming_query.where(
                Edge.relationship_type.in_(query.relationship_types)
            )
        incoming_result = await db.execute(incoming_query.limit(query.max_neighbors))
        incoming_edges = incoming_result.scalars().all()
        edges.extend(incoming_edges)
        neighbor_ids.update(edge.source_node_id for edge in incoming_edges)
    
    # Get neighbor nodes
    neighbors_result = await db.execute(
        select(Node).where(Node.id.in_(neighbor_ids))
    )
    neighbors = neighbors_result.scalars().all()
    
    return NeighborsResponse(
        node=node,
        neighbors=neighbors,
        edges=edges,
        count=len(neighbors)
    )


@router.post("/path", response_model=PathResponse)
async def find_shortest_path(
    query: PathQuery,
    db: AsyncSession = Depends(get_db)
):
    """
    Find shortest path between two nodes using BFS.
    """
    # Validate both nodes exist
    source_result = await db.execute(
        select(Node).where(Node.id == query.source_node_id)
    )
    source_node = source_result.scalar_one_or_none()
    
    target_result = await db.execute(
        select(Node).where(Node.id == query.target_node_id)
    )
    target_node = target_result.scalar_one_or_none()
    
    if not source_node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source node {query.source_node_id} not found"
        )
    
    if not target_node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target node {query.target_node_id} not found"
        )
    
    # BFS for shortest path
    visited = {query.source_node_id}
    queue = [(query.source_node_id, [query.source_node_id], [], 0.0, 0)]
    
    while queue:
        current_id, path, path_edges, total_weight, depth = queue.pop(0)
        
        if current_id == query.target_node_id:
            # Found path - get full node objects
            nodes_result = await db.execute(
                select(Node).where(Node.id.in_(path))
            )
            path_nodes = {n.id: n for n in nodes_result.scalars()}
            ordered_nodes = [path_nodes[node_id] for node_id in path]
            
            # Get edge objects
            edges_result = await db.execute(
                select(Edge).where(Edge.id.in_([e.id for e in path_edges]))
            )
            edges = edges_result.scalars().all()
            
            return PathResponse(
                path=ordered_nodes,
                edges=edges,
                length=len(path) - 1,
                total_weight=total_weight
            )
        
        if depth >= query.max_depth:
            continue
        
        # Get outgoing edges
        edges_result = await db.execute(
            select(Edge).where(Edge.source_node_id == current_id)
        )
        edges = edges_result.scalars().all()
        
        for edge in edges:
            next_id = edge.target_node_id
            if next_id not in visited:
                visited.add(next_id)
                queue.append((
                    next_id,
                    path + [next_id],
                    path_edges + [edge],
                    total_weight + edge.weight,
                    depth + 1
                ))
    
    # No path found
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"No path found between nodes within depth {query.max_depth}"
    )