"""contact_messages attachments (私信附件：图片/文件)

Revision ID: 0018
Revises: 0017
Create Date: 2026-07-23
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0018"
down_revision: str | None = "0017"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    with op.batch_alter_table("contact_messages") as batch:
        batch.add_column(sa.Column("attachment_url", sa.String(length=500), nullable=True))
        batch.add_column(sa.Column("attachment_name", sa.String(length=255), nullable=True))
        batch.add_column(sa.Column("attachment_kind", sa.String(length=10), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("contact_messages") as batch:
        batch.drop_column("attachment_kind")
        batch.drop_column("attachment_name")
        batch.drop_column("attachment_url")
