"""积分充值（人工确认）业务逻辑。

流程：用户选套餐 → 建 pending 充值订单 → 用户扫管理员收款码付款 →
管理员在后台核对到账后「确认」→ 幂等发放积分（PointsService.grant）。
不涉及真实支付网关，故无需资质；缺点是每笔需人工核对。
"""

from __future__ import annotations

from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.payment.models import Order
from app.modules.payment.repository import PaymentRepository
from app.modules.points.service import PointsService
from app.modules.settings.service import get_setting

# 收款码在 site_settings 中的 key（管理员后台上传后即时生效，优先于环境变量）。
RECHARGE_QR_KEY = "recharge_qr_url"


def list_packages() -> list[dict[str, int]]:
    """返回配置中的充值套餐，附带序号 id。"""
    packages = get_settings().recharge_package_list
    return [{"id": i, **pkg} for i, pkg in enumerate(packages)]


async def get_qr_url(db: AsyncSession) -> str:
    """收款码地址：优先取管理员在后台上传的值，回退到环境变量 RECHARGE_QR_URL。"""
    saved = await get_setting(db, RECHARGE_QR_KEY)
    return saved or get_settings().recharge_qr_url


class RechargeService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = PaymentRepository(db)

    async def create(self, user_id: int, package_id: int) -> Order:
        packages = list_packages()
        pkg = next((p for p in packages if p["id"] == package_id), None)
        if pkg is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="充值套餐不存在")
        # 金额由服务端按套餐决定，前端只传 package_id，避免篡改金额。
        order = Order(
            user_id=user_id,
            item_type="recharge",
            item_id=package_id,
            amount_cash=Decimal(str(pkg["amount"])),
            points_delta=pkg["points"],
            status="pending",
            provider="manual",
        )
        self.repo.add(order)
        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def list_mine(self, user_id: int) -> list[Order]:
        return await self.repo.list_recharge_orders_by_user(user_id)

    async def list_for_admin(self, status_value: str | None) -> list[Order]:
        return await self.repo.list_recharge_orders_by_status(status_value)

    async def confirm(self, order_id: int) -> Order:
        order = await self.repo.get_order(order_id)
        if order is None or order.item_type != "recharge":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="充值订单不存在")
        if order.status == "paid":
            return order  # 幂等：已确认直接返回
        if order.status == "failed":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="该订单已被驳回，无法确认"
            )
        order.status = "paid"
        # 幂等发放：同一 (recharge, order.id) 只会加一次积分。
        await PointsService(self.db).grant(
            user_id=order.user_id,
            delta=order.points_delta or 0,
            reason=f"充值到账 ¥{order.amount_cash}",
            ref_type="recharge",
            ref_id=order.id,
        )
        await self.db.commit()
        await self.db.refresh(order)
        return order

    async def reject(self, order_id: int) -> Order:
        order = await self.repo.get_order(order_id)
        if order is None or order.item_type != "recharge":
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="充值订单不存在")
        if order.status == "paid":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="该订单已到账，无法驳回"
            )
        order.status = "failed"
        await self.db.commit()
        await self.db.refresh(order)
        return order
