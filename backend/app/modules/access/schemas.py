from pydantic import BaseModel


class ModuleAccessOut(BaseModel):
    """模块访问状态：是否已解锁、已用/可用免费名额、解锁所需积分。"""

    module: str
    unlocked: bool
    free_used: int
    free_limit: int
    unlock_points: int


class ModuleUnlockResult(ModuleAccessOut):
    balance: int
    already: bool = False
