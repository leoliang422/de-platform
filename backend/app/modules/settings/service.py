from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.settings.models import SiteSetting


async def get_setting(db: AsyncSession, key: str) -> str | None:
    row = await db.get(SiteSetting, key)
    return row.value if row is not None else None


async def set_setting(db: AsyncSession, key: str, value: str) -> None:
    row = await db.get(SiteSetting, key)
    if row is None:
        db.add(SiteSetting(key=key, value=value))
    else:
        row.value = value
    await db.commit()
