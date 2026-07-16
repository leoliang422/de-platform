from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.submissions.models import Submission


class SubmissionRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get(self, submission_id: int) -> Submission | None:
        return await self.db.get(Submission, submission_id)

    async def list_by_user(self, user_id: int) -> list[Submission]:
        stmt = (
            select(Submission).where(Submission.user_id == user_id).order_by(Submission.id.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def list_by_status(self, status: str | None = None) -> list[Submission]:
        stmt = select(Submission)
        if status is not None:
            stmt = stmt.where(Submission.status == status)
        stmt = stmt.order_by(Submission.id.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
