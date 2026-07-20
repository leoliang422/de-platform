from pydantic import BaseModel, ConfigDict


class CompanyOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    logo_url: str | None = None


class InterviewQAOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    section: str
    order_index: int
    question: str
    answer: str


class InterviewCardOut(BaseModel):
    """一次完整面试（一张卡片）。"""

    id: int
    company_id: int
    title: str
    interview_type: str | None = None
    content_md: str
    author_id: int | None = None
    author_nickname: str = "匿名用户"
    author_avatar: str | None = None
    rounds_covered: list[str] = []
    qa: list[InterviewQAOut] = []
    # 模块级积分门控：locked=True 时 qa 被清空，需消耗免费名额或解锁模块后查看。
    locked: bool = False


class ModuleAccessInfo(BaseModel):
    unlocked: bool = False
    free_used: int = 0
    free_limit: int = 0
    unlock_points: int = 0


class InterviewTypeGroup(BaseModel):
    """按面经类型聚合。"""

    interview_type: str
    count: int
    posts: list[InterviewCardOut]


class InterviewByTypeResponse(BaseModel):
    """企业下按类型聚合的面经，附带当前用户的模块访问状态。"""

    groups: list[InterviewTypeGroup]
    access: ModuleAccessInfo
