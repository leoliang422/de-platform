"""contact messages (用户 ↔ 管理员私信)

Revision ID: 0016
Revises: 0015
Create Date: 2026-07-23
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0016"
down_revision: str | None = "0015"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    op.create_table(
        "contact_messages",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("from_admin", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("sender_id", sa.Integer(), nullable=True),
        sa.Column("body", sa.Text(), nullable=False, server_default=""),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index("ix_contact_messages_user_id", "contact_messages", ["user_id"])
    op.create_index("ix_contact_messages_created_at", "contact_messages", ["created_at"])


def downgrade() -> None:
    op.drop_index("ix_contact_messages_created_at", table_name="contact_messages")
    op.drop_index("ix_contact_messages_user_id", table_name="contact_messages")
    op.drop_table("contact_messages")
