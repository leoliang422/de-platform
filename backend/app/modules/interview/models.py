from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# 面经类型：社招 / 校招 / 日常实习 / 暑期实习。
INTERVIEW_TYPES = ("social", "campus", "daily", "summer")
# 面试轮次（问答归属）：一面 / 二面 / 三面 / HR 面。
ROUND_SECTIONS = ("round1", "round2", "round3", "hr")


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    logo_url: Mapped[str | None] = mapped_column(String(500), nullable=True)


class InterviewPost(Base):
    __tablename__ = "interview_posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    company_id: Mapped[int] = mapped_column(
        ForeignKey("companies.id", ondelete="CASCADE"), nullable=False, index=True
    )
    title: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    # 类型：social / campus / daily / summer
    interview_type: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    # 整体感受 / 概述
    content_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 兼容旧库列（不再对外使用）：保留默认空串以满足历史 NOT NULL 约束。
    position: Mapped[str] = mapped_column(String(120), nullable=False, default="")
    status: Mapped[str] = mapped_column(String(20), default="published", nullable=False)
    author_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    qa: Mapped[list["InterviewQA"]] = relationship(
        "InterviewQA",
        cascade="all, delete-orphan",
        order_by="InterviewQA.order_index, InterviewQA.id",
        lazy="selectin",
    )


class InterviewQA(Base):
    """面经中的一问一答，归属某一轮次（一面/二面/三面/HR 面）。"""

    __tablename__ = "interview_qa"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("interview_posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section: Mapped[str] = mapped_column(String(20), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False, default="")
    answer: Mapped[str] = mapped_column(Text, nullable=False, default="")
