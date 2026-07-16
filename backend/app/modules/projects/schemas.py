from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ProjectListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    level: str
    access_type: str
    price_cash: Decimal | None = None
    price_points: int | None = None


class ProjectQAOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    question_md: str
    answer_md: str
    order: int


class ProjectDetail(ProjectListItem):
    description_md: str
    # 付费项目在未解锁时锁定实现与问答（解锁逻辑见 M3）
    locked: bool
    implementation_md: str | None = None
    qa: list[ProjectQAOut] = []
