"""
Node model representing entities in the social graph.
"""

from datetime import datetime
from typing import List
from uuid import uuid4
from sqlalchemy import String, DateTime, Index, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Node(Base):
    """
    Represents an entity (user, repo, subreddit, page) in the graph.
    
    Attributes:
        id: Unique identifier (UUID)
        entity_type: Type of entity (user, repo, subreddit, page)
        entity_id: External ID from the source platform
        source: Data source (reddit, github, wikipedia)
        display_name: Human-readable name
        metadata: Flexible JSON storage for source-specific data
        created_at: Timestamp of creation
        updated_at: Timestamp of last update
    """
    
    __tablename__ = "nodes"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Core Fields
    entity_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type: user, repo, subreddit, page"
    )
    
    entity_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="External ID from source platform"
    )
    
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Source: reddit, github, wikipedia"
    )
    
    display_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        index=True,
        comment="Human-readable name for display"
    )
    
    # Flexible metadata storage
    metadata: Mapped[dict] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Source-specific data (followers, karma, stars, etc.)"
    )
    
    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    # Relationships
    outgoing_edges: Mapped[List["Edge"]] = relationship(
        "Edge",
        foreign_keys="Edge.source_node_id",
        back_populates="source_node",
        cascade="all, delete-orphan"
    )
    
    incoming_edges: Mapped[List["Edge"]] = relationship(
        "Edge",
        foreign_keys="Edge.target_node_id",
        back_populates="target_node",
        cascade="all, delete-orphan"
    )
    
    # Constraints
    __table_args__ = (
        UniqueConstraint(
            'source', 'entity_type', 'entity_id',
            name='uq_node_source_type_id'
        ),
        Index('ix_nodes_metadata', 'metadata', postgresql_using='gin'),
        {'comment': 'Social graph nodes (entities)'}
    )
    
    def __repr__(self) -> str:
        return f"<Node(id={self.id}, type={self.entity_type}, name={self.display_name})>"
    
    @property
    def degree(self) -> int:
        """Calculate node degree (total connections)."""
        return len(self.outgoing_edges) + len(self.incoming_edges)
    
    @property
    def in_degree(self) -> int:
        """Calculate in-degree (incoming connections)."""
        return len(self.incoming_edges)
    
    @property
    def out_degree(self) -> int:
        """Calculate out-degree (outgoing connections)."""
        return len(self.outgoing_edges)