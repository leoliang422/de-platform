import datetime as dt
from typing import Any

from pydantic import BaseModel, ConfigDict


class AdminSubmissionOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    target_type: str
    title: str
    raw_content: str
    processed_md: str | None = None
    extra: dict[str, Any]
    status: str
    reject_reason: str | None = None
    published_ref_id: int | None = None
    created_at: dt.datetime


class AdminUserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: str
    nickname: str
    role: str
    points_balance: int
    created_at: dt.datetime


class AdminUserUpdate(BaseModel):
    role: str | None = None  # user | admin
    # 二选一：set_points 绝对值 / delta_points 增减；均写入积分账本
    set_points: int | None = None
    delta_points: int | None = None
    reason: str | None = None


class ModuleAccessItem(BaseModel):
    module: str  # sql | interview
    label: str
    unlocked: bool


class ProjectAccessItem(BaseModel):
    id: int
    title: str
    access_type: str
    unlocked: bool


class AdminUserAccessOut(BaseModel):
    """某用户的权限范围：模块级解锁 + 项目解锁清单。"""

    user_id: int
    modules: list[ModuleAccessItem]
    projects: list[ProjectAccessItem]


class AdminRechargeOrderOut(BaseModel):
    """管理员视角的充值订单（附用户信息，便于核对到账）。"""

    id: int
    user_id: int
    user_nickname: str
    user_email: str
    amount_cash: float
    points_delta: int | None = None
    note: str | None = None
    status: str
    created_at: dt.datetime


class RechargeQrOut(BaseModel):
    url: str


class RechargeQrIn(BaseModel):
    url: str
