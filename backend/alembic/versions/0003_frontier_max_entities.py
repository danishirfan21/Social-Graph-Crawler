"""persist crawl limit on frontier work

Revision ID: 0003_frontier_max_entities
Revises: 0002_crawl_frontier
"""
from alembic import op
import sqlalchemy as sa

revision = "0003_frontier_max_entities"
down_revision = "0002_crawl_frontier"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "crawl_frontier_items",
        sa.Column("max_entities", sa.Integer(), nullable=False, server_default="100"),
    )
    # SQLite cannot issue ``ALTER COLUMN ... DROP DEFAULT``. Keeping the
    # default there is harmless and lets the development configuration use a
    # file-backed SQLite database without a migration failure.
    if op.get_bind().dialect.name != "sqlite":
        op.alter_column("crawl_frontier_items", "max_entities", server_default=None)


def downgrade() -> None:
    op.drop_column("crawl_frontier_items", "max_entities")
