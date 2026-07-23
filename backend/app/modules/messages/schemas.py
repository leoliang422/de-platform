import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_admin: bool
    body: str
    attachment_url: str | None = None
    attachment_name: str | None = None
    attachment_kind: str | None = None
    read_at: dt.datetime | None = None
    created_at: dt.datetime


class SendMessageIn(BaseModel):
    body: str = Field(default="", max_length=4000)
    attachment_url: str | None = Field(default=None, max_length=500)
    attachment_name: str | None = Field(default=None, max_length=255)
    attachment_kind: Literal["image", "file"] | None = None

    @model_validator(mode="after")
    def _require_content(self) -> "SendMessageIn":
        if not self.body.strip() and not self.attachment_url:
            raise ValueError("消息内容不能为空")
        return self


class UnreadCountOut(BaseModel):
    unread: int


class ConversationOut(BaseModel):
    """管理员侧的会话摘要（每个用户一条）。"""

    user_id: int
    nickname: str
    avatar_url: str | None = None
    last_body: str
    last_at: dt.datetime | None = None
    unread: int
    pinned: bool = False
    blocked: bool = False


class ConversationStateIn(BaseModel):
    """管理员更新会话状态（置顶 / 屏蔽），只传需要改的字段。"""

    pinned: bool | None = None
    blocked: bool | None = None


class ConversationStateOut(BaseModel):
    pinned: bool
    blocked: bool
