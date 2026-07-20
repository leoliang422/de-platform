import datetime as dt

from sqlalchemy import (
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base

# 可互动的内容类型（与四大板块一致）。
CONTENT_TYPES = ("knowledge", "sql", "interview", "project")
# 反应类型：点赞 / 收藏。
REACTION_KINDS = ("like", "favorite")


class Reaction(Base):
    """用户对某内容的点赞 / 收藏（一条一种）。"""

    __tablename__ = "reactions"
    __table_args__ = (
        UniqueConstraint("user_id", "content_type", "content_id", "kind", name="uq_reaction"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content_type: Mapped[str] = mapped_column(String(20), nullable=False)
    content_id: Mapped[int] = mapped_column(Integer, nullable=False)
    kind: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class Comment(Base):
    """内容下的评论；``parent_id`` 非空表示对某评论的回复。"""

    __tablename__ = "comments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content_type: Mapped[str] = mapped_column(String(20), nullable=False)
    content_id: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("comments.id", ondelete="CASCADE"), nullable=True
    )
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class Annotation(Base):
    """划词批注：选中正文某段文字后附加的笔记；全员可见、无需审核。

    ``quote`` 保存被选中的文字，``anchor_offset`` 为其在正文纯文本中的起始字符偏移，
    用于在阅读端定位并高亮。``parent_id`` 非空表示对某条批注的回复。
    """

    __tablename__ = "annotations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content_type: Mapped[str] = mapped_column(String(20), nullable=False)
    content_id: Mapped[int] = mapped_column(Integer, nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        ForeignKey("annotations.id", ondelete="CASCADE"), nullable=True
    )
    quote: Mapped[str] = mapped_column(Text, nullable=False, default="")
    anchor_offset: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class ContentView(Base):
    """内容浏览量计数（每种内容一行）。"""

    __tablename__ = "content_views"
    __table_args__ = (UniqueConstraint("content_type", "content_id", name="uq_content_view"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content_type: Mapped[str] = mapped_column(String(20), nullable=False)
    content_id: Mapped[int] = mapped_column(Integer, nullable=False)
    count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
