from collections.abc import AsyncGenerator
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.core.config import get_settings


class Base(DeclarativeBase):
    pass


def _build_async_engine_url(raw: str) -> tuple[str, dict[str, Any]]:
    """规范化数据库连接串，使托管 Postgres（如 Neon）可直接用 asyncpg 连接。

    - `postgresql://` → `postgresql+asyncpg://`
    - asyncpg 不认识 `sslmode`/`channel_binding` 查询参数，剥离后改用 connect_args(ssl=True)
    """
    url = raw
    connect_args: dict[str, Any] = {}
    if url.startswith("postgresql://"):
        url = "postgresql+asyncpg://" + url[len("postgresql://") :]
    if "+asyncpg" in url:
        parts = urlsplit(url)
        query = dict(parse_qsl(parts.query))
        sslmode = query.pop("sslmode", None)
        query.pop("channel_binding", None)
        if sslmode is not None and sslmode != "disable":
            connect_args["ssl"] = True
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    return url, connect_args


settings = get_settings()
_engine_url, _connect_args = _build_async_engine_url(settings.database_url)
engine = create_async_engine(
    _engine_url, future=True, pool_pre_ping=True, connect_args=_connect_args
)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:
        yield session
