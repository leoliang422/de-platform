"""GET /interviews/mine：用户自己上传的面经卡片（投递记录「查看面经」弹窗用）。"""

from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.interview.models import Company, InterviewPost, InterviewQA
from app.modules.users.models import User


async def _token(client: AsyncClient, email: str) -> str:
    await client.post(
        "/auth/register",
        json={"email": email, "password": "secret123", "nickname": email.split("@")[0]},
    )
    resp = await client.post("/auth/login", json={"email": email, "password": "secret123"})
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_list_mine_filters_by_author_and_company(
    client: AsyncClient, db: AsyncSession
) -> None:
    me_token = await _token(client, "mine@test.io")
    other_token = await _token(client, "other@test.io")  # noqa: F841
    me = (await db.execute(select(User).where(User.email == "mine@test.io"))).scalar_one()
    other = (await db.execute(select(User).where(User.email == "other@test.io"))).scalar_one()

    company = Company(name="蔚来")
    db.add(company)
    await db.flush()
    # 我上传的两篇（可见），别人一篇（不返回）
    p1 = InterviewPost(company_id=company.id, status="published", author_id=me.id)
    p1.qa = [InterviewQA(section="round1", order_index=0, question="自我介绍", answer="略")]
    db.add(p1)
    db.add(InterviewPost(company_id=company.id, status="published", author_id=me.id))
    db.add(InterviewPost(company_id=company.id, status="published", author_id=other.id))
    await db.commit()

    cards = (
        await client.get("/interviews/mine?company=蔚来", headers=_auth(me_token))
    ).json()
    assert len(cards) == 2
    assert all(c["locked"] is False for c in cards)
    assert any(c["qa"] for c in cards)

    # 公司名不匹配 → 空
    assert (
        await client.get("/interviews/mine?company=小鹏", headers=_auth(me_token))
    ).json() == []

    # 需要登录
    assert (await client.get("/interviews/mine")).status_code in (401, 403)
