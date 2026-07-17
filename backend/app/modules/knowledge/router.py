from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user_optional
from app.modules.interactions.service import bulk_content_stats
from app.modules.knowledge.repository import KnowledgeRepository
from app.modules.knowledge.schemas import (
    KnowledgeDetail,
    KnowledgeListItem,
    KnowledgeListPage,
)
from app.modules.payment.service import user_can_access
from app.modules.users.models import User

router = APIRouter(prefix="/knowledge", tags=["knowledge"])


@router.get("", response_model=KnowledgeListPage)
async def list_knowledge(
    category_id: int | None = Query(default=None),
    sort: Literal["hot", "new"] = Query(default="hot"),
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
) -> KnowledgeListPage:
    """八股列表：按热度（浏览+点赞+收藏加权）或最新排序，分页返回并附带互动角标。"""
    items = await KnowledgeRepository(db).list_published(category_id)
    stats = await bulk_content_stats(db, "knowledge", [i.id for i in items])

    rows: list[KnowledgeListItem] = []
    for i in items:
        s = stats[i.id]
        rows.append(
            KnowledgeListItem(
                id=i.id,
                category_id=i.category_id,
                title=i.title,
                is_paid=i.is_paid,
                price_cash=i.price_cash,
                price_points=i.price_points,
                views=s.views,
                likes=s.likes,
                favorites=s.favorites,
                comments=s.comments,
                hotness=s.hotness,
            )
        )

    if sort == "hot":
        rows.sort(key=lambda r: (r.hotness, r.id), reverse=True)
    else:
        rows.sort(key=lambda r: r.id, reverse=True)

    total = len(rows)
    start = (page - 1) * page_size
    paged = rows[start : start + page_size]
    return KnowledgeListPage(items=paged, total=total, page=page, page_size=page_size)


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
