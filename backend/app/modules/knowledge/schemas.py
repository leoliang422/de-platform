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


class KnowledgeDetail(KnowledgeListItem):
    content_md: str
