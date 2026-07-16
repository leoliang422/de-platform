import datetime as dt
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# 状态机：draft → processing → pending_review → published
#                                     ↘ rejected → (可退回) draft
STATUSES = ("draft", "processing", "pending_review", "published", "rejected")
TARGET_TYPES = ("knowledge", "sql", "interview", "project")


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    target_type: Mapped[str] = mapped_column(String(20), nullable=False)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    raw_content: Mapped[str] = mapped_column(Text, nullable=False, default="")
    processed_md: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 类型相关的结构化字段（category_id / difficulty / tags / company_name / 价格等）。
    extra: Mapped[dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft", nullable=False, index=True)
    reject_reason: Mapped[str | None] = mapped_column(String(500), nullable=True)
    # 发布后指向新建内容的主键，便于溯源。
    published_ref_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )
