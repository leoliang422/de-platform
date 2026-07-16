from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sql_bank.models import SqlQuestion


class SqlQuestionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_published(self, category_id: int | None = None) -> list[SqlQuestion]:
        stmt = select(SqlQuestion).where(SqlQuestion.status == "published")
        if category_id is not None:
            stmt = stmt.where(SqlQuestion.category_id == category_id)
        stmt = stmt.order_by(SqlQuestion.id.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get(self, question_id: int) -> SqlQuestion | None:
        return await self.db.get(SqlQuestion, question_id)
