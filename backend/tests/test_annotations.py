"""内容备注（annotations）：全员可见、无需审核、支持回复与删除、回复通知作者。"""

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


async def _make_knowledge(db: AsyncSession, title: str = "备注知识") -> int:
    item = await knowledge_service.create_published(
        db,
        title=title,
        content_md="正文",
        category_id=None,
        is_paid=False,
        price_cash=None,
        price_points=None,
        author_id=None,
    )
    await db.commit()
    return item.id


async def test_annotation_create_list_public(client: AsyncClient, db: AsyncSession) -> None:
    kid = await _make_knowledge(db)
    token = await _login(client, "note1@test.io")

    r = await client.post(
        f"/interactions/knowledge/{kid}/annotations",
        headers=_auth(token),
        json={"body": "这里补充一点"},
    )
    assert r.status_code == 201, r.text
    assert r.json()["body"] == "这里补充一点"
    assert r.json()["author_nickname"]

    # 未登录也能查看（全员可见、无需审核）
    listing = await client.get(f"/interactions/knowledge/{kid}/annotations")
    assert listing.status_code == 200
    assert len(listing.json()) == 1


async def test_annotation_reply_notifies_parent_author(
    client: AsyncClient, db: AsyncSession
) -> None:
    kid = await _make_knowledge(db)
    alice = await _login(client, "note_alice@test.io")
    bob = await _login(client, "note_bob@test.io")

    top = await client.post(
        f"/interactions/knowledge/{kid}/annotations",
        headers=_auth(alice),
        json={"body": "顶层备注"},
    )
    top_id = top.json()["id"]

    reply = await client.post(
        f"/interactions/knowledge/{kid}/annotations",
        headers=_auth(bob),
        json={"body": "回复备注", "parent_id": top_id},
    )
    assert reply.status_code == 201
    assert reply.json()["parent_id"] == top_id

    notifs = await client.get("/notifications", headers=_auth(alice))
    assert any(n["type"] == "comment" for n in notifs.json())

    listing = await client.get(f"/interactions/knowledge/{kid}/annotations")
    assert len(listing.json()) == 2


async def test_annotation_reply_requires_valid_parent(
    client: AsyncClient, db: AsyncSession
) -> None:
    kid = await _make_knowledge(db)
    token = await _login(client, "note_bad@test.io")
    r = await client.post(
        f"/interactions/knowledge/{kid}/annotations",
        headers=_auth(token),
        json={"body": "回复不存在的备注", "parent_id": 99999},
    )
    assert r.status_code == 400


async def test_delete_annotation_permission(client: AsyncClient, db: AsyncSession) -> None:
    kid = await _make_knowledge(db)
    owner = await _login(client, "note_owner@test.io")
    intruder = await _login(client, "note_intruder@test.io")

    a = await client.post(
        f"/interactions/knowledge/{kid}/annotations",
        headers=_auth(owner),
        json={"body": "我的备注"},
    )
    aid = a.json()["id"]

    forbidden = await client.delete(
        f"/interactions/annotations/{aid}", headers=_auth(intruder)
    )
    assert forbidden.status_code == 403

    ok = await client.delete(f"/interactions/annotations/{aid}", headers=_auth(owner))
    assert ok.status_code == 204

    listing = await client.get(f"/interactions/knowledge/{kid}/annotations")
    assert listing.json() == []
