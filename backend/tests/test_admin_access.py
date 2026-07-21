"""管理员：无限查看（不受免费额度）+ 查看/授予/收回用户权限（模块 & 项目）。"""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.projects.models import Project
from app.modules.sql_bank.models import SqlQuestion
from app.modules.users.models import User


async def _register_and_login(client: AsyncClient, email: str) -> str:
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


async def _user_id(db: AsyncSession, email: str) -> int:
    user = (await db.execute(select(User).where(User.email == email))).scalar_one()
    return user.id


async def test_admin_bypasses_free_quota(client: AsyncClient, db: AsyncSession) -> None:
    # 建 12 道题，管理员应能无限查看且 summary 显示已解锁
    for i in range(12):
        db.add(
            SqlQuestion(
                title=f"admin题{i}",
                prompt_md=f"题干{i}",
                answer_md=f"答案{i}",
                difficulty="medium",
                status="published",
            )
        )
    await db.commit()

    admin_token = await _register_and_login(client, "adminview@test.io")
    await _promote_admin(db, "adminview@test.io")

    summary = (await client.get("/access/sql", headers=_auth(admin_token))).json()
    assert summary["unlocked"] is True

    qid = (
        await db.execute(select(SqlQuestion.id).where(SqlQuestion.title == "admin题0"))
    ).scalar_one()
    detail = (await client.get(f"/sql-questions/{qid}", headers=_auth(admin_token))).json()
    assert detail["answer_locked"] is False
    assert detail["answer_md"] == "答案0"


async def test_admin_grant_and_revoke_module_and_project(
    client: AsyncClient, db: AsyncSession
) -> None:
    project = Project(title="付费项目", access_type="points", status="published")
    db.add(project)
    await db.commit()
    await db.refresh(project)

    admin_token = await _register_and_login(client, "boss@test.io")
    await _promote_admin(db, "boss@test.io")
    await _register_and_login(client, "member@test.io")
    member_id = await _user_id(db, "member@test.io")

    # 初始：模块未解锁、项目未解锁
    access = (
        await client.get(f"/admin/users/{member_id}/access", headers=_auth(admin_token))
    ).json()
    sql_mod = next(m for m in access["modules"] if m["module"] == "sql")
    assert sql_mod["unlocked"] is False
    proj = next(p for p in access["projects"] if p["id"] == project.id)
    assert proj["unlocked"] is False

    # 授予 SQL 模块
    granted = (
        await client.put(f"/admin/users/{member_id}/access/module/sql", headers=_auth(admin_token))
    ).json()
    assert next(m for m in granted["modules"] if m["module"] == "sql")["unlocked"] is True

    # 授予项目
    granted = (
        await client.put(
            f"/admin/users/{member_id}/access/project/{project.id}",
            headers=_auth(admin_token),
        )
    ).json()
    assert next(p for p in granted["projects"] if p["id"] == project.id)["unlocked"] is True

    # 收回项目
    revoked = (
        await client.delete(
            f"/admin/users/{member_id}/access/project/{project.id}",
            headers=_auth(admin_token),
        )
    ).json()
    assert next(p for p in revoked["projects"] if p["id"] == project.id)["unlocked"] is False

    # 收回模块
    revoked = (
        await client.delete(
            f"/admin/users/{member_id}/access/module/sql", headers=_auth(admin_token)
        )
    ).json()
    assert next(m for m in revoked["modules"] if m["module"] == "sql")["unlocked"] is False


async def test_non_admin_cannot_manage_access(client: AsyncClient, db: AsyncSession) -> None:
    token = await _register_and_login(client, "normal@test.io")
    uid = await _user_id(db, "normal@test.io")
    resp = await client.get(f"/admin/users/{uid}/access", headers=_auth(token))
    assert resp.status_code == 403
