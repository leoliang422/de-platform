from pydantic import BaseModel, ConfigDict


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    logo_url: str | None = None


class InterviewPostListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_id: int
    position: str


class InterviewPostDetail(InterviewPostListItem):
    content_md: str
