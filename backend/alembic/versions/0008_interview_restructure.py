"""interview restructure: meta fields + technical/HR Q&A rows

Revision ID: 0008
Revises: 0007
Create Date: 2026-07-17

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0008"
down_revision: str | None = "0007"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "interview_posts", sa.Column("position_level", sa.String(length=60), nullable=True)
    )
    op.add_column(
        "interview_posts", sa.Column("interview_date", sa.String(length=30), nullable=True)
    )
    op.add_column("interview_posts", sa.Column("rounds", sa.Integer(), nullable=True))
    op.add_column("interview_posts", sa.Column("result", sa.String(length=20), nullable=True))
    op.add_column("interview_posts", sa.Column("city", sa.String(length=60), nullable=True))
    op.add_column("interview_posts", sa.Column("channel", sa.String(length=60), nullable=True))
    op.create_index("ix_interview_posts_position", "interview_posts", ["position"])

    op.create_table(
        "interview_qa",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "post_id",
            sa.Integer(),
            sa.ForeignKey("interview_posts.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("section", sa.String(length=20), nullable=False),
        sa.Column("order_index", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("question", sa.Text(), nullable=False, server_default=""),
        sa.Column("answer", sa.Text(), nullable=False, server_default=""),
    )
    op.create_index("ix_interview_qa_post_id", "interview_qa", ["post_id"])


def downgrade() -> None:
    op.drop_index("ix_interview_qa_post_id", table_name="interview_qa")
    op.drop_table("interview_qa")
    op.drop_index("ix_interview_posts_position", table_name="interview_posts")
    op.drop_column("interview_posts", "channel")
    op.drop_column("interview_posts", "city")
    op.drop_column("interview_posts", "result")
    op.drop_column("interview_posts", "rounds")
    op.drop_column("interview_posts", "interview_date")
    op.drop_column("interview_posts", "position_level")
