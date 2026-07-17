"""知识树：提议节点 → 审核上线 → 树读取；管理 CRUD。"""

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


async def _make_category(db: AsyncSession, name: str = "Hive") -> int:
    cat = Category(section="knowledge", name=name, slug=name.lower(), order=0)
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    return cat.id


async def test_propose_review_and_tree(client: AsyncClient, db: AsyncSession) -> None:
    cat_id = await _make_category(db)
    admin = await _login(client, "kt-admin@test.io")
    await _make_admin(db, "kt-admin@test.io")
    user = await _login(client, "kt-user@test.io")

    # 管理员建根节点
    root = await client.post(
        "/admin/knowledge-tree/nodes",
        headers=_auth(admin),
        json={"category_id": cat_id, "title": "Hive 基础"},
    )
    assert root.status_code == 201, root.text
    root_id = root.json()["id"]

    # 公开树可见根节点
    tree = (await client.get(f"/knowledge-tree?category_id={cat_id}")).json()
    assert len(tree) == 1
    assert tree[0]["title"] == "Hive 基础"

    # 用户在根下提议子节点 → pending，公开树暂不可见
    prop = await client.post(
        "/knowledge-tree/nodes",
        headers=_auth(user),
        json={"category_id": cat_id, "parent_id": root_id, "title": "分区表"},
    )
    assert prop.status_code == 201, prop.text
    node_id = prop.json()["id"]
    assert prop.json()["status"] == "pending"

    tree = (await client.get(f"/knowledge-tree?category_id={cat_id}")).json()
    assert tree[0]["children"] == []

    # 管理员看到待审
    pending = (await client.get("/admin/knowledge-tree/pending", headers=_auth(admin))).json()
    assert any(p["id"] == node_id and p["parent_title"] == "Hive 基础" for p in pending)

    # 审核通过 → 公开树出现该子节点
    ok = await client.post(f"/admin/knowledge-tree/{node_id}/approve", headers=_auth(admin))
    assert ok.status_code == 200
    tree = (await client.get(f"/knowledge-tree?category_id={cat_id}")).json()
    assert tree[0]["children"][0]["title"] == "分区表"

    # 提议者收到通知
    notifs = (await client.get("/notifications", headers=_auth(user))).json()
    assert any(n["type"] == "knowledge_node_approved" for n in notifs)


async def test_reject_removes_node(client: AsyncClient, db: AsyncSession) -> None:
    cat_id = await _make_category(db, "Spark")
    admin = await _login(client, "kt-admin2@test.io")
    await _make_admin(db, "kt-admin2@test.io")
    user = await _login(client, "kt-user2@test.io")

    prop = await client.post(
        "/knowledge-tree/nodes",
        headers=_auth(user),
        json={"category_id": cat_id, "title": "错误节点"},
    )
    node_id = prop.json()["id"]

    r = await client.post(f"/admin/knowledge-tree/{node_id}/reject", headers=_auth(admin))
    assert r.status_code == 204
    pending = (await client.get("/admin/knowledge-tree/pending", headers=_auth(admin))).json()
    assert all(p["id"] != node_id for p in pending)


async def test_propose_requires_auth(client: AsyncClient, db: AsyncSession) -> None:
    cat_id = await _make_category(db, "Flink")
    r = await client.post(
        "/knowledge-tree/nodes",
        json={"category_id": cat_id, "title": "x"},
    )
    assert r.status_code == 401


async def test_admin_endpoints_require_admin(client: AsyncClient, db: AsyncSession) -> None:
    cat_id = await _make_category(db, "Kafka")
    user = await _login(client, "kt-plain@test.io")
    r = await client.get("/admin/knowledge-tree/pending", headers=_auth(user))
    assert r.status_code == 403
    r = await client.post(
        "/admin/knowledge-tree/nodes",
        headers=_auth(user),
        json={"category_id": cat_id, "title": "x"},
    )
    assert r.status_code == 403
