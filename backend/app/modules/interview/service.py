from __future__ import annotations

from collections import OrderedDict
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.interview.models import (
    INTERVIEW_TYPES,
    ROUND_SECTIONS,
    Company,
    InterviewPost,
    InterviewQA,
)
from app.modules.interview.schemas import (
    InterviewCardOut,
    InterviewQAOut,
    InterviewTypeGroup,
)
from app.modules.users.models import User

# 轮次展示顺序
_ROUND_ORDER = {sec: i for i, sec in enumerate(ROUND_SECTIONS)}


async def get_or_create_company(db: AsyncSession, name: str) -> Company:
    result = await db.execute(select(Company).where(Company.name == name))
    company = result.scalar_one_or_none()
    if company is None:
        company = Company(name=name)
        db.add(company)
        await db.flush()
    return company


def _build_qa_rows(qa_items: list[dict[str, Any]] | None) -> list[InterviewQA]:
    rows: list[InterviewQA] = []
    order = 0
    for item in qa_items or []:
        section = item.get("section")
        if section not in ROUND_SECTIONS:
            section = "round1"
        question = (item.get("question") or "").strip()
        answer = (item.get("answer") or "").strip()
        if not question and not answer:
            continue
        rows.append(
            InterviewQA(section=section, order_index=order, question=question, answer=answer)
        )
        order += 1
    return rows


async def create_published(
    db: AsyncSession,
    *,
    company_name: str,
    title: str,
    content_md: str = "",
    position: str = "",
    interview_type: str | None = None,
    qa_items: list[dict[str, Any]] | None = None,
    author_id: int | None = None,
    status_value: str = "published",
) -> InterviewPost:
    company = await get_or_create_company(db, company_name)
    post = InterviewPost(
        company_id=company.id,
        title=title,
        content_md=content_md,
        position=(position or "").strip(),
        interview_type=interview_type,
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


def _rounds_covered(post: InterviewPost) -> list[str]:
    seen = {qa.section for qa in post.qa}
    return [sec for sec in ROUND_SECTIONS if sec in seen]


def _to_card(post: InterviewPost, author: User | None, locked: bool = False) -> InterviewCardOut:
    ordered = sorted(post.qa, key=lambda q: (_ROUND_ORDER.get(q.section, 99), q.order_index, q.id))
    return InterviewCardOut(
        id=post.id,
        company_id=post.company_id,
        title=post.title,
        position=post.position or "",
        interview_type=post.interview_type,
        content_md="" if locked else post.content_md,
        author_id=post.author_id,
        author_nickname=author.nickname if author else "匿名用户",
        author_avatar=author.avatar_url if author else None,
        rounds_covered=_rounds_covered(post),
        qa=[] if locked else [InterviewQAOut.model_validate(q) for q in ordered],
        locked=locked,
    )


async def _authors_map(db: AsyncSession, posts: list[InterviewPost]) -> dict[int, User]:
    ids = {p.author_id for p in posts if p.author_id is not None}
    if not ids:
        return {}
    rows = (await db.execute(select(User).where(User.id.in_(ids)))).scalars().all()
    return {u.id: u for u in rows}


async def list_cards_by_type(
    db: AsyncSession, posts: list[InterviewPost], user: User | None = None
) -> list[InterviewTypeGroup]:
    from app.modules.access.service import AccessService

    access = AccessService(db)
    authors = await _authors_map(db, posts)
    groups: OrderedDict[str, list[InterviewCardOut]] = OrderedDict((t, []) for t in INTERVIEW_TYPES)
    other: list[InterviewCardOut] = []
    for post in posts:
        # 只读判断（不消耗免费名额）：锁定的卡片隐藏问答，前端点击"查看"时再消耗。
        visible = await access.can_view(user, "interview", post.id, post.author_id)
        author = authors.get(post.author_id) if post.author_id else None
        card = _to_card(post, author, locked=not visible)
        key = post.interview_type if post.interview_type in INTERVIEW_TYPES else None
        if key is None:
            other.append(card)
        else:
            groups[key].append(card)
    result = [
        InterviewTypeGroup(interview_type=t, count=len(cards), posts=cards)
        for t, cards in groups.items()
    ]
    if other:
        result.append(InterviewTypeGroup(interview_type="other", count=len(other), posts=other))
    return result


async def to_card_detail(
    db: AsyncSession, post: InterviewPost, locked: bool = False
) -> InterviewCardOut:
    author = await db.get(User, post.author_id) if post.author_id else None
    return _to_card(post, author, locked=locked)


async def list_mine(
    db: AsyncSession, author_id: int, company_name: str | None = None
) -> list[InterviewCardOut]:
    """当前用户自己上传的面经（可按公司名过滤），本人内容始终可见。"""
    from app.modules.interview.repository import InterviewRepository

    posts = await InterviewRepository(db).list_posts_by_author(author_id, company_name)
    author = await db.get(User, author_id)
    return [_to_card(post, author, locked=False) for post in posts]


async def update(db: AsyncSession, post_id: int, fields: dict[str, Any]) -> InterviewPost:
    post = await db.get(InterviewPost, post_id)
    if post is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="面经不存在")

    company_name = fields.pop("company_name", None)
    if company_name:
        company = await get_or_create_company(db, company_name)
        post.company_id = company.id

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
