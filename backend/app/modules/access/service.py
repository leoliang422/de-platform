from __future__ import annotations

from dataclasses import dataclass

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.modules.access.models import (
    ACCESS_MODULES,
    MODULE_UNLOCK_MARKER,
    ModuleAccessLog,
)
from app.modules.access.schemas import ModuleAccessOut
from app.modules.points.service import PointsService
from app.modules.users.models import User


@dataclass
class RevealState:
    """一次"查看受限条目"的结果。"""

    granted: bool  # 是否可查看该条目内容
    consumed: bool  # 本次是否消耗了一个免费名额
    module_unlocked: bool
    free_used: int
    free_limit: int
    unlock_points: int


def _validate_module(module: str) -> None:
    if module not in ACCESS_MODULES:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="模块不存在")


class AccessService:
    """SQL / 面经 的模块级积分访问控制。

    规则：每个用户每个模块可免费查看 N 条；超出后一次性用积分解锁整个模块，此后全部可见。
    """

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.settings = get_settings()

    def unlock_points(self, module: str) -> int:
        if module == "sql":
            return self.settings.sql_module_unlock_points
        if module == "interview":
            return self.settings.interview_module_unlock_points
        return 0

    @property
    def free_limit(self) -> int:
        return self.settings.free_module_quota

    async def _module_unlocked(self, user_id: int, module: str) -> bool:
        stmt = select(ModuleAccessLog.id).where(
            ModuleAccessLog.user_id == user_id,
            ModuleAccessLog.module == module,
            ModuleAccessLog.item_id == MODULE_UNLOCK_MARKER,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none() is not None

    async def _free_used(self, user_id: int, module: str) -> int:
        stmt = select(func.count()).where(
            ModuleAccessLog.user_id == user_id,
            ModuleAccessLog.module == module,
            ModuleAccessLog.item_id != MODULE_UNLOCK_MARKER,
        )
        return int((await self.db.execute(stmt)).scalar_one())

    async def _has_item(self, user_id: int, module: str, item_id: int) -> bool:
        stmt = select(ModuleAccessLog.id).where(
            ModuleAccessLog.user_id == user_id,
            ModuleAccessLog.module == module,
            ModuleAccessLog.item_id == item_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none() is not None

    def _is_privileged(self, user: User | None, author_id: int | None) -> bool:
        if user is None:
            return False
        return user.role == "admin" or (author_id is not None and author_id == user.id)

    async def can_view(
        self, user: User | None, module: str, item_id: int, author_id: int | None
    ) -> bool:
        """只读判断某条内容当前是否可见（不消耗免费名额）。"""
        _validate_module(module)
        if self._is_privileged(user, author_id):
            return True
        if user is None:
            return False
        if await self._module_unlocked(user.id, module):
            return True
        return await self._has_item(user.id, module, item_id)

    async def reveal(
        self, user: User, module: str, item_id: int, author_id: int | None
    ) -> RevealState:
        """查看一条受限内容：已可见则直接放行；否则在免费额度内消耗一次，超额则拒绝。"""
        _validate_module(module)
        unlocked = await self._module_unlocked(user.id, module)
        used = await self._free_used(user.id, module)
        price = self.unlock_points(module)

        if self._is_privileged(user, author_id) or unlocked or await self._has_item(
            user.id, module, item_id
        ):
            return RevealState(
                granted=True,
                consumed=False,
                module_unlocked=unlocked,
                free_used=used,
                free_limit=self.free_limit,
                unlock_points=price,
            )

        if used < self.free_limit:
            self.db.add(ModuleAccessLog(user_id=user.id, module=module, item_id=item_id))
            await self.db.commit()
            return RevealState(
                granted=True,
                consumed=True,
                module_unlocked=False,
                free_used=used + 1,
                free_limit=self.free_limit,
                unlock_points=price,
            )

        return RevealState(
            granted=False,
            consumed=False,
            module_unlocked=False,
            free_used=used,
            free_limit=self.free_limit,
            unlock_points=price,
        )

    async def summary(self, user: User | None, module: str) -> ModuleAccessOut:
        _validate_module(module)
        price = self.unlock_points(module)
        if user is None:
            return ModuleAccessOut(
                module=module,
                unlocked=False,
                free_used=0,
                free_limit=self.free_limit,
                unlock_points=price,
            )
        # 管理员不受免费额度限制，视为已解锁（无限查看）。
        if user.role == "admin":
            return ModuleAccessOut(
                module=module,
                unlocked=True,
                free_used=0,
                free_limit=self.free_limit,
                unlock_points=price,
            )
        return ModuleAccessOut(
            module=module,
            unlocked=await self._module_unlocked(user.id, module),
            free_used=await self._free_used(user.id, module),
            free_limit=self.free_limit,
            unlock_points=price,
        )

    async def unlock_module(self, user: User, module: str) -> ModuleUnlockOutcome:
        _validate_module(module)
        if await self._module_unlocked(user.id, module):
            return ModuleUnlockOutcome(already=True)

        price = self.unlock_points(module)
        if user.points_balance < price:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="积分不足")

        row = ModuleAccessLog(user_id=user.id, module=module, item_id=MODULE_UNLOCK_MARKER)
        self.db.add(row)
        await self.db.flush()

        await PointsService(self.db).grant(
            user_id=user.id,
            delta=-price,
            reason=f"解锁模块：{module}",
            ref_type="module_unlock",
            ref_id=row.id,
        )
        await self.db.commit()
        return ModuleUnlockOutcome(already=False)


@dataclass
class ModuleUnlockOutcome:
    already: bool
