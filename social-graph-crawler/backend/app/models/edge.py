"""
Edge model representing relationships between nodes.
"""

from datetime import datetime
from uuid import uuid4
from sqlalchemy import String, DateTime, Float, ForeignKey, Index, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from app.database import Base


class Edge(Base):
    """
    Represents a relationship (edge) between two nodes in the graph.
    
    Attributes:
        id: Unique identifier (UUID)
        source_node_id: ID of the source node
        target_node_id: ID of the target node
        relationship_type: Type of relationship (follows, contributes, links_to)
        weight: Strength of the relationship (default: 1.0)
        metadata: Flexible JSON storage for relationship-specific data
        created_at: Timestamp of creation
    """
    
    __tablename__ = "edges"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Foreign Keys
    source_node_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Source node of the relationship"
    )
    
    target_node_id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("nodes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Target node of the relationship"
    )
    
    # Core Fields
    relationship_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Type: follows, contributes, links_to, mentioned_in"
    )
    
    weight: Mapped[float] = mapped_column(
        Float,
        default=1.0,
        nullable=False,
        comment="Relationship strength (0.0 to 1.0+)"
    )
    
    # Flexible metadata storage
    metadata: Mapped[dict] = mapped_column(
        JSON,
        nullable=True,
        default=dict,
        comment="Relationship-specific data (timestamp, context, etc.)"
    )
    
    # Timestamp
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    # Relationships
    source_node: Mapped["Node"] = relationship(
        "Node",
        foreign_keys=[source_node_id],
        back_populates="outgoing_edges"
    )
    
    target_node: Mapped["Node"] = relationship(
        "Node",
        foreign_keys=[target_node_id],
        back_populates="incoming_edges"
    )
    
    # Constraints
    __table_args__ = (
        UniqueConstraint(
            'source_node_id', 'target_node_id', 'relationship_type',
            name='uq_edge_source_target_type'
        ),
        Index('ix_edges_weight', 'weight'),
        {'comment': 'Social graph edges (relationships)'}
    )
    
    def __repr__(self) -> str:
        return (
            f"<Edge(id={self.id}, type={self.relationship_type}, "
            f"weight={self.weight})>"
        )


# Import Node to resolve forward reference
from app.models.node import Node
Edge.source_node.property.mapper.class_ = Node
Edge.target_node.property.mapper.class_ = Node