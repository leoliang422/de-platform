"""interview: add title + interview_type (redesign)

Revision ID: 0010
Revises: 0009
Create Date: 2026-07-17

保留旧列（position/city/result/...）不做破坏性删除，仅新增 title / interview_type。
新问答按轮次归属（round1/round2/round3/hr），复用既有 interview_qa.section 列。

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "interview_posts",
        sa.Column("title", sa.String(length=200), nullable=False, server_default=""),
    )
    op.add_column(
        "interview_posts", sa.Column("interview_type", sa.String(length=20), nullable=True)
    )
    op.create_index("ix_interview_posts_interview_type", "interview_posts", ["interview_type"])


def downgrade() -> None:
    op.drop_index("ix_interview_posts_interview_type", table_name="interview_posts")
    op.drop_column("interview_posts", "interview_type")
    op.drop_column("interview_posts", "title")
