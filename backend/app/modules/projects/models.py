from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class Project(Base):
    __tablename__ = "projects"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    description_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    implementation_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    level: Mapped[str] = mapped_column(String(20), default="basic", nullable=False)
    access_type: Mapped[str] = mapped_column(String(10), default="free", nullable=False)
    price_cash: Mapped[Decimal | None] = mapped_column(Numeric(10, 2), nullable=True)
    price_points: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="published", nullable=False)
    author_id: Mapped[int | None] = mapped_column(Integer, nullable=True)


class ProjectQA(Base):
    __tablename__ = "project_qa"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    project_id: Mapped[int] = mapped_column(
        ForeignKey("projects.id", ondelete="CASCADE"), nullable=False, index=True
    )
    question_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    answer_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    order: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
