import datetime as dt
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

TargetType = Literal["knowledge", "sql", "interview", "project"]


class InterviewQAIn(BaseModel):
    # 上传时即区分所属轮次（一面/二面/三面/HR面），以及问题与答案。
    section: Literal["round1", "round2", "round3", "hr"] = "round1"
    question: str = Field(default="", max_length=4000)
    answer: str = Field(default="", max_length=8000)


class SubmissionCreate(BaseModel):
    target_type: TargetType
    # 面经无标题/无正文（整体感受已去掉），标题/正文按类型在 service 层校验。
    title: str = Field(default="", max_length=200)
    raw_content: str = Field(default="")

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
    interview_type: Literal["social", "campus", "daily", "summer"] | None = None
    qa_items: list[InterviewQAIn] | None = None

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
