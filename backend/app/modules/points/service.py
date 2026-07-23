from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.points.models import PointLedger
from app.modules.points.repository import PointsRepository
from app.modules.settings.service import REWARD_KEY_BY_TYPE, get_int_setting
from app.modules.users.repository import UserRepository

# 各类内容审核通过后的积分奖励默认值（后台「系统配置」可覆盖，见 docs/points-and-payment.md）。
POINTS_BY_TYPE: dict[str, int] = {
    "knowledge": 10,
    "sql": 10,
    "interview": 20,
    "project": 100,
}


async def reward_points(db: AsyncSession, target_type: str) -> int:
    """某类投稿审核通过后的奖励积分：优先取后台配置，回退默认值。"""
    default = POINTS_BY_TYPE.get(target_type, 0)
    key = REWARD_KEY_BY_TYPE.get(target_type)
    if key is None:
        return default
    return await get_int_setting(db, key, default)


class PointsService:
    """积分发放/消耗。方法只 flush 不 commit，事务边界交由调用方。"""

    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = PointsRepository(db)
        self.users = UserRepository(db)

    async def grant(
        self, user_id: int, delta: int, reason: str, ref_type: str, ref_id: int
    ) -> PointLedger | None:
        """幂等发放：同一 (ref_type, ref_id) 只记一次，返回 None 表示已发放过。"""
        existing = await self.repo.get_by_ref(ref_type, ref_id)
        if existing is not None:
            return None

        entry = PointLedger(
            user_id=user_id,
            delta=delta,
            reason=reason,
            ref_type=ref_type,
            ref_id=ref_id,
        )
        self.repo.add(entry)

        user = await self.users.get_by_id(user_id)
        if user is not None:
            user.points_balance += delta

        await self.db.flush()
        return entry
