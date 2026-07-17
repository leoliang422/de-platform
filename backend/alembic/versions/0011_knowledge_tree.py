"""knowledge tree nodes

Revision ID: 0011
Revises: 0010
Create Date: 2026-07-17

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0011"
down_revision: str | None = "0010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "knowledge_nodes",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category_id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("knowledge_item_id", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), nullable=False, server_default="published"),
        sa.Column("proposer_id", sa.Integer(), nullable=True),
        sa.Column("note", sa.String(length=500), nullable=True),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["category_id"], ["categories.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["knowledge_nodes.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["knowledge_item_id"], ["knowledge_items.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_knowledge_nodes_category_id", "knowledge_nodes", ["category_id"])
    op.create_index("ix_knowledge_nodes_parent_id", "knowledge_nodes", ["parent_id"])
    op.create_index("ix_knowledge_nodes_status", "knowledge_nodes", ["status"])


def downgrade() -> None:
    op.drop_index("ix_knowledge_nodes_status", table_name="knowledge_nodes")
    op.drop_index("ix_knowledge_nodes_parent_id", table_name="knowledge_nodes")
    op.drop_index("ix_knowledge_nodes_category_id", table_name="knowledge_nodes")
    op.drop_table("knowledge_nodes")
