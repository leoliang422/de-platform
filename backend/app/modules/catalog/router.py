from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.catalog.models import SECTIONS
from app.modules.catalog.repository import CategoryRepository
from app.modules.catalog.schemas import CategoryNode
from app.modules.catalog.service import build_tree

router = APIRouter(prefix="/categories", tags=["catalog"])


@router.get("", response_model=list[CategoryNode])
async def list_categories(
    section: str = Query(..., description="板块：knowledge / sql / interview / project"),
    db: AsyncSession = Depends(get_db),
) -> list[CategoryNode]:
    if section not in SECTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"无效板块，可选：{', '.join(SECTIONS)}",
        )
    categories = await CategoryRepository(db).list_by_section(section)
    return build_tree(categories)
