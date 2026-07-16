from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.models import KnowledgeItem


class KnowledgeRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_published(self, category_id: int | None = None) -> list[KnowledgeItem]:
        stmt = select(KnowledgeItem).where(KnowledgeItem.status == "published")
        if category_id is not None:
            stmt = stmt.where(KnowledgeItem.category_id == category_id)
        stmt = stmt.order_by(KnowledgeItem.id.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get(self, item_id: int) -> KnowledgeItem | None:
        return await self.db.get(KnowledgeItem, item_id)
