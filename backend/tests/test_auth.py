from httpx import AsyncClient


async def test_register_login_and_me(client: AsyncClient) -> None:
    resp = await client.post(
        "/auth/register",
        json={"email": "neo@matrix.io", "password": "secret1", "nickname": "Neo"},
    )
    assert resp.status_code == 201, resp.text
    body = resp.json()
    assert body["email"] == "neo@matrix.io"
    assert body["role"] == "user"
    assert body["points_balance"] == 0

    resp = await client.post("/auth/login", json={"email": "neo@matrix.io", "password": "secret1"})
    assert resp.status_code == 200, resp.text
    tokens = resp.json()
    assert tokens["token_type"] == "bearer"

    resp = await client.get(
        "/users/me", headers={"Authorization": f"Bearer {tokens['access_token']}"}
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["nickname"] == "Neo"


async def test_refresh_token(client: AsyncClient) -> None:
    await client.post(
        "/auth/register",
        json={"email": "trin@matrix.io", "password": "secret1", "nickname": "Trinity"},
    )
    login = await client.post(
        "/auth/login", json={"email": "trin@matrix.io", "password": "secret1"}
    )
    refresh_token = login.json()["refresh_token"]

    resp = await client.post("/auth/refresh", json={"refresh_token": refresh_token})
    assert resp.status_code == 200, resp.text
    assert "access_token" in resp.json()


async def test_duplicate_email_rejected(client: AsyncClient) -> None:
    payload = {"email": "dup@matrix.io", "password": "secret1", "nickname": "Dup"}
    first = await client.post("/auth/register", json=payload)
    assert first.status_code == 201
    second = await client.post("/auth/register", json=payload)
    assert second.status_code == 400


async def test_wrong_password_rejected(client: AsyncClient) -> None:
    await client.post(
        "/auth/register",
        json={"email": "smith@matrix.io", "password": "secret1", "nickname": "Smith"},
    )
    resp = await client.post(
        "/auth/login", json={"email": "smith@matrix.io", "password": "wrongpass"}
    )
    assert resp.status_code == 401


async def test_me_requires_auth(client: AsyncClient) -> None:
    resp = await client.get("/users/me")
    assert resp.status_code in (401, 403)
