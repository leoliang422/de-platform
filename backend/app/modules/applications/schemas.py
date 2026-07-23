import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

Nature = Literal["state", "private", "foreign", "other"]
ApplicationStatus = Literal[
    "applied",
    "resume_fail",
    "written",
    "written_fail",
    "round1",
    "round1_fail",
    "round2",
    "round2_fail",
    "round3",
    "round3_fail",
    "hr",
    "hr_fail",
    "rejected",
    "offer",
]


# ---- 投递记录 ----
class RecordCreate(BaseModel):
    company_name: str = Field(default="", max_length=120)
    nature: Nature | None = None
    position: str = Field(default="", max_length=120)
    applied_date: dt.date | None = None
    status: ApplicationStatus = "applied"


class RecordUpdate(BaseModel):
    company_name: str | None = Field(default=None, max_length=120)
    nature: Nature | None = None
    position: str | None = Field(default=None, max_length=120)
    applied_date: dt.date | None = None
    status: ApplicationStatus | None = None


class RecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    list_id: int
    company_name: str
    nature: str | None = None
    position: str
    applied_date: dt.date | None = None
    status: str
    order_index: int
    # 若当前用户为该公司投过面经，则为对应公司 id（前端可直接跳转），否则 None。
    interview_company_id: int | None = None


# ---- 投递列表 ----
class ListCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ListUpdate(BaseModel):
    name: str = Field(min_length=1, max_length=100)


class ListOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    order_index: int
    records: list[RecordOut] = []


# ---- 面试日历 ----
class CalendarEventCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    event_date: dt.date
    start_time: str | None = Field(default=None, max_length=5)
    end_time: str | None = Field(default=None, max_length=5)
    note: str | None = None
    color: str | None = Field(default=None, max_length=20)


class CalendarEventUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    event_date: dt.date | None = None
    start_time: str | None = Field(default=None, max_length=5)
    end_time: str | None = Field(default=None, max_length=5)
    note: str | None = None
    color: str | None = Field(default=None, max_length=20)


class CalendarEventOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    event_date: dt.date
    start_time: str | None = None
    end_time: str | None = None
    note: str | None = None
    color: str | None = None
