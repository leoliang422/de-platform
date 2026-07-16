from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import Category


class CategoryRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_by_section(self, section: str) -> list[Category]:
        result = await self.db.execute(
            select(Category)
            .where(Category.section == section)
            .order_by(Category.order, Category.id)
        )
        return list(result.scalars().all())
