from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.points.models import PointLedger
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


@router.delete("/ledger", status_code=status.HTTP_204_NO_CONTENT)
async def clear_ledger(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """清空本人积分明细记录（仅清历史流水，不影响当前积分余额）。"""
    await db.execute(delete(PointLedger).where(PointLedger.user_id == current_user.id))
    await db.commit()


@router.delete("/ledger/{entry_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_ledger_entry(
    entry_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    """永久删除一条积分明细（仅清历史流水，不影响当前积分余额）。"""
    entry = await PointsRepository(db).get(entry_id)
    if entry is None or entry.user_id != current_user.id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="记录不存在")
    await db.delete(entry)
    await db.commit()
