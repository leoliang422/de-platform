"""annotations (划词批注)

Revision ID: 0012
Revises: 0011
Create Date: 2026-07-20
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0012"
down_revision: str | None = "0011"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "annotations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("content_type", sa.String(length=20), nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("parent_id", sa.Integer(), nullable=True),
        sa.Column("quote", sa.Text(), nullable=False, server_default=""),
        sa.Column("anchor_offset", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["parent_id"], ["annotations.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_annotations_user_id", "annotations", ["user_id"])
    op.create_index("ix_annotations_created_at", "annotations", ["created_at"])
    op.create_index("ix_annotations_content", "annotations", ["content_type", "content_id"])


def downgrade() -> None:
    op.drop_index("ix_annotations_content", table_name="annotations")
    op.drop_index("ix_annotations_created_at", table_name="annotations")
    op.drop_index("ix_annotations_user_id", table_name="annotations")
    op.drop_table("annotations")
