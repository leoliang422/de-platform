import datetime as dt
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


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


class PointsPackage(BaseModel):
    amount: int = Field(gt=0, le=100000, description="人民币金额（元）")
    points: int = Field(gt=0, le=1000000, description="到账积分")


class PointsConfigOut(BaseModel):
    """系统配置 · 积分规则（当前生效值）。"""

    free_module_quota: int
    sql_module_unlock_points: int
    interview_module_unlock_points: int
    reward_knowledge: int
    reward_sql: int
    reward_interview: int
    reward_project: int
    packages: list[PointsPackage]


class PointsConfigIn(BaseModel):
    free_module_quota: int = Field(ge=0, le=100000)
    sql_module_unlock_points: int = Field(ge=0, le=1000000)
    interview_module_unlock_points: int = Field(ge=0, le=1000000)
    reward_knowledge: int = Field(ge=0, le=1000000)
    reward_sql: int = Field(ge=0, le=1000000)
    reward_interview: int = Field(ge=0, le=1000000)
    reward_project: int = Field(ge=0, le=1000000)
    packages: list[PointsPackage] = Field(default_factory=list, max_length=20)
