"""投递记录管理：投递列表 / 记录 / 面试日历（均按用户隔离）。"""

from httpx import AsyncClient


async def _token(client: AsyncClient, email: str) -> str:
    await client.post(
        "/auth/register",
        json={"email": email, "password": "secret123", "nickname": email.split("@")[0]},
    )
    resp = await client.post("/auth/login", json={"email": email, "password": "secret123"})
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_list_record_crud_flow(client: AsyncClient) -> None:
    token = await _token(client, "app1@test.io")

    # 建列表
    resp = await client.post("/applications/lists", headers=_auth(token), json={"name": "秋招"})
    assert resp.status_code == 201, resp.text
    list_id = resp.json()["id"]
    assert resp.json()["name"] == "秋招"
    assert resp.json()["records"] == []

    # 加记录
    resp = await client.post(
        f"/applications/lists/{list_id}/records",
        headers=_auth(token),
        json={
            "company_name": "字节跳动",
            "nature": "private",
            "position": "数据开发",
            "applied_date": "2026-08-27",
            "status": "applied",
        },
    )
    assert resp.status_code == 201, resp.text
    rec_id = resp.json()["id"]
    assert resp.json()["company_name"] == "字节跳动"

    # 改状态
    resp = await client.patch(
        f"/applications/records/{rec_id}",
        headers=_auth(token),
        json={"status": "round1"},
    )
    assert resp.status_code == 200
    assert resp.json()["status"] == "round1"

    # 列表带出记录
    lists = (await client.get("/applications/lists", headers=_auth(token))).json()
    assert len(lists) == 1
    assert len(lists[0]["records"]) == 1
    assert lists[0]["records"][0]["status"] == "round1"

    # 重命名列表
    resp = await client.patch(
        f"/applications/lists/{list_id}", headers=_auth(token), json={"name": "2026秋招"}
    )
    assert resp.status_code == 200
    assert resp.json()["name"] == "2026秋招"

    # 删记录
    resp = await client.delete(f"/applications/records/{rec_id}", headers=_auth(token))
    assert resp.status_code == 204
    lists = (await client.get("/applications/lists", headers=_auth(token))).json()
    assert lists[0]["records"] == []

    # 删列表
    resp = await client.delete(f"/applications/lists/{list_id}", headers=_auth(token))
    assert resp.status_code == 204
    assert (await client.get("/applications/lists", headers=_auth(token))).json() == []


async def test_lists_isolated_between_users(client: AsyncClient) -> None:
    a = await _token(client, "owner@test.io")
    b = await _token(client, "intruder@test.io")

    list_id = (
        await client.post("/applications/lists", headers=_auth(a), json={"name": "私有"})
    ).json()["id"]

    # 他人看不到、也不能改/删
    assert (await client.get("/applications/lists", headers=_auth(b))).json() == []
    assert (
        await client.patch(
            f"/applications/lists/{list_id}", headers=_auth(b), json={"name": "hack"}
        )
    ).status_code == 404
    assert (
        await client.delete(f"/applications/lists/{list_id}", headers=_auth(b))
    ).status_code == 404
    assert (
        await client.post(
            f"/applications/lists/{list_id}/records",
            headers=_auth(b),
            json={"company_name": "x"},
        )
    ).status_code == 404


async def test_calendar_crud_and_month_filter(client: AsyncClient) -> None:
    token = await _token(client, "cal@test.io")

    ev = (
        await client.post(
            "/applications/calendar",
            headers=_auth(token),
            json={
                "title": "字节一面",
                "event_date": "2026-09-10",
                "start_time": "14:00",
                "end_time": "15:00",
                "note": "视频面",
            },
        )
    ).json()
    ev_id = ev["id"]
    assert ev["title"] == "字节一面"

    # 另一个月的事件
    await client.post(
        "/applications/calendar",
        headers=_auth(token),
        json={"title": "别的月", "event_date": "2026-10-01"},
    )

    # 按月过滤
    sep = (
        await client.get("/applications/calendar?month=2026-09", headers=_auth(token))
    ).json()
    assert [e["title"] for e in sep] == ["字节一面"]

    # 全部
    allev = (await client.get("/applications/calendar", headers=_auth(token))).json()
    assert len(allev) == 2

    # 改
    resp = await client.patch(
        f"/applications/calendar/{ev_id}",
        headers=_auth(token),
        json={"title": "字节二面", "start_time": "16:00"},
    )
    assert resp.status_code == 200
    assert resp.json()["title"] == "字节二面"
    assert resp.json()["start_time"] == "16:00"

    # 删
    assert (
        await client.delete(f"/applications/calendar/{ev_id}", headers=_auth(token))
    ).status_code == 204
    assert (
        len((await client.get("/applications/calendar", headers=_auth(token))).json()) == 1
    )


async def test_requires_auth(client: AsyncClient) -> None:
    assert (await client.get("/applications/lists")).status_code in (401, 403)
    assert (await client.get("/applications/calendar")).status_code in (401, 403)
