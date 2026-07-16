from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user_optional
from app.modules.knowledge.repository import KnowledgeRepository
from app.modules.knowledge.schemas import KnowledgeDetail, KnowledgeListItem
from app.modules.payment.service import user_can_access
from app.modules.users.models import User

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("", response_model=list[KnowledgeListItem])
async def list_knowledge(
    category_id: int | None = Query(default=None),
    db: AsyncSession = Depends(get_db),
) -> list[KnowledgeListItem]:
    items = await KnowledgeRepository(db).list_published(category_id)
    return [KnowledgeListItem.model_validate(i) for i in items]


@router.get("/{item_id}", response_model=KnowledgeDetail)
async def get_knowledge(
    item_id: int,
    db: AsyncSession = Depends(get_db),
    user: User | None = Depends(get_current_user_optional),
) -> KnowledgeDetail:
    item = await KnowledgeRepository(db).get(item_id)
    if item is None or item.status != "published":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="内容不存在")

    locked = item.is_paid and not await user_can_access(
        db, user, "knowledge", item.id, item.author_id
    )
    detail = KnowledgeDetail(
        id=item.id,
        category_id=item.category_id,
        title=item.title,
        is_paid=item.is_paid,
        price_cash=item.price_cash,
        price_points=item.price_points,
        locked=locked,
        content_md=None if locked else item.content_md,
    )
    return detail
