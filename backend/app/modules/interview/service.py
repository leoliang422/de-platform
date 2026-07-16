from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.interview.models import Company, InterviewPost


async def get_or_create_company(db: AsyncSession, name: str) -> Company:
    result = await db.execute(select(Company).where(Company.name == name))
    company = result.scalar_one_or_none()
    if company is None:
        company = Company(name=name)
        db.add(company)
        await db.flush()
    return company


async def create_published(
    db: AsyncSession,
    *,
    company_name: str,
    position: str,
    content_md: str,
    author_id: int | None,
) -> InterviewPost:
    company = await get_or_create_company(db, company_name)
    post = InterviewPost(
        company_id=company.id,
        position=position,
        content_md=content_md,
        status="published",
        author_id=author_id,
    )
    db.add(post)
    await db.flush()
    return post
