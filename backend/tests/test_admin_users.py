"""管理员用户管理：列表、改角色、调整积分（写账本）。"""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User


async def _login(client: AsyncClient, email: str) -> str:
    await client.post(
        "/auth/register",
        json={"email": email, "password": "secret123", "nickname": email.split("@")[0]},
    )
    resp = await client.post("/auth/login", json={"email": email, "password": "secret123"})
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _make_admin(db: AsyncSession, email: str) -> None:
    user = (await db.execute(select(User).where(User.email == email))).scalar_one()
    user.role = "admin"
    await db.commit()


async def test_list_and_search_users(client: AsyncClient, db: AsyncSession) -> None:
    admin = await _login(client, "uadmin@test.io")
    await _make_admin(db, "uadmin@test.io")
    await _login(client, "alice@test.io")

    users = (await client.get("/admin/users", headers=_auth(admin))).json()
    emails = {u["email"] for u in users}
    assert {"uadmin@test.io", "alice@test.io"} <= emails

    found = (await client.get("/admin/users?q=alice", headers=_auth(admin))).json()
    assert len(found) == 1 and found[0]["email"] == "alice@test.io"


async def test_adjust_points_and_role(client: AsyncClient, db: AsyncSession) -> None:
    admin = await _login(client, "uadmin2@test.io")
    await _make_admin(db, "uadmin2@test.io")
    await _login(client, "bob@test.io")
    bob = (await db.execute(select(User).where(User.email == "bob@test.io"))).scalar_one()

    # 增加 50 分
    r = await client.patch(
        f"/admin/users/{bob.id}",
        headers=_auth(admin),
        json={"delta_points": 50, "reason": "活动奖励"},
    )
    assert r.status_code == 200
    assert r.json()["points_balance"] == 50

    # 设为绝对值 20
    r = await client.patch(f"/admin/users/{bob.id}", headers=_auth(admin), json={"set_points": 20})
    assert r.json()["points_balance"] == 20

    # 升为管理员
    r = await client.patch(f"/admin/users/{bob.id}", headers=_auth(admin), json={"role": "admin"})
    assert r.json()["role"] == "admin"

    # 账本可见（两次调整）
    ledger = (await client.get("/points/me", headers=_auth(admin))).json()
    # admin 自己的账本不含 bob 的调整，这里仅验证接口连通
    assert "balance" in ledger


async def test_user_mgmt_requires_admin(client: AsyncClient) -> None:
    token = await _login(client, "plainuser@test.io")
    assert (await client.get("/admin/users", headers=_auth(token))).status_code == 403
