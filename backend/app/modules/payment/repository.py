from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.payment.models import Entitlement, Order


class PaymentRepository:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db

    async def get_entitlement(
        self, user_id: int, content_type: str, content_id: int
    ) -> Entitlement | None:
        stmt = select(Entitlement).where(
            Entitlement.user_id == user_id,
            Entitlement.content_type == content_type,
            Entitlement.content_id == content_id,
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()

    async def get_order(self, order_id: int) -> Order | None:
        return await self.db.get(Order, order_id)

    async def list_entitlements(self, user_id: int) -> list[Entitlement]:
        stmt = (
            select(Entitlement)
            .where(Entitlement.user_id == user_id)
            .order_by(Entitlement.id.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())

    def add(self, obj: Entitlement | Order) -> None:
        self.db.add(obj)
