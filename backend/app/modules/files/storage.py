from __future__ import annotations

import datetime as dt
import uuid
from pathlib import Path
from typing import Protocol, runtime_checkable

from app.core.config import get_settings


class StorageNotConfigured(RuntimeError):
    """真实对象存储未配齐凭证时抛出，工厂据此回退 local。"""


def _make_key(ext: str) -> str:
    now = dt.datetime.now(dt.UTC)
    return f"{now:%Y/%m}/{uuid.uuid4().hex}{ext}"


@runtime_checkable
class Storage(Protocol):
    name: str

    async def save(self, *, data: bytes, ext: str, content_type: str) -> str:
        """保存文件，返回相对 key（如 ``2026/07/<uuid>.png``）。"""
        ...

    def public_url(self, key: str, request_base: str) -> str: ...


class LocalStorage:
    """存本地磁盘，由后端 ``/uploads`` 静态路由提供访问（默认，零外部依赖）。

    注意：Render 等平台磁盘为临时存储，重启/重部署会丢失。生产建议用 S3/R2。
    """

    name = "local"

    def __init__(self) -> None:
        s = get_settings()
        self.root = Path(s.storage_local_dir)
        self.public_base = s.storage_public_base_url

    async def save(self, *, data: bytes, ext: str, content_type: str) -> str:
        key = _make_key(ext)
        path = self.root / key
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def public_url(self, key: str, request_base: str) -> str:
        base = (self.public_base or request_base).rstrip("/")
        return f"{base}/uploads/{key}"


class DbStorage:
    """把文件存进数据库（stored_files 表），由 ``/uploads/<key>`` 路由读取。

    适合 Render 免费实例这类“临时磁盘”环境：文件随数据库持久化，重部署不丢失，
    且无需外部对象存储。图片较小（≤5MB），对 Postgres/SQLite 均可用。
    """

    name = "db"

    def __init__(self) -> None:
        self.public_base = get_settings().storage_public_base_url

    async def save(self, *, data: bytes, ext: str, content_type: str) -> str:
        # 延迟导入，避免与模型注册产生循环依赖。
        from app.core.database import SessionLocal
        from app.modules.files.models import StoredFile

        key = _make_key(ext)
        async with SessionLocal() as db:
            db.add(StoredFile(key=key, content_type=content_type, data=data))
            await db.commit()
        return key

    def public_url(self, key: str, request_base: str) -> str:
        base = (self.public_base or request_base).rstrip("/")
        return f"{base}/uploads/{key}"


class S3Storage:
    """S3 兼容对象存储（R2 / TOS / MinIO）对接骨架。

    真实实现用 boto3/aioboto3 put_object 上传，凭证获取见 docs/deployment.md。
    凭证未配齐时不会被工厂选中（自动回退 local），因此不影响现有功能。
    """

    name = "s3"

    def __init__(self) -> None:
        s = get_settings()
        self.endpoint_url = s.s3_endpoint_url
        self.region = s.s3_region
        self.bucket = s.s3_bucket
        self.access_key_id = s.s3_access_key_id
        self.secret_access_key = s.s3_secret_access_key
        self.public_base = s.s3_public_base_url

    @staticmethod
    def is_configured() -> bool:
        s = get_settings()
        return bool(
            s.s3_bucket and s.s3_access_key_id and s.s3_secret_access_key and s.s3_public_base_url
        )

    async def save(self, *, data: bytes, ext: str, content_type: str) -> str:
        # TODO(M6-real): boto3/aioboto3 client(endpoint_url, region, key/secret)
        #   .put_object(Bucket=bucket, Key=key, Body=data, ContentType=content_type)
        raise StorageNotConfigured("S3 对象存储上传尚未接入（占位）。请补齐凭证并实现 put_object。")

    def public_url(self, key: str, request_base: str) -> str:
        return f"{self.public_base.rstrip('/')}/{key}"


def get_storage() -> Storage:
    provider = get_settings().storage_provider
    if provider == "s3" and S3Storage.is_configured():
        return S3Storage()
    if provider == "local":
        return LocalStorage()
    # 默认（含 provider="db"）：数据库持久化存储，重部署不丢失。
    return DbStorage()
