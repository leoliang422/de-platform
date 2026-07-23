"""orders: add points_delta (for 积分充值 recharge orders)

Revision ID: 0019
Revises: 0018
Create Date: 2026-07-23

充值订单复用 orders 表（item_type="recharge"）：points_delta 记录该订单确认到账后
应发放的积分数。历史内容解锁订单无此值，故可空。

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0019"
down_revision: str | None = "0018"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("points_delta", sa.Integer(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "points_delta")
