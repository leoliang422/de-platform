from __future__ import annotations

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
