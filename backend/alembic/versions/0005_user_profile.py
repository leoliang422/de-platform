"""user profile fields: avatar_url / bio / job_title

Revision ID: 0005
Revises: 0004
Create Date: 2026-07-17

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_url", sa.String(length=500), nullable=True))
    op.add_column("users", sa.Column("bio", sa.String(length=500), nullable=True))
    op.add_column("users", sa.Column("job_title", sa.String(length=100), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "job_title")
    op.drop_column("users", "bio")
    op.drop_column("users", "avatar_url")
