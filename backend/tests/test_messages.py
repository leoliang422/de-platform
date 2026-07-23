"""用户 ↔ 管理员 私信。"""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User


async def _token(client: AsyncClient, email: str) -> str:
    await client.post(
        "/auth/register",
        json={"email": email, "password": "secret123", "nickname": email.split("@")[0]},
    )
    resp = await client.post("/auth/login", json={"email": email, "password": "secret123"})
    return resp.json()["access_token"]


async def _promote_admin(db: AsyncSession, email: str) -> None:
    user = (await db.execute(select(User).where(User.email == email))).scalar_one()
    user.role = "admin"
    await db.commit()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_user_admin_conversation_flow(client: AsyncClient, db: AsyncSession) -> None:
    user_token = await _token(client, "u@test.io")
    admin_token = await _token(client, "admin@test.io")
    await _promote_admin(db, "admin@test.io")

    # 用户发消息
    resp = await client.post(
        "/messages", headers=_auth(user_token), json={"body": "你好管理员，有个问题"}
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["from_admin"] is False

    # 管理员看到会话列表（含未读）
    convs = (
        await client.get("/admin/messages/conversations", headers=_auth(admin_token))
    ).json()
    assert len(convs) == 1
    conv = convs[0]
    assert conv["unread"] == 1
    assert conv["last_body"] == "你好管理员，有个问题"
    user_id = conv["user_id"]

    # 管理员未读总数
    assert (
        await client.get("/admin/messages/unread_count", headers=_auth(admin_token))
    ).json()["unread"] == 1

    # 管理员打开会话 → 用户消息被标记已读
    msgs = (
        await client.get(f"/admin/messages/{user_id}", headers=_auth(admin_token))
    ).json()
    assert len(msgs) == 1
    assert (
        await client.get("/admin/messages/unread_count", headers=_auth(admin_token))
    ).json()["unread"] == 0

    # 管理员回复
    resp = await client.post(
        f"/admin/messages/{user_id}", headers=_auth(admin_token), json={"body": "你说"}
    )
    assert resp.status_code == 201
    assert resp.json()["from_admin"] is True

    # 用户侧未读=1，拉取会话后清零
    assert (
        await client.get("/messages/unread_count", headers=_auth(user_token))
    ).json()["unread"] == 1
    my = (await client.get("/messages", headers=_auth(user_token))).json()
    assert [m["from_admin"] for m in my] == [False, True]
    assert (
        await client.get("/messages/unread_count", headers=_auth(user_token))
    ).json()["unread"] == 0


async def test_send_attachment_message(client: AsyncClient) -> None:
    token = await _token(client, "att@test.io")
    resp = await client.post(
        "/messages",
        headers=_auth(token),
        json={
            "body": "",
            "attachment_url": "http://x/y.png",
            "attachment_name": "y.png",
            "attachment_kind": "image",
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["attachment_kind"] == "image"
    # 纯文本且无附件应被拒
    bad = await client.post("/messages", headers=_auth(token), json={"body": "   "})
    assert bad.status_code == 422


async def test_non_admin_cannot_access_admin_messages(client: AsyncClient) -> None:
    user_token = await _token(client, "plain@test.io")
    assert (
        await client.get("/admin/messages/conversations", headers=_auth(user_token))
    ).status_code == 403


async def test_messages_require_auth(client: AsyncClient) -> None:
    assert (await client.get("/messages")).status_code in (401, 403)
