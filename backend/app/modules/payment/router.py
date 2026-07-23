from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.modules.payment import recharge as recharge_service
from app.modules.payment.provider import PaymentNotConfigured, get_payment_provider
from app.modules.payment.recharge import RechargeService
from app.modules.payment.repository import PaymentRepository
from app.modules.payment.schemas import (
    EntitlementOut,
    RechargeConfigOut,
    RechargeCreateIn,
    RechargeOrderOut,
    RechargePackage,
    UnlockIn,
    UnlockResult,
)
from app.modules.payment.service import PaymentService
from app.modules.users.models import User

router = APIRouter(prefix="/payment", tags=["payment"])

_WEBHOOK_PROVIDERS = {"mock", "wechat", "alipay"}


@router.post("/unlock", response_model=UnlockResult)
async def unlock(
    data: UnlockIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UnlockResult:
    outcome = await PaymentService(db).unlock(current_user, data)
    await db.refresh(current_user)
    entitlement = (
        EntitlementOut.model_validate(outcome.entitlement)
        if outcome.entitlement is not None
        else None
    )
    return UnlockResult(
        status=outcome.status,
        entitlement=entitlement,
        balance=current_user.points_balance,
        already_unlocked=outcome.status == "already",
        order_id=outcome.order_id,
        pay_url=outcome.pay_url,
        qr_code=outcome.qr_code,
    )


@router.post("/webhook/{provider}")
async def payment_webhook(
    provider: str,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Response:
    """支付网关异步回调入口（无鉴权，靠验签保证来源可信）。

    路径 provider 必须与当前启用的通道一致，避免用错验签逻辑。
    """
    if provider not in _WEBHOOK_PROVIDERS:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="未知支付通道")

    active = get_payment_provider()
    if provider != active.name:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="支付通道未启用或不匹配"
        )

    body = await request.body()
    try:
        callback = active.parse_callback(dict(request.headers), body)
    except PaymentNotConfigured as exc:
        raise HTTPException(status_code=status.HTTP_501_NOT_IMPLEMENTED, detail=str(exc)) from exc
    except (KeyError, ValueError) as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="回调解析失败") from exc

    result = await PaymentService(db).settle_callback(callback)
    ack = active.callback_ack(result == "paid")
    media_type = "application/json" if active.name == "wechat" else "text/plain"
    return Response(content=ack, media_type=media_type)


@router.get("/entitlements/me", response_model=list[EntitlementOut])
async def my_entitlements(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[EntitlementOut]:
    items = await PaymentRepository(db).list_entitlements(current_user.id)
    return [EntitlementOut.model_validate(e) for e in items]


# ---- 积分充值（人工确认）----
@router.get("/recharge/config", response_model=RechargeConfigOut)
async def recharge_config(db: AsyncSession = Depends(get_db)) -> RechargeConfigOut:
    return RechargeConfigOut(
        qr_url=await recharge_service.get_qr_url(db),
        packages=[RechargePackage(**p) for p in recharge_service.list_packages()],
    )


@router.post("/recharge", response_model=RechargeOrderOut, status_code=status.HTTP_201_CREATED)
async def create_recharge(
    data: RechargeCreateIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> RechargeOrderOut:
    order = await RechargeService(db).create(current_user.id, data.package_id)
    return RechargeOrderOut.model_validate(order)


@router.get("/recharge/me", response_model=list[RechargeOrderOut])
async def my_recharge_orders(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> list[RechargeOrderOut]:
    orders = await RechargeService(db).list_mine(current_user.id)
    return [RechargeOrderOut.model_validate(o) for o in orders]
