from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class KnowledgeListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int | None = None
    title: str
    is_paid: bool
    price_cash: Decimal | None = None
    price_points: int | None = None
    # 互动指标（用于热度排序与角标）
    views: int = 0
    likes: int = 0
    favorites: int = 0
    comments: int = 0
    hotness: int = 0


class KnowledgeListPage(BaseModel):
    items: list[KnowledgeListItem]
    total: int
    page: int
    page_size: int


class KnowledgeDetail(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int | None = None
    title: str
    is_paid: bool
    price_cash: Decimal | None = None
    price_points: int | None = None
    locked: bool = False
    content_md: str | None = None
