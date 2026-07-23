"""application_records.interview_company_id (投递记录关联面经)

Revision ID: 0017
Revises: 0016
Create Date: 2026-07-23
"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision: str = "0017"
down_revision: str | None = "0016"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    with op.batch_alter_table("application_records") as batch:
        batch.add_column(sa.Column("interview_company_id", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_application_records_interview_company",
            "companies",
            ["interview_company_id"],
            ["id"],
            ondelete="SET NULL",
        )


def downgrade() -> None:
    with op.batch_alter_table("application_records") as batch:
        batch.drop_constraint(
            "fk_application_records_interview_company", type_="foreignkey"
        )
        batch.drop_column("interview_company_id")
