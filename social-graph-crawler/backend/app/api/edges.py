"""
API routes for Edge operations (CRUD).
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Edge, Node
from app.schemas.edge import (
    EdgeCreate,
    EdgeUpdate,
    EdgeResponse,
    EdgeWithNodes,
    EdgeListResponse
)


router = APIRouter()


@router.post("/", response_model=EdgeResponse, status_code=status.HTTP_201_CREATED)
async def create_edge(
    edge_data: EdgeCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new edge.
    
    - **source_node_id**: Source node UUID
    - **target_node_id**: Target node UUID
    - **relationship_type**: Type of relationship
    - **weight**: Relationship strength (default: 1.0)
    - **metadata**: Optional metadata dictionary
    """
    # Validate nodes exist
    source_result = await db.execute(
        select(Node).where(Node.id == edge_data.source_node_id)
    )
    source_node = source_result.scalar_one_or_none()
    
    if not source_node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Source node {edge_data.source_node_id} not found"
        )
    
    target_result = await db.execute(
        select(Node).where(Node.id == edge_data.target_node_id)
    )
    target_node = target_result.scalar_one_or_none()
    
    if not target_node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Target node {edge_data.target_node_id} not found"
        )
    
    # Check if edge already exists
    result = await db.execute(
        select(Edge).where(
            Edge.source_node_id == edge_data.source_node_id,
            Edge.target_node_id == edge_data.target_node_id,
            Edge.relationship_type == edge_data.relationship_type
        )
    )
    existing_edge = result.scalar_one_or_none()
    
    if existing_edge:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Edge with this source, target, and relationship type already exists"
        )
    
    # Create edge
    edge = Edge(**edge_data.model_dump())
    db.add(edge)
    await db.commit()
    await db.refresh(edge)
    
    return edge


@router.get("/", response_model=EdgeListResponse)
async def list_edges(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    relationship_type: Optional[str] = Query(None, description="Filter by relationship type"),
    source_node_id: Optional[UUID] = Query(None, description="Filter by source node"),
    target_node_id: Optional[UUID] = Query(None, description="Filter by target node"),
    min_weight: Optional[float] = Query(None, ge=0.0, description="Minimum weight"),
    db: AsyncSession = Depends(get_db)
):
    """
    List edges with pagination and filtering.
    """
    query = select(Edge)
    
    # Apply filters
    if relationship_type:
        query = query.where(Edge.relationship_type == relationship_type)
    
    if source_node_id:
        query = query.where(Edge.source_node_id == source_node_id)
    
    if target_node_id:
        query = query.where(Edge.target_node_id == target_node_id)
    
    if min_weight is not None:
        query = query.where(Edge.weight >= min_weight)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    edges = result.scalars().all()
    
    pages = (total + page_size - 1) // page_size
    
    return EdgeListResponse(
        items=edges,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/{edge_id}", response_model=EdgeWithNodes)
async def get_edge(
    edge_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get an edge by ID with related nodes."""
    result = await db.execute(
        select(Edge)
        .where(Edge.id == edge_id)
        .options(selectinload(Edge.source_node), selectinload(Edge.target_node))
    )
    edge = result.scalar_one_or_none()
    
    if not edge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge with id {edge_id} not found"
        )
    
    return edge


@router.put("/{edge_id}", response_model=EdgeResponse)
async def update_edge(
    edge_id: UUID,
    edge_data: EdgeUpdate,
    db: AsyncSession = Depends(get_db)
):
    """Update an edge."""
    result = await db.execute(
        select(Edge).where(Edge.id == edge_id)
    )
    edge = result.scalar_one_or_none()
    
    if not edge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge with id {edge_id} not found"
        )
    
    # Update fields
    update_data = edge_data.model_dump(exclude_unset=True)
    
    for field, value in update_data.items():
        if field == "metadata" and value:
            edge.metadata = {**edge.metadata, **value}
        else:
            setattr(edge, field, value)
    
    await db.commit()
    await db.refresh(edge)
    
    return edge


@router.delete("/{edge_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_edge(
    edge_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Delete an edge."""
    result = await db.execute(
        select(Edge).where(Edge.id == edge_id)
    )
    edge = result.scalar_one_or_none()
    
    if not edge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Edge with id {edge_id} not found"
        )
    
    await db.delete(edge)
    await db.commit()