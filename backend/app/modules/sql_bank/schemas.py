from pydantic import BaseModel, ConfigDict, field_validator


class SqlQuestionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int | None = None
    title: str
    difficulty: str
    tags: list[str] = []

    @field_validator("tags", mode="before")
    @classmethod
    def split_tags(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v if isinstance(v, list) else []


class SqlQuestionDetail(SqlQuestionListItem):
    prompt_md: str
    # 题干始终可见；答案受模块级积分门控，未获授权时为 None。
    answer_md: str | None = None
    answer_locked: bool = False
    # 访问状态（供前端展示"剩余免费名额 / 解锁模块"）。
    module_unlocked: bool = False
    free_used: int = 0
    free_limit: int = 0
    unlock_points: int = 0
