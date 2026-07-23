"""用户 ↔ 管理员 私信。

每个普通用户与「管理员」之间是一条会话，以 ``user_id`` 标识会话归属：
- 用户发的消息：``from_admin=False``，``sender_id`` = 该用户。
- 管理员回复：``from_admin=True``，``sender_id`` = 具体管理员 id。
``read_at`` 表示「被接收方读过」的时间（用户读管理员消息 / 管理员读用户消息）。
"""

import datetime as dt

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ContactMessage(Base):
    __tablename__ = "contact_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    # 会话归属的普通用户（不是发送者）。
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    from_admin: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    sender_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    body: Mapped[str] = mapped_column(Text, nullable=False, default="")
    # 附件（图片/文件）：url + 原文件名 + 类型（image / file）。纯文本消息为空。
    attachment_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    attachment_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    attachment_kind: Mapped[str | None] = mapped_column(String(10), nullable=True)
    read_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class ConversationState(Base):
    """管理员对某个用户会话的管理状态：置顶 / 屏蔽（用户被屏蔽后无法再发私信）。"""

    __tablename__ = "contact_conversation_states"

    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), primary_key=True
    )
    pinned: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    blocked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
