from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sql_bank.models import SqlProgress, SqlQuestion


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

    # ---- 做题进度 ----
    async def progress_map(self, user_id: int, question_ids: list[int]) -> dict[int, str]:
        if not question_ids:
            return {}
        rows = (
            await self.db.execute(
                select(SqlProgress.question_id, SqlProgress.status).where(
                    SqlProgress.user_id == user_id,
                    SqlProgress.question_id.in_(question_ids),
                )
            )
        ).all()
        return {qid: st for qid, st in rows}

    async def get_progress(self, user_id: int, question_id: int) -> str | None:
        return await self.db.scalar(
            select(SqlProgress.status).where(
                SqlProgress.user_id == user_id, SqlProgress.question_id == question_id
            )
        )

    async def set_progress(self, user_id: int, question_id: int, status: str | None) -> None:
        """status 为 None/空 时清除进度；否则 upsert。"""
        existing = await self.db.scalar(
            select(SqlProgress).where(
                SqlProgress.user_id == user_id, SqlProgress.question_id == question_id
            )
        )
        if not status:
            if existing is not None:
                await self.db.delete(existing)
        elif existing is None:
            self.db.add(SqlProgress(user_id=user_id, question_id=question_id, status=status))
        else:
            existing.status = status
        await self.db.commit()
