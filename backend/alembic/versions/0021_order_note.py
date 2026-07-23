"""orders: add note (充值转账备注，供管理员核对)

Revision ID: 0021
Revises: 0020
Create Date: 2026-07-23

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0021"
down_revision: str | None = "0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("note", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "note")
