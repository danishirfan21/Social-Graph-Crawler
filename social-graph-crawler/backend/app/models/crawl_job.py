"""
CrawlJob model for tracking crawler execution and status.
"""

from datetime import datetime
from enum import Enum
from uuid import uuid4
from sqlalchemy import String, DateTime, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.database import Base


class CrawlStatus(str, Enum):
    """Enumeration of crawl job statuses."""
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CrawlJob(Base):
    """
    Tracks the execution of crawler jobs.
    
    Attributes:
        id: Unique identifier (UUID)
        source: Data source being crawled
        status: Current job status
        entity_count: Number of nodes discovered
        edge_count: Number of edges discovered
        error_message: Error details if failed
        started_at: When the job started
        completed_at: When the job finished
        created_at: When the job was created
    """
    
    __tablename__ = "crawl_jobs"
    
    # Primary Key
    id: Mapped[UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid4,
        index=True
    )
    
    # Core Fields
    source: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        comment="Source: reddit, github, wikipedia"
    )
    
    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=CrawlStatus.PENDING.value,
        index=True,
        comment="Status: pending, running, completed, failed, cancelled"
    )
    
    # Statistics
    entity_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of nodes discovered"
    )
    
    edge_count: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Number of edges discovered"
    )
    
    # Error Tracking
    error_message: Mapped[str] = mapped_column(
        Text,
        nullable=True,
        comment="Error details if job failed"
    )
    
    # Timestamps
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the job started execution"
    )
    
    completed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="When the job finished execution"
    )
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    
    __table_args__ = (
        {'comment': 'Crawler job tracking and statistics'}
    )
    
    def __repr__(self) -> str:
        return (
            f"<CrawlJob(id={self.id}, source={self.source}, "
            f"status={self.status})>"
        )
    
    @property
    def duration_seconds(self) -> float:
        """Calculate job duration in seconds."""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        elif self.started_at:
            return (datetime.utcnow() - self.started_at).total_seconds()
        return 0.0
    
    @property
    def is_finished(self) -> bool:
        """Check if job has finished (completed, failed, or cancelled)."""
        return self.status in {
            CrawlStatus.COMPLETED.value,
            CrawlStatus.FAILED.value,
            CrawlStatus.CANCELLED.value
        }