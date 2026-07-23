from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.notifications.schemas import NotificationOut, UnreadCountOut
from app.modules.notifications.service import NotificationService
from app.modules.users.models import User

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
async def list_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[NotificationOut]:
    items = await NotificationService(db).list(current_user.id)
    return [NotificationOut.model_validate(n) for n in items]


@router.get("/unread_count", response_model=UnreadCountOut)
async def unread_count(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnreadCountOut:
    count = await NotificationService(db).unread_count(current_user.id)
    return UnreadCountOut(unread=count)


@router.post("/{notification_id}/read", response_model=NotificationOut)
async def mark_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> NotificationOut:
    n = await NotificationService(db).mark_read(current_user.id, notification_id)
    return NotificationOut.model_validate(n)


@router.post("/read-all", response_model=UnreadCountOut)
async def mark_all_read(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnreadCountOut:
    await NotificationService(db).mark_all_read(current_user.id)
    return UnreadCountOut(unread=0)


@router.delete("", status_code=status.HTTP_204_NO_CONTENT)
async def clear_notifications(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await NotificationService(db).clear(current_user.id)


@router.delete("/{notification_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_notification(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> None:
    await NotificationService(db).delete(current_user.id, notification_id)
