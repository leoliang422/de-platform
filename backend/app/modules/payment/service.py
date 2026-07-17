from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge import service as knowledge_service
from app.modules.payment.models import PAYABLE_TYPES, Entitlement, Order
from app.modules.payment.provider import CallbackResult, get_payment_provider
from app.modules.payment.repository import PaymentRepository
from app.modules.payment.schemas import UnlockIn
from app.modules.points.service import PointsService
from app.modules.projects import service as project_service
from app.modules.users.models import User


@dataclass
class UnlockOutcome:
    """解锁结果：同步结算返回权益，异步支付返回付款引导。"""

    status: str  # "paid" | "pending" | "already"
    entitlement: Entitlement | None = None
    order_id: int | None = None
    pay_url: str | None = None
    qr_code: str | None = None


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

    async def unlock(self, user: User, data: UnlockIn) -> UnlockOutcome:
        if data.content_type not in PAYABLE_TYPES:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="不支持的内容类型")

        pricing = await self._resolve_pricing(data.content_type, data.content_id)
        if not pricing.payable:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="该内容免费，无需解锁"
            )

        existing = await self.repo.get_entitlement(user.id, data.content_type, data.content_id)
        if existing is not None:
            return UnlockOutcome(status="already", entitlement=existing)

        if data.method == "cash":
            outcome = await self._unlock_with_cash(user, data, pricing)
        else:
            outcome = await self._unlock_with_points(user, data, pricing)

        await self.db.commit()
        if outcome.entitlement is not None:
            await self.db.refresh(outcome.entitlement)
        return outcome

    async def _unlock_with_cash(
        self, user: User, data: UnlockIn, pricing: _Pricing
    ) -> UnlockOutcome:
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
            provider=self.provider.name,
        )
        self.repo.add(order)
        await self.db.flush()

        charge = await self.provider.create_charge(
            amount=pricing.price_cash,
            order_id=order.id,
            subject=f"解锁 {data.content_type} #{data.content_id}",
        )
        order.provider_ref = charge.provider_ref

        if not charge.settled:
            # 异步支付：订单挂起，待 webhook 回调结算，此时尚不发放权益。
            order.status = "pending"
            await self.db.flush()
            return UnlockOutcome(
                status="pending",
                order_id=order.id,
                pay_url=charge.pay_url,
                qr_code=charge.qr_code,
            )

        order.status = "paid"
        entitlement = self._create_entitlement(user.id, data.content_type, data.content_id)
        await self.db.flush()
        return UnlockOutcome(status="paid", entitlement=entitlement, order_id=order.id)

    async def _unlock_with_points(
        self, user: User, data: UnlockIn, pricing: _Pricing
    ) -> UnlockOutcome:
        if pricing.price_points is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="该内容未设置积分价"
            )
        if user.points_balance < pricing.price_points:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="积分不足")

        entitlement = self._create_entitlement(
            user.id, data.content_type, data.content_id, source="points"
        )
        await self.db.flush()

        await PointsService(self.db).grant(
            user_id=user.id,
            delta=-pricing.price_points,
            reason=f"兑换解锁：{data.content_type}",
            ref_type="unlock",
            ref_id=entitlement.id,
        )
        return UnlockOutcome(status="paid", entitlement=entitlement)

    def _create_entitlement(
        self, user_id: int, content_type: str, content_id: int, source: str = "purchase"
    ) -> Entitlement:
        entitlement = Entitlement(
            user_id=user_id,
            content_type=content_type,
            content_id=content_id,
            source=source,
        )
        self.repo.add(entitlement)
        return entitlement

    async def settle_callback(self, callback: CallbackResult) -> str:
        """处理支付网关异步回调（webhook）：幂等地结算订单并发放权益。

        返回订单最终状态字符串（"paid" / "failed" / "ignored"）。
        """
        order = await self.repo.get_order(callback.order_id)
        if order is None:
            return "ignored"
        if callback.provider_ref and order.provider_ref is None:
            order.provider_ref = callback.provider_ref

        if not callback.success:
            if order.status == "pending":
                order.status = "failed"
                await self.db.commit()
            return "failed"

        # 成功回调：幂等——已结算则直接返回，避免重复发权益。
        if order.status == "paid":
            return "paid"

        order.status = "paid"
        existing = await self.repo.get_entitlement(order.user_id, order.item_type, order.item_id)
        if existing is None:
            self._create_entitlement(order.user_id, order.item_type, order.item_id)
        await self.db.commit()
        return "paid"
