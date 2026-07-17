from decimal import Decimal

from pydantic import BaseModel


class ContentSummary(BaseModel):
    id: int
    title: str
    subtitle: str | None = None
    status: str


# ---- knowledge ----
class KnowledgeCreate(BaseModel):
    title: str
    content_md: str
    category_id: int | None = None
    is_paid: bool = False
    price_cash: Decimal | None = None
    price_points: int | None = None
    status: str = "published"


class KnowledgeUpdate(BaseModel):
    title: str | None = None
    content_md: str | None = None
    category_id: int | None = None
    is_paid: bool | None = None
    price_cash: Decimal | None = None
    price_points: int | None = None
    status: str | None = None


# ---- sql ----
class SqlCreate(BaseModel):
    title: str
    prompt_md: str
    answer_md: str
    difficulty: str = "medium"
    tags: str = ""
    category_id: int | None = None
    status: str = "published"


class SqlUpdate(BaseModel):
    title: str | None = None
    prompt_md: str | None = None
    answer_md: str | None = None
    difficulty: str | None = None
    tags: str | None = None
    category_id: int | None = None
    status: str | None = None


# ---- interview ----
class InterviewQAInput(BaseModel):
    section: str = "round1"  # round1 | round2 | round3 | hr
    question: str = ""
    answer: str = ""


class InterviewCreate(BaseModel):
    company_name: str
    interview_type: str | None = None  # social | campus | daily | summer
    qa_items: list[InterviewQAInput] = []
    status: str = "published"


class InterviewUpdate(BaseModel):
    company_name: str | None = None
    interview_type: str | None = None
    qa_items: list[InterviewQAInput] | None = None
    status: str | None = None


# ---- project ----
class ProjectCreate(BaseModel):
    title: str
    description_md: str
    implementation_md: str = ""
    level: str = "basic"
    access_type: str = "free"
    price_cash: Decimal | None = None
    price_points: int | None = None
    status: str = "published"


class ProjectUpdate(BaseModel):
    title: str | None = None
    description_md: str | None = None
    implementation_md: str | None = None
    level: str | None = None
    access_type: str | None = None
    price_cash: Decimal | None = None
    price_points: int | None = None
    status: str | None = None
