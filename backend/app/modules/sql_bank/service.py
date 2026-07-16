from __future__ import annotations

from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.sql_bank.models import SqlQuestion


async def create_published(
    db: AsyncSession,
    *,
    title: str,
    prompt_md: str,
    answer_md: str,
    difficulty: str,
    tags: str,
    category_id: int | None,
    author_id: int | None,
) -> SqlQuestion:
    question = SqlQuestion(
        title=title,
        prompt_md=prompt_md,
        answer_md=answer_md,
        difficulty=difficulty,
        tags=tags,
        category_id=category_id,
        status="published",
        author_id=author_id,
    )
    db.add(question)
    await db.flush()
    return question


async def list_all(db: AsyncSession) -> list[SqlQuestion]:
    result = await db.execute(select(SqlQuestion).order_by(SqlQuestion.id.desc()))
    return list(result.scalars().all())


async def update(db: AsyncSession, question_id: int, fields: dict[str, Any]) -> SqlQuestion:
    question = await db.get(SqlQuestion, question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    for key, value in fields.items():
        setattr(question, key, value)
    await db.commit()
    await db.refresh(question)
    return question


async def delete(db: AsyncSession, question_id: int) -> None:
    question = await db.get(SqlQuestion, question_id)
    if question is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    await db.delete(question)
    await db.commit()
