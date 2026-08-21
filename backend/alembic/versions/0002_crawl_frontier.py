"""add durable crawl frontier

Revision ID: 0002_crawl_frontier
Revises: 0001_baseline_schema
"""
from alembic import op
import sqlalchemy as sa

revision = "0002_crawl_frontier"
down_revision = "0001_baseline_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crawl_frontier_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("crawl_job_id", sa.Uuid(), sa.ForeignKey("crawl_jobs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("target", sa.String(512), nullable=False),
        sa.Column("source", sa.String(50), nullable=False),
        sa.Column("depth", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("status", sa.String(20), nullable=False, server_default="queued"),
        sa.Column("attempt_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("worker_id", sa.String(128)),
        sa.Column("lease_expires_at", sa.DateTime(timezone=True)),
        sa.Column("last_error", sa.Text()),
        sa.Column("discovered_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("processing_at", sa.DateTime(timezone=True)),
        sa.Column("completed_at", sa.DateTime(timezone=True)),
        sa.UniqueConstraint("crawl_job_id", "target", name="uq_frontier_job_target"),
    )
    op.create_index("ix_frontier_claim", "crawl_frontier_items", ["status", "lease_expires_at"])
    op.create_index("ix_frontier_job_status", "crawl_frontier_items", ["crawl_job_id", "status"])


def downgrade() -> None:
    op.drop_table("crawl_frontier_items")
