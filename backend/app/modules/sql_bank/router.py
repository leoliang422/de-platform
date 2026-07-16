from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.sql_bank.repository import SqlQuestionRepository
from app.modules.sql_bank.schemas import SqlQuestionDetail, SqlQuestionListItem

router = APIRouter(prefix="/sql-questions", tags=["sql"])


@router.get("", response_model=list[SqlQuestionListItem])
async def list_questions(
    category_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[SqlQuestionListItem]:
    items = await SqlQuestionRepository(db).list_published(category_id)
    return [SqlQuestionListItem.model_validate(i) for i in items]


@router.get("/{question_id}", response_model=SqlQuestionDetail)
async def get_question(question_id: int, db: AsyncSession = Depends(get_db)) -> SqlQuestionDetail:
    item = await SqlQuestionRepository(db).get(question_id)
    if item is None or item.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="题目不存在")
    return SqlQuestionDetail.model_validate(item)
