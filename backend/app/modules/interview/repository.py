from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.interview.models import Company, InterviewPost


class InterviewRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_companies(self) -> list[Company]:
        result = await self.db.execute(select(Company).order_by(Company.name))
        return list(result.scalars().all())

    async def get_company(self, company_id: int) -> Company | None:
        return await self.db.get(Company, company_id)

    async def list_posts_by_company(self, company_id: int) -> list[InterviewPost]:
        result = await self.db.execute(
            select(InterviewPost)
            .where(
                InterviewPost.company_id == company_id,
                InterviewPost.status == "published",
            )
            .order_by(InterviewPost.id.desc())
        )
        return list(result.scalars().all())

    async def list_posts_by_author(
        self, author_id: int, company_name: str | None = None
    ) -> list[InterviewPost]:
        stmt = select(InterviewPost).where(
            InterviewPost.author_id == author_id,
            InterviewPost.status == "published",
        )
        if company_name and company_name.strip():
            stmt = stmt.join(Company, Company.id == InterviewPost.company_id).where(
                func.lower(Company.name) == company_name.strip().lower()
            )
        stmt = stmt.order_by(InterviewPost.id.desc())
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def get_post(self, post_id: int) -> InterviewPost | None:
        return await self.db.get(InterviewPost, post_id)
