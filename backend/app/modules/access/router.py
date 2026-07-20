from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user, get_current_user_optional
from app.modules.access.schemas import ModuleAccessOut, ModuleUnlockResult
from app.modules.access.service import AccessService
from app.modules.users.models import User

router = APIRouter(prefix="/access", tags=["access"])


@router.get("/{module}", response_model=ModuleAccessOut)
async def module_access(
    module: str,
    user: User | None = Depends(get_current_user_optional),
    db: AsyncSession = Depends(get_db),
) -> ModuleAccessOut:
    return await AccessService(db).summary(user, module)


@router.post("/{module}/unlock", response_model=ModuleUnlockResult)
async def unlock_module(
    module: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> ModuleUnlockResult:
    service = AccessService(db)
    outcome = await service.unlock_module(current_user, module)
    await db.refresh(current_user)
    summary = await service.summary(current_user, module)
    return ModuleUnlockResult(
        module=summary.module,
        unlocked=summary.unlocked,
        free_used=summary.free_used,
        free_limit=summary.free_limit,
        unlock_points=summary.unlock_points,
        balance=current_user.points_balance,
        already=outcome.already,
    )
