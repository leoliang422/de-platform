"""M6.4 通知中心：审核结果通知作者、未读数、标记已读。"""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.catalog.models import Category
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


async def _make_admin(db: AsyncSession, email: str) -> None:
    user = (await db.execute(select(User).where(User.email == email))).scalar_one()
    user.role = "admin"
    await db.commit()


async def _submit(client: AsyncClient, db: AsyncSession, token: str, title: str) -> int:
    cat = Category(section="knowledge", name="Hive", slug="hive", order=0)
    db.add(cat)
    await db.commit()
    await db.refresh(cat)
    resp = await client.post(
        "/submissions",
        headers=_auth(token),
        json={
            "target_type": "knowledge",
            "title": title,
            "raw_content": "内容",
            "category_id": cat.id,
        },
    )
    return resp.json()["id"]


async def test_approve_notifies_author(client: AsyncClient, db: AsyncSession) -> None:
    author = await _register_and_login(client, "author@test.io")
    sid = await _submit(client, db, author, "我的知识")

    admin = await _register_and_login(client, "admin1@test.io")
    await _make_admin(db, "admin1@test.io")
    approve = await client.post(f"/admin/submissions/{sid}/approve", headers=_auth(admin))
    assert approve.status_code == 200, approve.text

    # 作者应收到一条通知
    notifs = await client.get("/notifications", headers=_auth(author))
    assert notifs.status_code == 200
    body = notifs.json()
    assert len(body) == 1
    assert body[0]["type"] == "submission_approved"
    assert body[0]["read_at"] is None

    count = await client.get("/notifications/unread_count", headers=_auth(author))
    assert count.json()["unread"] == 1


async def test_reject_notifies_author(client: AsyncClient, db: AsyncSession) -> None:
    author = await _register_and_login(client, "author2@test.io")
    sid = await _submit(client, db, author, "待驳回")

    admin = await _register_and_login(client, "admin2@test.io")
    await _make_admin(db, "admin2@test.io")
    resp = await client.post(
        f"/admin/submissions/{sid}/reject",
        headers=_auth(admin),
        json={"reason": "格式不符"},
    )
    assert resp.status_code == 200, resp.text

    notifs = await client.get("/notifications", headers=_auth(author))
    assert notifs.json()[0]["type"] == "submission_rejected"
    assert "格式不符" in notifs.json()[0]["body"]


async def test_mark_read_and_read_all(client: AsyncClient, db: AsyncSession) -> None:
    author = await _register_and_login(client, "author3@test.io")
    sid = await _submit(client, db, author, "标记已读")
    admin = await _register_and_login(client, "admin3@test.io")
    await _make_admin(db, "admin3@test.io")
    await client.post(f"/admin/submissions/{sid}/approve", headers=_auth(admin))

    notifs = await client.get("/notifications", headers=_auth(author))
    nid = notifs.json()[0]["id"]

    read = await client.post(f"/notifications/{nid}/read", headers=_auth(author))
    assert read.status_code == 200
    assert read.json()["read_at"] is not None

    count = await client.get("/notifications/unread_count", headers=_auth(author))
    assert count.json()["unread"] == 0

    all_read = await client.post("/notifications/read-all", headers=_auth(author))
    assert all_read.json()["unread"] == 0


async def test_cannot_read_others_notification(client: AsyncClient, db: AsyncSession) -> None:
    author = await _register_and_login(client, "author4@test.io")
    sid = await _submit(client, db, author, "私有通知")
    admin = await _register_and_login(client, "admin4@test.io")
    await _make_admin(db, "admin4@test.io")
    await client.post(f"/admin/submissions/{sid}/approve", headers=_auth(admin))
    nid = (await client.get("/notifications", headers=_auth(author))).json()[0]["id"]

    intruder = await _register_and_login(client, "intruder2@test.io")
    resp = await client.post(f"/notifications/{nid}/read", headers=_auth(intruder))
    assert resp.status_code == 404


async def test_delete_and_clear_notifications(client: AsyncClient, db: AsyncSession) -> None:
    author = await _register_and_login(client, "ndel@test.io")
    admin = await _register_and_login(client, "ndeladmin@test.io")
    await _make_admin(db, "ndeladmin@test.io")
    for title in ("n1", "n2"):
        sid = await _submit(client, db, author, title)
        await client.post(f"/admin/submissions/{sid}/approve", headers=_auth(admin))

    notifs = (await client.get("/notifications", headers=_auth(author))).json()
    assert len(notifs) == 2

    # 删除一条（他人无权删）
    intruder = await _register_and_login(client, "nintruder@test.io")
    assert (
        await client.delete(f"/notifications/{notifs[0]['id']}", headers=_auth(intruder))
    ).status_code == 404
    assert (
        await client.delete(f"/notifications/{notifs[0]['id']}", headers=_auth(author))
    ).status_code == 204
    assert len((await client.get("/notifications", headers=_auth(author))).json()) == 1

    # 清空全部
    assert (await client.delete("/notifications", headers=_auth(author))).status_code == 204
    assert (await client.get("/notifications", headers=_auth(author))).json() == []
