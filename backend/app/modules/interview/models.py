from sqlalchemy import ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

# 面经问答所属环节：技术面 / HR 面。
QA_SECTIONS = ("technical", "hr")
# 面试结果。
INTERVIEW_RESULTS = ("pass", "fail", "pending", "unknown")


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
    position: Mapped[str] = mapped_column(String(120), nullable=False, index=True)
    # 整体感受/概述（可选）；结构化问答见 InterviewQA。
    content_md: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 面试元信息
    position_level: Mapped[str | None] = mapped_column(String(60), nullable=True)
    interview_date: Mapped[str | None] = mapped_column(String(30), nullable=True)
    rounds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    result: Mapped[str | None] = mapped_column(String(20), nullable=True)
    city: Mapped[str | None] = mapped_column(String(60), nullable=True)
    channel: Mapped[str | None] = mapped_column(String(60), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="published", nullable=False)
    author_id: Mapped[int | None] = mapped_column(Integer, nullable=True)

    qa: Mapped[list["InterviewQA"]] = relationship(
        "InterviewQA",
        cascade="all, delete-orphan",
        order_by="InterviewQA.section, InterviewQA.order_index, InterviewQA.id",
        lazy="selectin",
    )


class InterviewQA(Base):
    """面经中的一问一答，归属技术面或 HR 面。"""

    __tablename__ = "interview_qa"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    post_id: Mapped[int] = mapped_column(
        ForeignKey("interview_posts.id", ondelete="CASCADE"), nullable=False, index=True
    )
    section: Mapped[str] = mapped_column(String(20), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    question: Mapped[str] = mapped_column(Text, nullable=False, default="")
    answer: Mapped[str] = mapped_column(Text, nullable=False, default="")
