from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge import service as knowledge_service
from app.modules.payment.models import PAYABLE_TYPES, Entitlement, Order
from app.modules.payment.provider import get_payment_provider
from app.modules.payment.repository import PaymentRepository
from app.modules.payment.schemas import UnlockIn
from app.modules.points.service import PointsService
from app.modules.projects import service as project_service
from app.modules.users.models import User


async def user_can_access(
    db: AsyncSession,
    user: User | None,
    content_type: str,
    content_id: int,
    author_id: int | None,
) -> bool:
    """付费内容可见性：管理员 / 作者 / 已解锁用户可见。"""
    if user is None:
        return False
    if user.role == "admin" or (author_id is not None and author_id == user.id):
        return True
    return await PaymentService(db).has_entitlement(user.id, content_type, content_id)


class _Pricing:
    def __init__(self, payable: bool, price_cash: Decimal | None, price_points: int | None) -> None:
        self.payable = payable
        self.price_cash = price_cash
        self.price_points = price_points


class PaymentService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = PaymentRepository(db)
        self.provider = get_payment_provider()

    async def has_entitlement(self, user_id: int, content_type: str, content_id: int) -> bool:
        return (await self.repo.get_entitlement(user_id, content_type, content_id)) is not None

    async def _resolve_pricing(self, content_type: str, content_id: int) -> _Pricing:
        if content_type == "project":
            project = await project_service.get_published(self.db, content_id)
            if project is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="项目不存在")
            return _Pricing(project.access_type == "paid", project.price_cash, project.price_points)
        if content_type == "knowledge":
            item = await knowledge_service.get_published(self.db, content_id)
            if item is None:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="内容不存在")
            return _Pricing(item.is_paid, item.price_cash, item.price_points)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的内容类型")

    async def unlock(self, user: User, data: UnlockIn) -> tuple[Entitlement, bool]:
        if data.content_type not in PAYABLE_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的内容类型")

        pricing = await self._resolve_pricing(data.content_type, data.content_id)
        if not pricing.payable:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="该内容免费，无需解锁"
            )

        existing = await self.repo.get_entitlement(user.id, data.content_type, data.content_id)
        if existing is not None:
            return existing, True

        if data.method == "cash":
            entitlement = await self._unlock_with_cash(user, data, pricing)
        else:
            entitlement = await self._unlock_with_points(user, data, pricing)

        await self.db.commit()
        await self.db.refresh(entitlement)
        return entitlement, False

    async def _unlock_with_cash(self, user: User, data: UnlockIn, pricing: _Pricing) -> Entitlement:
        if pricing.price_cash is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="该内容未设置现金价"
            )

        order = Order(
            user_id=user.id,
            item_type=data.content_type,
            item_id=data.content_id,
            amount_cash=pricing.price_cash,
            status="pending",
            provider="mock",
        )
        self.repo.add(order)
        await self.db.flush()

        result = await self.provider.charge(pricing.price_cash, order.id)
        order.provider_ref = result.provider_ref
        order.status = "paid" if result.success else "failed"
        if not result.success:
            raise HTTPException(status_code=status.HTTP_402_PAYMENT_REQUIRED, detail="支付失败")

        entitlement = Entitlement(
            user_id=user.id,
            content_type=data.content_type,
            content_id=data.content_id,
            source="purchase",
        )
        self.repo.add(entitlement)
        await self.db.flush()
        return entitlement

    async def _unlock_with_points(
        self, user: User, data: UnlockIn, pricing: _Pricing
    ) -> Entitlement:
        if pricing.price_points is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="该内容未设置积分价"
            )
        if user.points_balance < pricing.price_points:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="积分不足")

        entitlement = Entitlement(
            user_id=user.id,
            content_type=data.content_type,
            content_id=data.content_id,
            source="points",
        )
        self.repo.add(entitlement)
        await self.db.flush()

        await PointsService(self.db).grant(
            user_id=user.id,
            delta=-pricing.price_points,
            reason=f"兑换解锁：{data.content_type}",
            ref_type="unlock",
            ref_id=entitlement.id,
        )
        return entitlement
