"""系统配置 · 积分规则：后台可编辑，且运行时（免费额度/解锁积分/充值套餐）即时生效。"""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import Category
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


async def test_points_config_edit_and_effect(client: AsyncClient, db: AsyncSession) -> None:
    admin = await _login(client, "pcadmin@test.io")
    await _make_admin(db, "pcadmin@test.io")

    # 默认值读取
    cfg = (await client.get("/admin/points-config", headers=_auth(admin))).json()
    assert cfg["free_module_quota"] == 10
    assert cfg["reward_knowledge"] == 10
    assert cfg["reward_project"] == 100
    assert len(cfg["packages"]) >= 1

    # 编辑：改免费额度 / 解锁积分 / 投稿奖励 / 充值套餐
    resp = await client.put(
        "/admin/points-config",
        headers=_auth(admin),
        json={
            "free_module_quota": 3,
            "sql_module_unlock_points": 88,
            "interview_module_unlock_points": 99,
            "reward_knowledge": 15,
            "reward_sql": 25,
            "reward_interview": 35,
            "reward_project": 200,
            "packages": [{"amount": 5, "points": 50}, {"amount": 20, "points": 240}],
        },
    )
    assert resp.status_code == 200, resp.text
    saved = resp.json()
    assert saved["free_module_quota"] == 3
    assert saved["sql_module_unlock_points"] == 88
    assert saved["reward_knowledge"] == 15
    assert saved["reward_project"] == 200
    assert [p["amount"] for p in saved["packages"]] == [5, 20]

    # 运行时即时生效：SQL 模块访问概览应反映新值
    user = await _login(client, "pcuser@test.io")
    summary = (await client.get("/access/sql", headers=_auth(user))).json()
    assert summary["free_limit"] == 3
    assert summary["unlock_points"] == 88

    # 充值套餐配置端点也应反映新值
    packages = (await client.get("/payment/recharge/config")).json()["packages"]
    assert [p["amount"] for p in packages] == [5, 20]

    # 非管理员不可编辑
    forbidden = await client.put(
        "/admin/points-config",
        headers=_auth(user),
        json={
            "free_module_quota": 1,
            "sql_module_unlock_points": 1,
            "interview_module_unlock_points": 1,
            "reward_knowledge": 1,
            "reward_sql": 1,
            "reward_interview": 1,
            "reward_project": 1,
            "packages": [],
        },
    )
    assert forbidden.status_code == 403


async def test_reward_points_config_applies_on_approval(
    client: AsyncClient, db: AsyncSession
) -> None:
    admin = await _login(client, "radmin@test.io")
    await _make_admin(db, "radmin@test.io")

    # 把八股奖励改为 15
    await client.put(
        "/admin/points-config",
        headers=_auth(admin),
        json={
            "free_module_quota": 10,
            "sql_module_unlock_points": 30,
            "interview_module_unlock_points": 30,
            "reward_knowledge": 15,
            "reward_sql": 10,
            "reward_interview": 20,
            "reward_project": 100,
            "packages": [{"amount": 10, "points": 100}],
        },
    )

    author = await _login(client, "rauthor@test.io")
    cat = Category(section="knowledge", name="Hive", slug="hive-r", order=0)
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    sid = (
        await client.post(
            "/submissions",
            headers=_auth(author),
            json={
                "target_type": "knowledge",
                "title": "奖励测试",
                "raw_content": "内容",
                "category_id": cat.id,
            },
        )
    ).json()["id"]
    approve = await client.post(f"/admin/submissions/{sid}/approve", headers=_auth(admin))
    assert approve.status_code == 200, approve.text

    # 作者应到账 15 积分（而非默认 10）
    overview = (await client.get("/points/me", headers=_auth(author))).json()
    assert overview["balance"] == 15
    assert overview["ledger"][0]["delta"] == 15
