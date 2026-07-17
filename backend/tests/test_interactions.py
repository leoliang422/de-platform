"""M8 互动：点赞/收藏切换、浏览量、评论/回复+通知、收藏列表。"""

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


async def _make_knowledge(db: AsyncSession, title: str = "测试知识") -> int:
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


async def test_like_toggle_and_stats(client: AsyncClient, db: AsyncSession) -> None:
    kid = await _make_knowledge(db)
    token = await _login(client, "liker@test.io")

    r = await client.post(f"/interactions/knowledge/{kid}/like", headers=_auth(token))
    assert r.status_code == 200
    assert r.json()["likes"] == 1
    assert r.json()["liked"] is True

    # 再次点击取消点赞
    r = await client.post(f"/interactions/knowledge/{kid}/like", headers=_auth(token))
    assert r.json()["likes"] == 0
    assert r.json()["liked"] is False


async def test_view_increment(client: AsyncClient, db: AsyncSession) -> None:
    kid = await _make_knowledge(db)
    await client.post(f"/interactions/knowledge/{kid}/view")
    r = await client.post(f"/interactions/knowledge/{kid}/view")
    assert r.json()["views"] == 2


async def test_favorite_and_list(client: AsyncClient, db: AsyncSession) -> None:
    kid = await _make_knowledge(db, "收藏知识")
    token = await _login(client, "faver@test.io")

    await client.post(f"/interactions/knowledge/{kid}/favorite", headers=_auth(token))
    favs = await client.get("/interactions/me/favorites", headers=_auth(token))
    assert favs.status_code == 200
    body = favs.json()
    assert len(body) == 1
    assert body[0]["title"] == "收藏知识"
    assert body[0]["content_type"] == "knowledge"


async def test_comment_reply_notifies_parent_author(client: AsyncClient, db: AsyncSession) -> None:
    kid = await _make_knowledge(db)
    alice = await _login(client, "alice@test.io")
    bob = await _login(client, "bob@test.io")

    top = await client.post(
        f"/interactions/knowledge/{kid}/comments",
        headers=_auth(alice),
        json={"body": "顶层评论"},
    )
    assert top.status_code == 201
    top_id = top.json()["id"]

    reply = await client.post(
        f"/interactions/knowledge/{kid}/comments",
        headers=_auth(bob),
        json={"body": "回复你", "parent_id": top_id},
    )
    assert reply.status_code == 201
    assert reply.json()["parent_id"] == top_id

    # alice 收到评论通知
    notifs = await client.get("/notifications", headers=_auth(alice))
    assert any(n["type"] == "comment" for n in notifs.json())

    # 列表包含两条
    listing = await client.get(f"/interactions/knowledge/{kid}/comments")
    assert len(listing.json()) == 2

    stats = await client.get(f"/interactions/knowledge/{kid}")
    assert stats.json()["comments"] == 2


async def test_delete_comment_permission(client: AsyncClient, db: AsyncSession) -> None:
    kid = await _make_knowledge(db)
    alice = await _login(client, "alice2@test.io")
    intruder = await _login(client, "intruder3@test.io")

    c = await client.post(
        f"/interactions/knowledge/{kid}/comments",
        headers=_auth(alice),
        json={"body": "我的评论"},
    )
    cid = c.json()["id"]

    forbidden = await client.delete(f"/interactions/comments/{cid}", headers=_auth(intruder))
    assert forbidden.status_code == 403

    ok = await client.delete(f"/interactions/comments/{cid}", headers=_auth(alice))
    assert ok.status_code == 204


async def test_invalid_content_type(client: AsyncClient) -> None:
    r = await client.get("/interactions/bogus/1")
    assert r.status_code == 404
