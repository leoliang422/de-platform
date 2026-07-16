from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.points.repository import PointsRepository
from app.modules.points.schemas import LedgerEntryOut, PointsOverview
from app.modules.users.models import User

router = APIRouter(prefix="/points", tags=["points"])


@router.get("/me", response_model=PointsOverview)
async def my_points(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> PointsOverview:
    entries = await PointsRepository(db).list_by_user(current_user.id)
    return PointsOverview(
        balance=current_user.points_balance,
        ledger=[LedgerEntryOut.model_validate(e) for e in entries],
    )
