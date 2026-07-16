from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.payment.repository import PaymentRepository
from app.modules.payment.schemas import EntitlementOut, UnlockIn, UnlockResult
from app.modules.payment.service import PaymentService
from app.modules.users.models import User

router = APIRouter(prefix="/payment", tags=["payment"])


@router.post("/unlock", response_model=UnlockResult)
async def unlock(
    data: UnlockIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnlockResult:
    entitlement, already = await PaymentService(db).unlock(current_user, data)
    await db.refresh(current_user)
    return UnlockResult(
        entitlement=EntitlementOut.model_validate(entitlement),
        balance=current_user.points_balance,
        already_unlocked=already,
    )


@router.get("/entitlements/me", response_model=list[EntitlementOut])
async def my_entitlements(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EntitlementOut]:
    items = await PaymentRepository(db).list_entitlements(current_user.id)
    return [EntitlementOut.model_validate(e) for e in items]
