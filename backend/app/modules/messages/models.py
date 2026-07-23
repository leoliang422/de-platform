"""用户 ↔ 管理员 私信。

每个普通用户与「管理员」之间是一条会话，以 ``user_id`` 标识会话归属：
- 用户发的消息：``from_admin=False``，``sender_id`` = 该用户。
- 管理员回复：``from_admin=True``，``sender_id`` = 具体管理员 id。
``read_at`` 表示「被接收方读过」的时间（用户读管理员消息 / 管理员读用户消息）。
"""

import datetime as dt

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Text, func
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
    read_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
