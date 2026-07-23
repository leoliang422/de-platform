import datetime as dt

from pydantic import BaseModel, ConfigDict, Field


class MessageOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    from_admin: bool
    body: str
    read_at: dt.datetime | None = None
    created_at: dt.datetime


class SendMessageIn(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


class UnreadCountOut(BaseModel):
    unread: int


class ConversationOut(BaseModel):
    """管理员侧的会话摘要（每个用户一条）。"""

    user_id: int
    nickname: str
    avatar_url: str | None = None
    last_body: str
    last_at: dt.datetime
    unread: int
