"""content tables: categories, knowledge, sql, interview, projects

Revision ID: 0002
Revises: 0001
Create Date: 2026-07-16

"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "categories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "parent_id",
            sa.Integer(),
            sa.ForeignKey("categories.id", ondelete="CASCADE"),
            nullable=True,
        ),
        sa.Column("section", sa.String(length=20), nullable=False),
        sa.Column("name", sa.String(length=100), nullable=False),
        sa.Column("slug", sa.String(length=120), nullable=False),
        sa.Column("order", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_index("ix_categories_parent_id", "categories", ["parent_id"])
    op.create_index("ix_categories_section", "categories", ["section"])

    op.create_table(
        "knowledge_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("is_paid", sa.Boolean(), server_default=sa.false(), nullable=False),
        sa.Column("price_cash", sa.Numeric(10, 2), nullable=True),
        sa.Column("price_points", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="published", nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_knowledge_items_category_id", "knowledge_items", ["category_id"])

    op.create_table(
        "sql_questions",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "category_id",
            sa.Integer(),
            sa.ForeignKey("categories.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("difficulty", sa.String(length=20), server_default="medium", nullable=False),
        sa.Column("prompt_md", sa.Text(), nullable=False),
        sa.Column("answer_md", sa.Text(), nullable=False),
        sa.Column("tags", sa.String(length=255), server_default="", nullable=False),
        sa.Column("status", sa.String(length=20), server_default="published", nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_sql_questions_category_id", "sql_questions", ["category_id"])

    op.create_table(
        "companies",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=120), nullable=False),
        sa.Column("logo_url", sa.String(length=500), nullable=True),
    )
    op.create_index("ix_companies_name", "companies", ["name"], unique=True)

    op.create_table(
        "interview_posts",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "company_id",
            sa.Integer(),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("position", sa.String(length=120), nullable=False),
        sa.Column("content_md", sa.Text(), nullable=False),
        sa.Column("status", sa.String(length=20), server_default="published", nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=True),
    )
    op.create_index("ix_interview_posts_company_id", "interview_posts", ["company_id"])

    op.create_table(
        "projects",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("title", sa.String(length=200), nullable=False),
        sa.Column("description_md", sa.Text(), nullable=False),
        sa.Column("implementation_md", sa.Text(), nullable=False),
        sa.Column("level", sa.String(length=20), server_default="basic", nullable=False),
        sa.Column("access_type", sa.String(length=10), server_default="free", nullable=False),
        sa.Column("price_cash", sa.Numeric(10, 2), nullable=True),
        sa.Column("price_points", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=20), server_default="published", nullable=False),
        sa.Column("author_id", sa.Integer(), nullable=True),
    )

    op.create_table(
        "project_qa",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "project_id",
            sa.Integer(),
            sa.ForeignKey("projects.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("question_md", sa.Text(), nullable=False),
        sa.Column("answer_md", sa.Text(), nullable=False),
        sa.Column("order", sa.Integer(), server_default="0", nullable=False),
    )
    op.create_index("ix_project_qa_project_id", "project_qa", ["project_id"])


def downgrade() -> None:
    op.drop_index("ix_project_qa_project_id", table_name="project_qa")
    op.drop_table("project_qa")
    op.drop_table("projects")
    op.drop_index("ix_interview_posts_company_id", table_name="interview_posts")
    op.drop_table("interview_posts")
    op.drop_index("ix_companies_name", table_name="companies")
    op.drop_table("companies")
    op.drop_index("ix_sql_questions_category_id", table_name="sql_questions")
    op.drop_table("sql_questions")
    op.drop_index("ix_knowledge_items_category_id", table_name="knowledge_items")
    op.drop_table("knowledge_items")
    op.drop_index("ix_categories_section", table_name="categories")
    op.drop_index("ix_categories_parent_id", table_name="categories")
    op.drop_table("categories")
