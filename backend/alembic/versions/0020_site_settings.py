"""site_settings: key-value 站点配置（管理员可改的收款码等）

Revision ID: 0020
Revises: 0019
Create Date: 2026-07-23

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0020"
down_revision: str | None = "0019"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "site_settings",
        sa.Column("key", sa.String(length=64), primary_key=True),
        sa.Column("value", sa.Text(), nullable=False, server_default=""),
    )


def downgrade() -> None:
    op.drop_table("site_settings")
