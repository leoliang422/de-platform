import datetime as dt
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TargetType = Literal["knowledge", "sql", "interview", "project"]


class SubmissionCreate(BaseModel):
    target_type: TargetType
    title: str = Field(min_length=1, max_length=200)
    raw_content: str = Field(min_length=1)

    # 通用可选：分类
    category_id: int | None = None

    # knowledge / project 付费
    is_paid: bool = False
    price_cash: Decimal | None = None
    price_points: int | None = None

    # sql
    prompt_md: str | None = None
    difficulty: str | None = None
    tags: str | None = None

    # interview
    company_name: str | None = None
    position: str | None = None

    # project
    level: str | None = None
    access_type: Literal["free", "paid"] | None = None
    implementation_md: str | None = None


class SubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    target_type: str
    title: str
    status: str
    reject_reason: str | None = None
    processed_md: str | None = None
    published_ref_id: int | None = None
    created_at: dt.datetime


class RejectIn(BaseModel):
    reason: str = Field(min_length=1, max_length=500)
