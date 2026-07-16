from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.points.models import PointLedger
from app.modules.points.service import PointsService
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


async def test_knowledge_submission_review_and_points(
    client: AsyncClient, db: AsyncSession
) -> None:
    user_token = await _register_and_login(client, "author@test.io")

    resp = await client.post(
        "/submissions",
        headers=_auth(user_token),
        json={
            "target_type": "knowledge",
            "title": "Hive 小文件治理",
            "raw_content": "小文件太多影响性能，可用 concatenate、合并任务等。",
        },
    )
    assert resp.status_code == 201, resp.text
    sub = resp.json()
    assert sub["status"] == "pending_review"  # MockLLM 同步加工完成
    assert sub["processed_md"]
    sub_id = sub["id"]

    admin_token = await _register_and_login(client, "boss@test.io")
    await _promote_admin(db, "boss@test.io")

    resp = await client.get("/admin/submissions", headers=_auth(admin_token))
    assert resp.status_code == 200
    assert any(s["id"] == sub_id for s in resp.json())

    resp = await client.post(f"/admin/submissions/{sub_id}/approve", headers=_auth(admin_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "published"

    resp = await client.get("/knowledge")
    assert "Hive 小文件治理" in [i["title"] for i in resp.json()]

    resp = await client.get("/points/me", headers=_auth(user_token))
    body = resp.json()
    assert body["balance"] == 10
    assert len(body["ledger"]) == 1
    assert body["ledger"][0]["ref_type"] == "submission"


async def test_reject_does_not_grant_points(client: AsyncClient, db: AsyncSession) -> None:
    user_token = await _register_and_login(client, "author2@test.io")
    resp = await client.post(
        "/submissions",
        headers=_auth(user_token),
        json={"target_type": "knowledge", "title": "t", "raw_content": "raw body"},
    )
    sub_id = resp.json()["id"]

    admin_token = await _register_and_login(client, "boss2@test.io")
    await _promote_admin(db, "boss2@test.io")

    resp = await client.post(
        f"/admin/submissions/{sub_id}/reject",
        headers=_auth(admin_token),
        json={"reason": "内容不完整"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "rejected"
    assert resp.json()["reject_reason"] == "内容不完整"

    resp = await client.get("/points/me", headers=_auth(user_token))
    assert resp.json()["balance"] == 0


async def test_admin_requires_admin_role(client: AsyncClient) -> None:
    user_token = await _register_and_login(client, "plainuser@test.io")
    resp = await client.get("/admin/submissions", headers=_auth(user_token))
    assert resp.status_code == 403


async def test_interview_submission_creates_company(client: AsyncClient, db: AsyncSession) -> None:
    user_token = await _register_and_login(client, "author3@test.io")
    resp = await client.post(
        "/submissions",
        headers=_auth(user_token),
        json={
            "target_type": "interview",
            "title": "字节数开一面",
            "raw_content": "问了数据倾斜和连续登录 SQL。",
            "company_name": "字节跳动",
            "position": "数据开发工程师",
        },
    )
    assert resp.status_code == 201, resp.text
    sub_id = resp.json()["id"]

    admin_token = await _register_and_login(client, "boss3@test.io")
    await _promote_admin(db, "boss3@test.io")
    resp = await client.post(f"/admin/submissions/{sub_id}/approve", headers=_auth(admin_token))
    assert resp.status_code == 200

    resp = await client.get("/companies")
    companies = {c["name"]: c["id"] for c in resp.json()}
    assert "字节跳动" in companies
    resp = await client.get(f"/companies/{companies['字节跳动']}/interviews")
    assert resp.json()[0]["position"] == "数据开发工程师"

    resp = await client.get("/points/me", headers=_auth(user_token))
    assert resp.json()["balance"] == 20


async def test_interview_submission_requires_company(client: AsyncClient) -> None:
    user_token = await _register_and_login(client, "author4@test.io")
    resp = await client.post(
        "/submissions",
        headers=_auth(user_token),
        json={"target_type": "interview", "title": "无企业", "raw_content": "x"},
    )
    assert resp.status_code == 422


async def test_points_grant_is_idempotent(db: AsyncSession) -> None:
    user = User(email="pts@test.io", password_hash="x", nickname="pts", role="user")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    service = PointsService(db)
    first = await service.grant(user.id, 100, "test", "submission", 999)
    second = await service.grant(user.id, 100, "test", "submission", 999)
    await db.commit()

    assert first is not None
    assert second is None
    await db.refresh(user)
    assert user.points_balance == 100
    entries = (await db.execute(select(PointLedger))).scalars().all()
    assert len(entries) == 1
