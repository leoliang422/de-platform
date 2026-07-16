from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.knowledge.repository import KnowledgeRepository
from app.modules.knowledge.schemas import KnowledgeDetail, KnowledgeListItem

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("", response_model=list[KnowledgeListItem])
async def list_knowledge(
    category_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[KnowledgeListItem]:
    items = await KnowledgeRepository(db).list_published(category_id)
    return [KnowledgeListItem.model_validate(i) for i in items]


@router.get("/{item_id}", response_model=KnowledgeDetail)
async def get_knowledge(item_id: int, db: AsyncSession = Depends(get_db)) -> KnowledgeDetail:
    item = await KnowledgeRepository(db).get(item_id)
    if item is None or item.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="内容不存在")
    return KnowledgeDetail.model_validate(item)
