"""submissions + point_ledger

Revision ID: 0003
Revises: 0002
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "point_ledger",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("delta", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=100), nullable=False),
        sa.Column("ref_type", sa.String(length=30), nullable=False),
        sa.Column("ref_id", sa.Integer(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.UniqueConstraint("ref_type", "ref_id", name="uq_point_ledger_ref"),
    )
    op.create_index("ix_point_ledger_user_id", "point_ledger", ["user_id"])

    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "user_id",
            sa.Integer(),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("target_type", sa.String(length=20), nullable=False),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("raw_content", sa.Text(), nullable=False),
        sa.Column("processed_md", sa.Text(), nullable=True),
        sa.Column("extra", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="draft", nullable=False),
        sa.Column("reject_reason", sa.String(length=500), nullable=True),
        sa.Column("published_ref_id", sa.Integer(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_submissions_user_id", "submissions", ["user_id"])
    op.create_index("ix_submissions_status", "submissions", ["status"])


def downgrade() -> None:
    op.drop_index("ix_submissions_status", table_name="submissions")
    op.drop_index("ix_submissions_user_id", table_name="submissions")
    op.drop_table("submissions")
    op.drop_index("ix_point_ledger_user_id", table_name="point_ledger")
    op.drop_table("point_ledger")
