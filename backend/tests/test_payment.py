from decimal import Decimal

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.knowledge.models import KnowledgeItem
from app.modules.projects.models import Project, ProjectQA
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


async def _set_points(db: AsyncSession, email: str, points: int) -> None:
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one()
    user.points_balance = points
    await db.commit()


async def _make_paid_project(db: AsyncSession) -> int:
    project = Project(
        title="付费项目",
        description_md="desc",
        implementation_md="secret impl",
        access_type="paid",
        price_cash=Decimal("199.00"),
        price_points=100,
        status="published",
    )
    db.add(project)
    await db.flush()
    db.add(ProjectQA(project_id=project.id, question_md="q", answer_md="a", order=1))
    await db.commit()
    await db.refresh(project)
    return project.id


async def test_unlock_project_with_points(client: AsyncClient, db: AsyncSession) -> None:
    pid = await _make_paid_project(db)
    token = await _register_and_login(client, "buyer1@test.io")
    await _set_points(db, "buyer1@test.io", 500)

    resp = await client.post(
        "/payment/unlock",
        headers=_auth(token),
        json={"content_type": "project", "content_id": pid, "method": "points"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["balance"] == 400
    assert body["entitlement"]["source"] == "points"

    resp = await client.get(f"/projects/{pid}", headers=_auth(token))
    assert resp.json()["locked"] is False
    assert resp.json()["implementation_md"] == "secret impl"

    resp = await client.get(f"/projects/{pid}")
    assert resp.json()["locked"] is True


async def test_unlock_project_with_cash(client: AsyncClient, db: AsyncSession) -> None:
    pid = await _make_paid_project(db)
    token = await _register_and_login(client, "buyer2@test.io")

    resp = await client.post(
        "/payment/unlock",
        headers=_auth(token),
        json={"content_type": "project", "content_id": pid, "method": "cash"},
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["entitlement"]["source"] == "purchase"
    assert resp.json()["balance"] == 0  # 现金支付不动积分


async def test_insufficient_points(client: AsyncClient, db: AsyncSession) -> None:
    pid = await _make_paid_project(db)
    token = await _register_and_login(client, "poor@test.io")
    await _set_points(db, "poor@test.io", 50)

    resp = await client.post(
        "/payment/unlock",
        headers=_auth(token),
        json={"content_type": "project", "content_id": pid, "method": "points"},
    )
    assert resp.status_code == 400
    assert "积分不足" in resp.json()["detail"]


async def test_free_content_rejects_unlock(client: AsyncClient, db: AsyncSession) -> None:
    project = Project(
        title="免费项目",
        description_md="d",
        implementation_md="i",
        access_type="free",
        status="published",
    )
    db.add(project)
    await db.commit()
    await db.refresh(project)

    token = await _register_and_login(client, "free@test.io")
    resp = await client.post(
        "/payment/unlock",
        headers=_auth(token),
        json={"content_type": "project", "content_id": project.id, "method": "cash"},
    )
    assert resp.status_code == 400


async def test_double_unlock_is_idempotent(client: AsyncClient, db: AsyncSession) -> None:
    pid = await _make_paid_project(db)
    token = await _register_and_login(client, "dbl@test.io")
    await _set_points(db, "dbl@test.io", 500)

    payload = {"content_type": "project", "content_id": pid, "method": "points"}
    first = await client.post("/payment/unlock", headers=_auth(token), json=payload)
    assert first.json()["balance"] == 400
    assert first.json()["already_unlocked"] is False

    second = await client.post("/payment/unlock", headers=_auth(token), json=payload)
    assert second.status_code == 200
    assert second.json()["already_unlocked"] is True
    assert second.json()["balance"] == 400  # 未二次扣分


async def test_paid_knowledge_locked_until_unlock(client: AsyncClient, db: AsyncSession) -> None:
    item = KnowledgeItem(
        title="付费知识",
        content_md="paid body",
        is_paid=True,
        price_cash=Decimal("9.90"),
        price_points=100,
        status="published",
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)

    resp = await client.get(f"/knowledge/{item.id}")
    assert resp.json()["locked"] is True
    assert resp.json()["content_md"] is None

    token = await _register_and_login(client, "kbuyer@test.io")
    await _set_points(db, "kbuyer@test.io", 500)
    resp = await client.post(
        "/payment/unlock",
        headers=_auth(token),
        json={"content_type": "knowledge", "content_id": item.id, "method": "points"},
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get(f"/knowledge/{item.id}", headers=_auth(token))
    assert resp.json()["locked"] is False
    assert resp.json()["content_md"] == "paid body"


async def test_entitlements_me(client: AsyncClient, db: AsyncSession) -> None:
    pid = await _make_paid_project(db)
    token = await _register_and_login(client, "list@test.io")
    await _set_points(db, "list@test.io", 500)
    await client.post(
        "/payment/unlock",
        headers=_auth(token),
        json={"content_type": "project", "content_id": pid, "method": "points"},
    )
    resp = await client.get("/payment/entitlements/me", headers=_auth(token))
    assert resp.status_code == 200
    assert len(resp.json()) == 1
    assert resp.json()[0]["content_id"] == pid
