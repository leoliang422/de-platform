from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.settings.models import SiteSetting

# 站点级可编辑配置的 key（后台系统配置写入，运行时优先于环境变量默认值）。
KEY_FREE_QUOTA = "free_module_quota"
KEY_SQL_UNLOCK = "sql_module_unlock_points"
KEY_INTERVIEW_UNLOCK = "interview_module_unlock_points"
KEY_RECHARGE_PACKAGES = "recharge_packages"
KEY_RECHARGE_QR = "recharge_qr_url"


async def get_setting(db: AsyncSession, key: str) -> str | None:
    row = await db.get(SiteSetting, key)
    return row.value if row is not None else None


async def get_int_setting(db: AsyncSession, key: str, default: int) -> int:
    """读取整数配置；无值或非法时回退默认值。"""
    raw = await get_setting(db, key)
    if raw is None:
        return default
    try:
        return int(raw.strip())
    except (ValueError, AttributeError):
        return default


async def set_setting(db: AsyncSession, key: str, value: str) -> None:
    row = await db.get(SiteSetting, key)
    if row is None:
        db.add(SiteSetting(key=key, value=value))
    else:
        row.value = value
    await db.commit()
