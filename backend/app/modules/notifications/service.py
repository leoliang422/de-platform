from __future__ import annotations

import datetime as dt

from fastapi import HTTPException, status
from sqlalchemy import delete, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.notifications.models import Notification
from app.modules.notifications.repository import NotificationRepository


class NotificationService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = NotificationRepository(db)

    async def notify(
        self,
        *,
        user_id: int,
        type: str,
        title: str,
        body: str | None = None,
        link: str | None = None,
    ) -> Notification:
        """创建一条站内通知。

        供其他模块在自身事务内调用：这里只 ``add`` + ``flush``，由调用方 commit。
        """
        notification = Notification(user_id=user_id, type=type, title=title, body=body, link=link)
        self.db.add(notification)
        await self.db.flush()
        return notification

    async def list(self, user_id: int) -> list[Notification]:
        return await self.repo.list_by_user(user_id)

    async def unread_count(self, user_id: int) -> int:
        return await self.repo.count_unread(user_id)

    async def mark_read(self, user_id: int, notification_id: int) -> Notification:
        notification = await self.repo.get(notification_id)
        if notification is None or notification.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="通知不存在")
        if notification.read_at is None:
            notification.read_at = dt.datetime.now(dt.UTC)
            await self.db.commit()
            await self.db.refresh(notification)
        return notification

    async def mark_all_read(self, user_id: int) -> None:
        stmt = (
            update(Notification)
            .where(Notification.user_id == user_id, Notification.read_at.is_(None))
            .values(read_at=dt.datetime.now(dt.UTC))
        )
        await self.db.execute(stmt)
        await self.db.commit()

    async def delete(self, user_id: int, notification_id: int) -> None:
        """永久删除一条通知（仅限本人）。"""
        notification = await self.repo.get(notification_id)
        if notification is None or notification.user_id != user_id:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="通知不存在")
        await self.db.delete(notification)
        await self.db.commit()

    async def clear(self, user_id: int) -> None:
        """清空本人全部通知。"""
        await self.db.execute(delete(Notification).where(Notification.user_id == user_id))
        await self.db.commit()
