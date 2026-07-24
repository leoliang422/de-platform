from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_current_user_optional
from app.modules.access.service import AccessService
from app.modules.sql_bank.models import SqlQuestion
from app.modules.sql_bank.repository import SqlQuestionRepository
from app.modules.sql_bank.schemas import (
    SqlProgressIn,
    SqlQuestionDetail,
    SqlQuestionListItem,
)
from app.modules.users.models import User

router = APIRouter(prefix="/sql-questions", tags=["sql"])


@router.get("", response_model=list[SqlQuestionListItem])
async def list_questions(
    category_id: int | None = Query(default=None),
    user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> list[SqlQuestionListItem]:
    repo = SqlQuestionRepository(db)
    items = await repo.list_published(category_id)
    progress: dict[int, str] = {}
    if user is not None:
        progress = await repo.progress_map(user.id, [i.id for i in items])
    out: list[SqlQuestionListItem] = []
    for i in items:
        li = SqlQuestionListItem.model_validate(i)
        li.my_status = progress.get(i.id)
        out.append(li)
    return out


def _detail(
    item: SqlQuestion,
    *,
    answer_visible: bool,
    module_unlocked: bool,
    free_used: int,
    free_limit: int,
    unlock_points: int,
) -> SqlQuestionDetail:
    detail = SqlQuestionDetail.model_validate(item)
    detail.answer_md = item.answer_md if answer_visible else None
    detail.answer_locked = not answer_visible
    detail.module_unlocked = module_unlocked
    detail.free_used = free_used
    detail.free_limit = free_limit
    detail.unlock_points = unlock_points
    return detail


@router.get("/{question_id}", response_model=SqlQuestionDetail)
async def get_question(
    question_id: int,
    user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> SqlQuestionDetail:
    item = await SqlQuestionRepository(db).get(question_id)
    if item is None or item.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")

    access = AccessService(db)
    visible = await access.can_view(user, "sql", item.id, item.author_id)
    summary = await access.summary(user, "sql")
    detail = _detail(
        item,
        answer_visible=visible,
        module_unlocked=summary.unlocked,
        free_used=summary.free_used,
        free_limit=summary.free_limit,
        unlock_points=summary.unlock_points,
    )
    if user is not None:
        detail.my_status = await SqlQuestionRepository(db).get_progress(user.id, item.id)
    return detail


@router.put("/{question_id}/progress", response_model=SqlQuestionListItem)
async def set_progress(
    question_id: int,
    data: SqlProgressIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SqlQuestionListItem:
    repo = SqlQuestionRepository(db)
    item = await repo.get(question_id)
    if item is None or item.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    new_status = None if data.status == "none" else data.status
    await repo.set_progress(current_user.id, question_id, new_status)
    li = SqlQuestionListItem.model_validate(item)
    li.my_status = new_status
    return li


@router.post("/{question_id}/reveal", response_model=SqlQuestionDetail)
async def reveal_answer(
    question_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> SqlQuestionDetail:
    """查看答案：命中免费名额则消耗一次；超额且未解锁模块时返回锁定态。"""
    item = await SqlQuestionRepository(db).get(question_id)
    if item is None or item.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")

    state = await AccessService(db).reveal(current_user, "sql", item.id, item.author_id)
    return _detail(
        item,
        answer_visible=state.granted,
        module_unlocked=state.module_unlocked,
        free_used=state.free_used,
        free_limit=state.free_limit,
        unlock_points=state.unlock_points,
    )
