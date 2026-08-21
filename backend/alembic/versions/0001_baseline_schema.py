"""baseline schema

Revision ID: 0001_baseline_schema
Revises:
Create Date: 2026-08-21
"""
from alembic import op
import sqlalchemy as sa

revision = "0001_baseline_schema"
down_revision = None
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.create_table("nodes", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("entity_type", sa.String(50), nullable=False), sa.Column("entity_id", sa.String(255), nullable=False), sa.Column("source", sa.String(50), nullable=False), sa.Column("display_name", sa.String(255), nullable=False), sa.Column("metadata", sa.JSON(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("source", "entity_type", "entity_id", name="uq_node_source_type_entity"))
    op.create_index("ix_nodes_source", "nodes", ["source"])
    op.create_index("ix_nodes_entity_type", "nodes", ["entity_type"])
    op.create_table("crawl_jobs", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("source", sa.String(50), nullable=False), sa.Column("start_entity", sa.String(255), nullable=False), sa.Column("request_key", sa.String(64), nullable=False), sa.Column("status", sa.String(20), nullable=False), sa.Column("entity_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("edge_count", sa.Integer(), nullable=False, server_default="0"), sa.Column("error_message", sa.Text()), sa.Column("started_at", sa.DateTime(timezone=True)), sa.Column("completed_at", sa.DateTime(timezone=True)), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False))
    op.create_index("uq_active_crawl_request", "crawl_jobs", ["request_key"], unique=True, postgresql_where=sa.text("status IN ('pending', 'running')"), sqlite_where=sa.text("status IN ('pending', 'running')"))
    op.create_index("ix_crawl_jobs_source", "crawl_jobs", ["source"])
    op.create_index("ix_crawl_jobs_status", "crawl_jobs", ["status"])
    op.create_table("edges", sa.Column("id", sa.Uuid(), primary_key=True), sa.Column("source_node_id", sa.Uuid(), sa.ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False), sa.Column("target_node_id", sa.Uuid(), sa.ForeignKey("nodes.id", ondelete="CASCADE"), nullable=False), sa.Column("relationship_type", sa.String(50), nullable=False), sa.Column("weight", sa.Float(), nullable=False), sa.Column("metadata", sa.JSON(), nullable=True), sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False), sa.UniqueConstraint("source_node_id", "target_node_id", "relationship_type", name="uq_edge_source_target_type"))
    op.create_index("ix_edges_source_node_id", "edges", ["source_node_id"])
    op.create_index("ix_edges_target_node_id", "edges", ["target_node_id"])
    op.create_index("ix_edges_relationship_type", "edges", ["relationship_type"])

def downgrade() -> None:
    op.drop_table("edges")
    op.drop_table("crawl_jobs")
    op.drop_table("nodes")
