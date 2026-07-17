from __future__ import annotations

from collections import OrderedDict
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.interview.models import QA_SECTIONS, Company, InterviewPost, InterviewQA


async def get_or_create_company(db: AsyncSession, name: str) -> Company:
    result = await db.execute(select(Company).where(Company.name == name))
    company = result.scalar_one_or_none()
    if company is None:
        company = Company(name=name)
        db.add(company)
        await db.flush()
    return company


def _build_qa_rows(qa_items: list[dict[str, Any]] | None) -> list[InterviewQA]:
    """把 [{section, question, answer}] 转成 InterviewQA 行，按 section 内顺序编号。"""
    rows: list[InterviewQA] = []
    counters = {section: 0 for section in QA_SECTIONS}
    for item in qa_items or []:
        section = item.get("section")
        if section not in QA_SECTIONS:
            section = "technical"
        question = (item.get("question") or "").strip()
        answer = (item.get("answer") or "").strip()
        if not question and not answer:
            continue
        rows.append(
            InterviewQA(
                section=section,
                order_index=counters[section],
                question=question,
                answer=answer,
            )
        )
        counters[section] += 1
    return rows


async def create_published(
    db: AsyncSession,
    *,
    company_name: str,
    position: str,
    content_md: str = "",
    qa_items: list[dict[str, Any]] | None = None,
    position_level: str | None = None,
    interview_date: str | None = None,
    rounds: int | None = None,
    result: str | None = None,
    city: str | None = None,
    channel: str | None = None,
    author_id: int | None = None,
    status_value: str = "published",
) -> InterviewPost:
    company = await get_or_create_company(db, company_name)
    post = InterviewPost(
        company_id=company.id,
        position=position,
        content_md=content_md,
        position_level=position_level,
        interview_date=interview_date,
        rounds=rounds,
        result=result,
        city=city,
        channel=channel,
        status=status_value,
        author_id=author_id,
        qa=_build_qa_rows(qa_items),
    )
    db.add(post)
    await db.flush()
    return post


async def list_all(db: AsyncSession) -> list[InterviewPost]:
    result = await db.execute(select(InterviewPost).order_by(InterviewPost.id.desc()))
    return list(result.scalars().all())


def group_by_position(posts: list[InterviewPost]) -> list[dict[str, Any]]:
    """把面经按岗位聚合（相同岗位合并）。"""
    groups: OrderedDict[str, list[InterviewPost]] = OrderedDict()
    for post in posts:
        groups.setdefault(post.position, []).append(post)
    return [
        {"position": position, "count": len(items), "posts": items}
        for position, items in groups.items()
    ]


async def update(db: AsyncSession, post_id: int, fields: dict[str, Any]) -> InterviewPost:
    post = await db.get(InterviewPost, post_id)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面经不存在")

    company_name = fields.pop("company_name", None)
    if company_name:
        company = await get_or_create_company(db, company_name)
        post.company_id = company.id

    # 提供了 qa_items 则整体替换问答（orphan 由 cascade 删除）
    qa_items = fields.pop("qa_items", None)
    if qa_items is not None:
        post.qa = _build_qa_rows(qa_items)

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
