from __future__ import annotations

from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.models import KnowledgeItem
from app.modules.knowledge.repository import KnowledgeRepository


async def get_published(db: AsyncSession, item_id: int) -> KnowledgeItem | None:
    item = await KnowledgeRepository(db).get(item_id)
    if item is None or item.status != "published":
        return None
    return item


async def create_published(
    db: AsyncSession,
    *,
    title: str,
    content_md: str,
    category_id: int | None,
    is_paid: bool,
    price_cash: Decimal | None,
    price_points: int | None,
    author_id: int | None,
) -> KnowledgeItem:
    item = KnowledgeItem(
        title=title,
        content_md=content_md,
        category_id=category_id,
        is_paid=is_paid,
        price_cash=price_cash,
        price_points=price_points,
        status="published",
        author_id=author_id,
    )
    db.add(item)
    await db.flush()
    return item
