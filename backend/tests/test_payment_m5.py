"""M5 支付：工厂回退 + 异步回调（webhook）结算路径。

现金同步结算（mock 默认）的行为仍由 tests/test_payment.py 覆盖，此处补充
真实通道未配齐时的安全回退，以及 webhook 幂等结算逻辑。
"""

from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.payment.models import Entitlement, Order
from app.modules.payment.provider import (
    AlipayProvider,
    MockProvider,
    WechatPayProvider,
    get_payment_provider,
)
from app.modules.projects.models import Project
from app.modules.users.models import User


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post(
        "/auth/register",
        json={"email": email, "password": "secret123", "nickname": email.split("@")[0]},
    )
    resp = await client.post("/auth/login", json={"email": email, "password": "secret123"})
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _make_paid_project(db: AsyncSession) -> int:
    project = Project(
        title="付费项目",
        description_md="desc",
        implementation_md="secret impl",
        access_type="paid",
        price_cash=Decimal("199.00"),
        price_points=100,
        status="published",
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)
    return project.id


async def _user_id(db: AsyncSession, email: str) -> int:
    result = await db.execute(select(User).where(User.email == email))
    return result.scalar_one().id


def test_default_provider_is_mock() -> None:
    assert get_payment_provider().name == "mock"
    assert isinstance(get_payment_provider(), MockProvider)


def test_real_providers_fall_back_when_unconfigured(monkeypatch) -> None:
    # 选了真实通道但凭证为空时，工厂必须回退 mock，避免影响现有功能。
    assert WechatPayProvider.is_configured() is False
    assert AlipayProvider.is_configured() is False

    get_settings.cache_clear()
    monkeypatch.setenv("PAYMENT_PROVIDER", "wechat")
    try:
        assert get_payment_provider().name == "mock"
        monkeypatch.setenv("PAYMENT_PROVIDER", "alipay")
        get_settings.cache_clear()
        assert get_payment_provider().name == "mock"
    finally:
        get_settings.cache_clear()


async def test_webhook_settles_pending_order(client: AsyncClient, db: AsyncSession) -> None:
    pid = await _make_paid_project(db)
    token = await _register_and_login(client, "wh_ok@test.io")
    uid = await _user_id(db, "wh_ok@test.io")

    order = Order(
        user_id=uid,
        item_type="project",
        item_id=pid,
        amount_cash=Decimal("199.00"),
        status="pending",
        provider="mock",
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    # 付费内容在结算前应保持锁定。
    locked = await client.get(f"/projects/{pid}", headers=_auth(token))
    assert locked.json()["locked"] is True

    resp = await client.post(
        "/payment/webhook/mock",
        json={"order_id": order.id, "success": True},
    )
    assert resp.status_code == 200, resp.text

    await db.refresh(order)
    assert order.status == "paid"

    unlocked = await client.get(f"/projects/{pid}", headers=_auth(token))
    assert unlocked.json()["locked"] is False
    assert unlocked.json()["implementation_md"] == "secret impl"


async def test_webhook_is_idempotent(client: AsyncClient, db: AsyncSession) -> None:
    pid = await _make_paid_project(db)
    await _register_and_login(client, "wh_idem@test.io")
    uid = await _user_id(db, "wh_idem@test.io")

    order = Order(
        user_id=uid,
        item_type="project",
        item_id=pid,
        amount_cash=Decimal("199.00"),
        status="pending",
        provider="mock",
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    payload = {"order_id": order.id, "success": True}
    first = await client.post("/payment/webhook/mock", json=payload)
    second = await client.post("/payment/webhook/mock", json=payload)
    assert first.status_code == 200
    assert second.status_code == 200

    result = await db.execute(
        select(Entitlement).where(
            Entitlement.user_id == uid,
            Entitlement.content_type == "project",
            Entitlement.content_id == pid,
        )
    )
    assert len(result.scalars().all()) == 1  # 未因重复回调多发权益


async def test_webhook_unknown_provider_404(client: AsyncClient) -> None:
    resp = await client.post("/payment/webhook/stripe", json={"order_id": 1, "success": True})
    assert resp.status_code == 404


async def test_webhook_failed_marks_order_failed(client: AsyncClient, db: AsyncSession) -> None:
    pid = await _make_paid_project(db)
    await _register_and_login(client, "wh_fail@test.io")
    uid = await _user_id(db, "wh_fail@test.io")

    order = Order(
        user_id=uid,
        item_type="project",
        item_id=pid,
        amount_cash=Decimal("199.00"),
        status="pending",
        provider="mock",
    )
    db.add(order)
    await db.commit()
    await db.refresh(order)

    resp = await client.post(
        "/payment/webhook/mock",
        json={"order_id": order.id, "success": False},
    )
    assert resp.status_code == 200
    await db.refresh(order)
    assert order.status == "failed"
