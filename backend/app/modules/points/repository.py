from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.points.models import PointLedger


class PointsRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_by_ref(self, ref_type: str, ref_id: int) -> PointLedger | None:
        stmt = select(PointLedger).where(
            PointLedger.ref_type == ref_type, PointLedger.ref_id == ref_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def list_by_user(self, user_id: int) -> list[PointLedger]:
        stmt = (
            select(PointLedger)
            .where(PointLedger.user_id == user_id)
            .order_by(PointLedger.id.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    def add(self, entry: PointLedger) -> None:
        self.db.add(entry)

    async def get(self, entry_id: int) -> PointLedger | None:
        return await self.db.get(PointLedger, entry_id)
