"""
API routes for Node operations (CRUD).
"""

from typing import List, Optional
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Node
from app.schemas.node import (
    NodeCreate,
    NodeUpdate,
    NodeResponse,
    NodeWithEdges,
    NodeListResponse
)


router = APIRouter()


@router.post("/", response_model=NodeResponse, status_code=status.HTTP_201_CREATED)
async def create_node(
    node_data: NodeCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new node.
    
    - **entity_type**: Type of entity (user, repo, subreddit, page)
    - **entity_id**: External ID from source platform
    - **source**: Data source (reddit, github, wikipedia)
    - **display_name**: Human-readable name
    - **metadata**: Optional metadata dictionary
    """
    # Check if node already exists
    result = await db.execute(
        select(Node).where(
            Node.source == node_data.source,
            Node.entity_type == node_data.entity_type,
            Node.entity_id == node_data.entity_id
        )
    )
    existing_node = result.scalar_one_or_none()
    
    if existing_node:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Node with this source, entity_type, and entity_id already exists"
        )
    
    # Create new node
    node = Node(**node_data.model_dump())
    db.add(node)
    await db.commit()
    await db.refresh(node)
    
    return node


@router.get("/", response_model=NodeListResponse)
async def list_nodes(
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=500, description="Items per page"),
    entity_type: Optional[str] = Query(None, description="Filter by entity type"),
    source: Optional[str] = Query(None, description="Filter by source"),
    search: Optional[str] = Query(None, description="Search in display_name"),
    db: AsyncSession = Depends(get_db)
):
    """
    List nodes with pagination and filtering.
    
    - **page**: Page number (starts at 1)
    - **page_size**: Number of items per page
    - **entity_type**: Filter by entity type
    - **source**: Filter by source
    - **search**: Search query for display_name
    """
    # Build query
    query = select(Node)
    
    # Apply filters
    if entity_type:
        query = query.where(Node.entity_type == entity_type)
    
    if source:
        query = query.where(Node.source == source)
    
    if search:
        query = query.where(Node.display_name.ilike(f"%{search}%"))
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar()
    
    # Apply pagination
    offset = (page - 1) * page_size
    query = query.offset(offset).limit(page_size)
    
    # Execute query
    result = await db.execute(query)
    nodes = result.scalars().all()
    
    # Calculate pages
    pages = (total + page_size - 1) // page_size
    
    return NodeListResponse(
        items=nodes,
        total=total,
        page=page,
        page_size=page_size,
        pages=pages
    )


@router.get("/{node_id}", response_model=NodeWithEdges)
async def get_node(
    node_id: UUID,
    include_edges: bool = Query(True, description="Include related edges"),
    db: AsyncSession = Depends(get_db)
):
    """
    Get a node by ID.
    
    - **node_id**: UUID of the node
    - **include_edges**: Whether to include related edges
    """
    query = select(Node).where(Node.id == node_id)
    
    if include_edges:
        query = query.options(
            selectinload(Node.outgoing_edges),
            selectinload(Node.incoming_edges)
        )
    
    result = await db.execute(query)
    node = result.scalar_one_or_none()
    
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node with id {node_id} not found"
        )
    
    return node


@router.put("/{node_id}", response_model=NodeResponse)
async def update_node(
    node_id: UUID,
    node_data: NodeUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update a node.
    
    - **node_id**: UUID of the node
    - **display_name**: New display name (optional)
    - **metadata**: New metadata (optional, will be merged with existing)
    """
    result = await db.execute(
        select(Node).where(Node.id == node_id)
    )
    node = result.scalar_one_or_none()
    
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node with id {node_id} not found"
        )
    
    # Update fields
    update_data = node_data.model_dump(exclude_unset=True)
    
    if "display_name" in update_data:
        node.display_name = update_data["display_name"]
    
    if "metadata" in update_data:
        node.metadata = {**node.metadata, **update_data["metadata"]}
    
    await db.commit()
    await db.refresh(node)
    
    return node


@router.delete("/{node_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_node(
    node_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete a node.
    
    - **node_id**: UUID of the node
    
    Note: This will also delete all related edges due to CASCADE.
    """
    result = await db.execute(
        select(Node).where(Node.id == node_id)
    )
    node = result.scalar_one_or_none()
    
    if not node:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Node with id {node_id} not found"
        )
    
    await db.delete(node)
    await db.commit()


@router.get("/search/", response_model=List[NodeResponse])
async def search_nodes(
    q: str = Query(..., min_length=2, description="Search query"),
    limit: int = Query(20, ge=1, le=100, description="Maximum results"),
    db: AsyncSession = Depends(get_db)
):
    """
    Search nodes by display name or entity ID.
    
    - **q**: Search query (minimum 2 characters)
    - **limit**: Maximum number of results
    """
    query = select(Node).where(
        or_(
            Node.display_name.ilike(f"%{q}%"),
            Node.entity_id.ilike(f"%{q}%")
        )
    ).limit(limit)
    
    result = await db.execute(query)
    nodes = result.scalars().all()
    
    return nodes