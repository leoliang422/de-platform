"""sql_progress: 用户 SQL 做题进度（已做 / 已掌握）

Revision ID: 0024
Revises: 0023
Create Date: 2026-07-24

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0024"
down_revision: str | None = "0023"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "sql_progress",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "question_id",
            sa.Integer(),
            sa.ForeignKey("sql_questions.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("status", sa.String(length=20), nullable=False),
        sa.UniqueConstraint("user_id", "question_id", name="uq_sql_progress"),
    )
    op.create_index("ix_sql_progress_user_id", "sql_progress", ["user_id"])
    op.create_index("ix_sql_progress_question_id", "sql_progress", ["question_id"])


def downgrade() -> None:
    op.drop_index("ix_sql_progress_question_id", table_name="sql_progress")
    op.drop_index("ix_sql_progress_user_id", table_name="sql_progress")
    op.drop_table("sql_progress")
