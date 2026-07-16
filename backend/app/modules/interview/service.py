from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
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


async def list_all(db: AsyncSession) -> list[InterviewPost]:
    result = await db.execute(select(InterviewPost).order_by(InterviewPost.id.desc()))
    return list(result.scalars().all())


async def update(db: AsyncSession, post_id: int, fields: dict[str, Any]) -> InterviewPost:
    post = await db.get(InterviewPost, post_id)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面经不存在")
    # 允许通过 company_name 改挂企业
    company_name = fields.pop("company_name", None)
    if company_name:
        company = await get_or_create_company(db, company_name)
        post.company_id = company.id
    for key, value in fields.items():
        setattr(post, key, value)
    await db.commit()
    await db.refresh(post)
    return post


async def delete(db: AsyncSession, post_id: int) -> None:
    post = await db.get(InterviewPost, post_id)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面经不存在")
    await db.delete(post)
    await db.commit()
