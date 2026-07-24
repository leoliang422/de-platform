"""annotations: 补齐 quote / anchor_offset 列（历史环境对齐）

早期 0012 迁移曾在部分环境先建表（无 quote/anchor_offset），之后这两列被并入
0012；已应用过 0012 的库不会重跑，导致线上 annotations 缺列、写入 500。
本迁移幂等补列：仅当列不存在时新增，故对已含这两列的库（如本地全新建库）无副作用。

Revision ID: 0023
Revises: 0022
Create Date: 2026-07-24

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0023"
down_revision: str | None = "0022"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _existing_columns(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return {c["name"] for c in inspector.get_columns(table)}


def upgrade() -> None:
    cols = _existing_columns("annotations")
    if "quote" not in cols:
        op.add_column(
            "annotations",
            sa.Column("quote", sa.Text(), nullable=False, server_default=""),
        )
    if "anchor_offset" not in cols:
        op.add_column(
            "annotations",
            sa.Column("anchor_offset", sa.Integer(), nullable=False, server_default="0"),
        )


def downgrade() -> None:
    cols = _existing_columns("annotations")
    if "anchor_offset" in cols:
        op.drop_column("annotations", "anchor_offset")
    if "quote" in cols:
        op.drop_column("annotations", "quote")
