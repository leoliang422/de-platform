"""积分化模块级访问：SQL/面经 免费 10 条，超出后一次性积分解锁整个模块。"""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.interview.models import Company, InterviewPost, InterviewQA
from app.modules.sql_bank.models import SqlQuestion
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


async def _set_points(db: AsyncSession, email: str, amount: int) -> None:
    user = (await db.execute(select(User).where(User.email == email))).scalar_one()
    user.points_balance = amount
    await db.commit()


async def _make_sql(db: AsyncSession, n: int) -> list[int]:
    ids: list[int] = []
    for i in range(n):
        q = SqlQuestion(
            title=f"题目{i}",
            prompt_md=f"题干{i}",
            answer_md=f"答案{i}",
            difficulty="medium",
            status="published",
        )
        db.add(q)
        await db.flush()
        ids.append(q.id)
    await db.commit()
    return ids


async def test_sql_answer_locked_for_anonymous(client: AsyncClient, db: AsyncSession) -> None:
    [qid] = await _make_sql(db, 1)
    detail = (await client.get(f"/sql-questions/{qid}")).json()
    assert detail["prompt_md"] == "题干0"
    assert detail["answer_locked"] is True
    assert detail["answer_md"] is None


async def test_sql_free_quota_then_module_unlock(client: AsyncClient, db: AsyncSession) -> None:
    ids = await _make_sql(db, 12)
    token = await _login(client, "sqluser@test.io")
    await _set_points(db, "sqluser@test.io", 100)

    # 前 10 条：免费查看答案
    for i, qid in enumerate(ids[:10]):
        r = await client.post(f"/sql-questions/{qid}/reveal", headers=_auth(token))
        assert r.status_code == 200
        body = r.json()
        assert body["answer_locked"] is False
        assert body["answer_md"] == f"答案{i}"
        assert body["free_used"] == i + 1

    # 已查看过的条目再次 GET 详情仍可见（永久有效）
    seen = (await client.get(f"/sql-questions/{ids[0]}", headers=_auth(token))).json()
    assert seen["answer_locked"] is False

    # 第 11 条：超出免费额度 → 锁定
    r = await client.post(f"/sql-questions/{ids[10]}/reveal", headers=_auth(token))
    assert r.json()["answer_locked"] is True
    assert r.json()["answer_md"] is None

    # 解锁整个 SQL 模块
    unlock = await client.post("/access/sql/unlock", headers=_auth(token))
    assert unlock.status_code == 200, unlock.text
    assert unlock.json()["unlocked"] is True
    assert unlock.json()["balance"] == 50  # 100 - 50

    # 解锁后第 11、12 条均可见
    r = await client.post(f"/sql-questions/{ids[10]}/reveal", headers=_auth(token))
    assert r.json()["answer_locked"] is False
    r = await client.get(f"/sql-questions/{ids[11]}", headers=_auth(token))
    assert r.json()["answer_locked"] is False

    summary = (await client.get("/access/sql", headers=_auth(token))).json()
    assert summary["unlocked"] is True


async def test_sql_unlock_requires_points(client: AsyncClient, db: AsyncSession) -> None:
    await _make_sql(db, 1)
    token = await _login(client, "poor@test.io")
    await _set_points(db, "poor@test.io", 5)
    r = await client.post("/access/sql/unlock", headers=_auth(token))
    assert r.status_code == 400


async def test_interview_card_locked_then_revealed(client: AsyncClient, db: AsyncSession) -> None:
    company = Company(name="某公司")
    db.add(company)
    await db.flush()
    post = InterviewPost(
        company_id=company.id,
        title="某公司",
        interview_type="campus",
        content_md="",
        status="published",
        qa=[InterviewQA(section="round1", order_index=0, question="Q1", answer="A1")],
    )
    db.add(post)
    await db.commit()
    await db.refresh(post)

    token = await _login(client, "ivuser@test.io")

    # 列表：默认锁定，qa 为空
    by_type = (
        await client.get(
            f"/companies/{company.id}/interviews-by-type", headers=_auth(token)
        )
    ).json()
    campus = next(g for g in by_type["groups"] if g["interview_type"] == "campus")
    assert campus["posts"][0]["locked"] is True
    assert campus["posts"][0]["qa"] == []
    assert by_type["access"]["free_limit"] == 10

    # reveal：消耗一次免费名额后可见
    revealed = (await client.post(f"/interviews/{post.id}/reveal", headers=_auth(token))).json()
    assert revealed["locked"] is False
    assert revealed["qa"][0]["question"] == "Q1"

    # 再次进入列表，该卡片已解锁
    by_type2 = (
        await client.get(
            f"/companies/{company.id}/interviews-by-type", headers=_auth(token)
        )
    ).json()
    campus2 = next(g for g in by_type2["groups"] if g["interview_type"] == "campus")
    assert campus2["posts"][0]["locked"] is False
    assert by_type2["access"]["free_used"] == 1
