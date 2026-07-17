from pydantic import BaseModel, ConfigDict


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    logo_url: str | None = None


class InterviewQAOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    section: str
    order_index: int
    question: str
    answer: str


class InterviewPostListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    position: str
    position_level: str | None = None
    interview_date: str | None = None
    rounds: int | None = None
    result: str | None = None
    city: str | None = None
    channel: str | None = None


class InterviewPostDetail(InterviewPostListItem):
    content_md: str
    technical_qa: list[InterviewQAOut] = []
    hr_qa: list[InterviewQAOut] = []


class PositionGroup(BaseModel):
    """同一企业下按岗位聚合的面经。"""

    position: str
    count: int
    posts: list[InterviewPostListItem]
