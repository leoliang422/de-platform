"""interactions: reactions + comments + content views

Revision ID: 0009
Revises: 0008
Create Date: 2026-07-17

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0009"
down_revision: str | None = "0008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "reactions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content_type", sa.String(length=20), nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=20), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("user_id", "content_type", "content_id", "kind", name="uq_reaction"),
    )
    op.create_index("ix_reactions_user_id", "reactions", ["user_id"])
    op.create_index("ix_reactions_content", "reactions", ["content_type", "content_id"])

    op.create_table(
        "comments",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("content_type", sa.String(length=20), nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column(
            "parent_id",
            sa.Integer(),
            sa.ForeignKey("comments.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
    )
    op.create_index("ix_comments_user_id", "comments", ["user_id"])
    op.create_index("ix_comments_created_at", "comments", ["created_at"])
    op.create_index("ix_comments_content", "comments", ["content_type", "content_id"])

    op.create_table(
        "content_views",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("content_type", sa.String(length=20), nullable=False),
        sa.Column("content_id", sa.Integer(), nullable=False),
        sa.Column("count", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("content_type", "content_id", name="uq_content_view"),
    )


def downgrade() -> None:
    op.drop_table("content_views")
    op.drop_index("ix_comments_content", table_name="comments")
    op.drop_index("ix_comments_created_at", table_name="comments")
    op.drop_index("ix_comments_user_id", table_name="comments")
    op.drop_table("comments")
    op.drop_index("ix_reactions_content", table_name="reactions")
    op.drop_index("ix_reactions_user_id", table_name="reactions")
    op.drop_table("reactions")
