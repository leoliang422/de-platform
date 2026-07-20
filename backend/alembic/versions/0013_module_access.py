"""module access log (积分化模块级访问控制)

Revision ID: 0013
Revises: 0012
Create Date: 2026-07-20
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0013"
down_revision: str | None = "0012"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "module_access_log",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("module", sa.String(length=20), nullable=False),
        sa.Column("item_id", sa.Integer(), nullable=False, server_default="0"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.UniqueConstraint("user_id", "module", "item_id", name="uq_module_access"),
    )
    op.create_index("ix_module_access_log_user_id", "module_access_log", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_module_access_log_user_id", table_name="module_access_log")
    op.drop_table("module_access_log")
