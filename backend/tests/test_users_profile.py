"""M6.1 账号安全 + 个人资料：改密码、编辑资料、公开主页。"""

from httpx import AsyncClient


async def _register_and_login(client: AsyncClient, email: str, password: str = "secret123") -> str:
    await client.post(
        "/auth/register",
        json={"email": email, "password": password, "nickname": email.split("@")[0]},
    )
    resp = await client.post("/auth/login", json={"email": email, "password": password})
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_update_profile(client: AsyncClient) -> None:
    token = await _register_and_login(client, "prof1@test.io")
    resp = await client.patch(
        "/users/me",
        headers=_auth(token),
        json={"nickname": "新昵称", "bio": "数据开发爱好者", "job_title": "数据工程师"},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["nickname"] == "新昵称"
    assert body["bio"] == "数据开发爱好者"
    assert body["job_title"] == "数据工程师"

    me = await client.get("/users/me", headers=_auth(token))
    assert me.json()["nickname"] == "新昵称"


async def test_partial_update_keeps_other_fields(client: AsyncClient) -> None:
    token = await _register_and_login(client, "prof2@test.io")
    await client.patch("/users/me", headers=_auth(token), json={"bio": "hello"})
    resp = await client.patch("/users/me", headers=_auth(token), json={"job_title": "分析师"})
    assert resp.status_code == 200
    assert resp.json()["bio"] == "hello"  # 未提交的字段保持不变
    assert resp.json()["job_title"] == "分析师"


async def test_change_password_then_login(client: AsyncClient) -> None:
    token = await _register_and_login(client, "pw@test.io", "oldpass123")
    resp = await client.patch(
        "/users/me/password",
        headers=_auth(token),
        json={"old_password": "oldpass123", "new_password": "newpass456"},
    )
    assert resp.status_code == 204, resp.text

    old = await client.post("/auth/login", json={"email": "pw@test.io", "password": "oldpass123"})
    assert old.status_code == 401
    new = await client.post("/auth/login", json={"email": "pw@test.io", "password": "newpass456"})
    assert new.status_code == 200


async def test_change_password_wrong_old(client: AsyncClient) -> None:
    token = await _register_and_login(client, "pw2@test.io", "oldpass123")
    resp = await client.patch(
        "/users/me/password",
        headers=_auth(token),
        json={"old_password": "WRONG", "new_password": "newpass456"},
    )
    assert resp.status_code == 400
    assert "原密码" in resp.json()["detail"]


async def test_change_password_same_as_old(client: AsyncClient) -> None:
    token = await _register_and_login(client, "pw3@test.io", "samepass123")
    resp = await client.patch(
        "/users/me/password",
        headers=_auth(token),
        json={"old_password": "samepass123", "new_password": "samepass123"},
    )
    assert resp.status_code == 400


async def test_public_profile(client: AsyncClient) -> None:
    token = await _register_and_login(client, "pub@test.io")
    me = await client.get("/users/me", headers=_auth(token))
    uid = me.json()["id"]

    resp = await client.get(f"/users/{uid}")
    assert resp.status_code == 200
    body = resp.json()
    assert body["nickname"] == "pub"
    assert "email" not in body  # 公开资料不暴露邮箱

    missing = await client.get("/users/999999")
    assert missing.status_code == 404


async def test_password_min_length_validation(client: AsyncClient) -> None:
    token = await _register_and_login(client, "pw4@test.io")
    resp = await client.patch(
        "/users/me/password",
        headers=_auth(token),
        json={"old_password": "secret123", "new_password": "123"},
    )
    assert resp.status_code == 422
