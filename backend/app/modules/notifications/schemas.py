import datetime as dt

from pydantic import BaseModel, ConfigDict


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    type: str
    title: str
    body: str | None = None
    link: str | None = None
    read_at: dt.datetime | None = None
    created_at: dt.datetime


class UnreadCountOut(BaseModel):
    unread: int
