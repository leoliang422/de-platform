from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.users.models import User


async def _register_and_login(client: AsyncClient, email: str) -> str:
    await client.post(
        "/auth/register",
        json={"email": email, "password": "secret123", "nickname": email.split("@")[0]},
    )
    resp = await client.post("/auth/login", json={"email": email, "password": "secret123"})
    return resp.json()["access_token"]


async def _promote_admin(db: AsyncSession, email: str) -> None:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one()
    user.role = "admin"
    await db.commit()


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_admin_knowledge_crud_and_visibility(
    client: AsyncClient, db: AsyncSession
) -> None:
    admin_token = await _register_and_login(client, "kadmin@test.io")
    await _promote_admin(db, "kadmin@test.io")

    # 直接粘贴 markdown 新建（跳过大模型），默认发布
    resp = await client.post(
        "/admin/content/knowledge",
        headers=_auth(admin_token),
        json={"title": "Spark Shuffle 原理", "content_md": "## Shuffle\n直接录入的正文"},
    )
    assert resp.status_code == 201, resp.text
    item_id = resp.json()["id"]
    assert resp.json()["status"] == "published"

    # 已发布 → 公开列表可见
    resp = await client.get("/knowledge")
    assert "Spark Shuffle 原理" in [i["title"] for i in resp.json()]

    # 下架（status=draft）→ 公开列表不可见，但管理员全状态列表仍可见
    resp = await client.patch(
        f"/admin/content/knowledge/{item_id}",
        headers=_auth(admin_token),
        json={"status": "draft"},
    )
    assert resp.status_code == 200
    resp = await client.get("/knowledge")
    assert "Spark Shuffle 原理" not in [i["title"] for i in resp.json()]
    resp = await client.get("/admin/content/knowledge", headers=_auth(admin_token))
    assert any(i["id"] == item_id and i["status"] == "draft" for i in resp.json())

    # 编辑标题
    resp = await client.patch(
        f"/admin/content/knowledge/{item_id}",
        headers=_auth(admin_token),
        json={"title": "Spark Shuffle 深入", "status": "published"},
    )
    assert resp.json()["title"] == "Spark Shuffle 深入"

    # 删除
    resp = await client.delete(
        f"/admin/content/knowledge/{item_id}", headers=_auth(admin_token)
    )
    assert resp.status_code == 204
    resp = await client.get("/admin/content/knowledge", headers=_auth(admin_token))
    assert all(i["id"] != item_id for i in resp.json())


async def test_admin_content_requires_admin(client: AsyncClient) -> None:
    user_token = await _register_and_login(client, "plain@test.io")
    resp = await client.post(
        "/admin/content/knowledge",
        headers=_auth(user_token),
        json={"title": "x", "content_md": "y"},
    )
    assert resp.status_code == 403


async def test_admin_interview_and_project_create(
    client: AsyncClient, db: AsyncSession
) -> None:
    admin_token = await _register_and_login(client, "iadmin@test.io")
    await _promote_admin(db, "iadmin@test.io")

    resp = await client.post(
        "/admin/content/interview",
        headers=_auth(admin_token),
        json={"company_name": "字节跳动", "position": "数据开发", "content_md": "一面二面"},
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["subtitle"] == "字节跳动"

    resp = await client.post(
        "/admin/content/project",
        headers=_auth(admin_token),
        json={
            "title": "实时数仓项目",
            "description_md": "描述",
            "access_type": "paid",
            "price_points": 50,
        },
    )
    assert resp.status_code == 201, resp.text
    assert resp.json()["subtitle"] == "paid"
