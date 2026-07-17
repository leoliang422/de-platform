from __future__ import annotations

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import Notification


class NotificationRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def list_by_user(self, user_id: int, limit: int = 50) -> list[Notification]:
        stmt = (
            select(Notification)
            .where(Notification.user_id == user_id)
            .order_by(Notification.id.desc())
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    async def count_unread(self, user_id: int) -> int:
        stmt = select(func.count()).where(
            Notification.user_id == user_id, Notification.read_at.is_(None)
        )
        result = await self.db.execute(stmt)
        return int(result.scalar_one())

    async def get(self, notification_id: int) -> Notification | None:
        return await self.db.get(Notification, notification_id)
