"""M6.3 找回密码：忘记→重置→登录、令牌一次性/失效、不枚举用户。"""

import datetime as dt

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import PasswordResetToken
from app.modules.users.models import User


async def _register(client: AsyncClient, email: str, password: str = "secret123") -> None:
    await client.post(
        "/auth/register",
        json={"email": email, "password": password, "nickname": email.split("@")[0]},
    )


async def test_forgot_then_reset_then_login(client: AsyncClient) -> None:
    await _register(client, "reset1@test.io", "oldpass123")

    forgot = await client.post("/auth/forgot-password", json={"email": "reset1@test.io"})
    assert forgot.status_code == 200, forgot.text
    token = forgot.json()["reset_token"]  # mock 通道返回，便于自测
    assert token

    reset = await client.post(
        "/auth/reset-password",
        json={"token": token, "new_password": "brandnew123"},
    )
    assert reset.status_code == 204, reset.text

    old = await client.post(
        "/auth/login", json={"email": "reset1@test.io", "password": "oldpass123"}
    )
    assert old.status_code == 401
    new = await client.post(
        "/auth/login", json={"email": "reset1@test.io", "password": "brandnew123"}
    )
    assert new.status_code == 200


async def test_reset_token_single_use(client: AsyncClient) -> None:
    await _register(client, "reset2@test.io")
    forgot = await client.post("/auth/forgot-password", json={"email": "reset2@test.io"})
    token = forgot.json()["reset_token"]

    first = await client.post(
        "/auth/reset-password", json={"token": token, "new_password": "newpass123"}
    )
    assert first.status_code == 204
    second = await client.post(
        "/auth/reset-password", json={"token": token, "new_password": "another123"}
    )
    assert second.status_code == 400  # 已使用


async def test_reset_invalid_token(client: AsyncClient) -> None:
    resp = await client.post(
        "/auth/reset-password", json={"token": "not-a-real-token", "new_password": "whatever123"}
    )
    assert resp.status_code == 400


async def test_forgot_unknown_email_does_not_leak(client: AsyncClient) -> None:
    resp = await client.post("/auth/forgot-password", json={"email": "ghost@test.io"})
    assert resp.status_code == 200
    body = resp.json()
    assert body["sent"] is True
    assert body["reset_token"] is None  # 未注册邮箱不生成 token


async def test_expired_token_rejected(client: AsyncClient, db: AsyncSession) -> None:
    await _register(client, "reset3@test.io")
    forgot = await client.post("/auth/forgot-password", json={"email": "reset3@test.io"})
    token = forgot.json()["reset_token"]

    # 手动把令牌过期时间改到过去
    result = await db.execute(select(User).where(User.email == "reset3@test.io"))
    uid = result.scalar_one().id
    row = (
        await db.execute(select(PasswordResetToken).where(PasswordResetToken.user_id == uid))
    ).scalar_one()
    row.expires_at = dt.datetime.now(dt.UTC) - dt.timedelta(minutes=1)
    await db.commit()

    resp = await client.post(
        "/auth/reset-password", json={"token": token, "new_password": "newpass123"}
    )
    assert resp.status_code == 400
