"""M6.2 图片上传：类型校验、成功落盘、鉴权、工厂回退。"""

from pathlib import Path

import pytest
from httpx import AsyncClient

from app.core.config import get_settings
from app.modules.files.storage import S3Storage, get_storage

# 1x1 透明 PNG
_PNG = (
    b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
    b"\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01"
    b"\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82"
)


async def _token(client: AsyncClient, email: str) -> str:
    await client.post(
        "/auth/register",
        json={"email": email, "password": "secret123", "nickname": email.split("@")[0]},
    )
    resp = await client.post("/auth/login", json={"email": email, "password": "secret123"})
    return resp.json()["access_token"]


def _auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


async def test_upload_image_success(
    client: AsyncClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("STORAGE_LOCAL_DIR", str(tmp_path))
    get_settings.cache_clear()
    try:
        token = await _token(client, "up1@test.io")
        resp = await client.post(
            "/files/images",
            headers=_auth(token),
            files={"file": ("a.png", _PNG, "image/png")},
        )
        assert resp.status_code == 201, resp.text
        url = resp.json()["url"]
        assert "/uploads/" in url
        # 文件确实落盘到临时目录
        key = url.split("/uploads/", 1)[1]
        assert (tmp_path / key).exists()
    finally:
        get_settings.cache_clear()


async def test_upload_rejects_non_image(client: AsyncClient) -> None:
    token = await _token(client, "up2@test.io")
    resp = await client.post(
        "/files/images",
        headers=_auth(token),
        files={"file": ("a.txt", b"hello", "text/plain")},
    )
    assert resp.status_code == 400


async def test_upload_requires_auth(client: AsyncClient) -> None:
    resp = await client.post(
        "/files/images",
        files={"file": ("a.png", _PNG, "image/png")},
    )
    assert resp.status_code in (401, 403)


def test_storage_factory_falls_back_to_local(monkeypatch: pytest.MonkeyPatch) -> None:
    assert S3Storage.is_configured() is False
    monkeypatch.setenv("STORAGE_PROVIDER", "s3")
    get_settings.cache_clear()
    try:
        assert get_storage().name == "local"  # 凭证未配齐回退 local
    finally:
        get_settings.cache_clear()
