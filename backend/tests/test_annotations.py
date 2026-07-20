"""划词批注：创建/列举（全员可见、免审核）、锚定信息、回复通知、删除权限。"""

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge import service as knowledge_service


async def _login(client: AsyncClient, email: str) -> str:
    await client.post(
        "/auth/register",
        json={"email": email, "password": "secret123", "nickname": email.split("@")[0]},
    )
    resp = await client.post("/auth/login", json={"email": email, "password": "secret123"})
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def _make_knowledge(db: AsyncSession, title: str = "批注知识") -> int:
    item = await knowledge_service.create_published(
        db,
        title=title,
        content_md="Hive 是数据仓库工具，SQL 转 MapReduce。",
        category_id=None,
        is_paid=False,
        price_cash=None,
        price_points=None,
        author_id=None,
    )
    await db.commit()
    return item.id


async def test_annotation_create_and_list_public(client: AsyncClient, db: AsyncSession) -> None:
    kid = await _make_knowledge(db)
    token = await _login(client, "anno1@test.io")

    r = await client.post(
        f"/interactions/knowledge/{kid}/annotations",
        headers=_auth(token),
        json={"body": "这里其实也可以走 Tez", "quote": "SQL 转 MapReduce", "anchor_offset": 12},
    )
    assert r.status_code == 201, r.text
    body = r.json()
    assert body["quote"] == "SQL 转 MapReduce"
    assert body["anchor_offset"] == 12

    # 无需登录即可查看（全员可见）
    listing = await client.get(f"/interactions/knowledge/{kid}/annotations")
    assert listing.status_code == 200
    assert len(listing.json()) == 1
    assert listing.json()[0]["body"] == "这里其实也可以走 Tez"


async def test_annotation_reply_notifies_and_clears_anchor(
    client: AsyncClient, db: AsyncSession
) -> None:
    kid = await _make_knowledge(db)
    alice = await _login(client, "annoA@test.io")
    bob = await _login(client, "annoB@test.io")

    top = await client.post(
        f"/interactions/knowledge/{kid}/annotations",
        headers=_auth(alice),
        json={"body": "顶层批注", "quote": "Hive", "anchor_offset": 0},
    )
    top_id = top.json()["id"]

    reply = await client.post(
        f"/interactions/knowledge/{kid}/annotations",
        headers=_auth(bob),
        json={"body": "回复批注", "parent_id": top_id, "quote": "忽略", "anchor_offset": 99},
    )
    assert reply.status_code == 201
    assert reply.json()["parent_id"] == top_id
    # 回复不携带锚点
    assert reply.json()["quote"] == ""
    assert reply.json()["anchor_offset"] == 0

    notifs = await client.get("/notifications", headers=_auth(alice))
    assert any(n["type"] == "comment" for n in notifs.json())


async def test_annotation_reply_requires_valid_parent(
    client: AsyncClient, db: AsyncSession
) -> None:
    kid = await _make_knowledge(db)
    token = await _login(client, "annoP@test.io")
    r = await client.post(
        f"/interactions/knowledge/{kid}/annotations",
        headers=_auth(token),
        json={"body": "回复不存在的批注", "parent_id": 99999},
    )
    assert r.status_code == 400


async def test_delete_annotation_permission(client: AsyncClient, db: AsyncSession) -> None:
    kid = await _make_knowledge(db)
    owner = await _login(client, "annoOwner@test.io")
    intruder = await _login(client, "annoIntruder@test.io")

    a = await client.post(
        f"/interactions/knowledge/{kid}/annotations",
        headers=_auth(owner),
        json={"body": "我的批注"},
    )
    aid = a.json()["id"]

    forbidden = await client.delete(f"/interactions/annotations/{aid}", headers=_auth(intruder))
    assert forbidden.status_code == 403

    ok = await client.delete(f"/interactions/annotations/{aid}", headers=_auth(owner))
    assert ok.status_code == 204
