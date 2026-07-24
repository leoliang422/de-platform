from typing import Literal

from pydantic import BaseModel, ConfigDict, field_validator


class SqlQuestionListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    category_id: int | None = None
    title: str
    difficulty: str
    tags: list[str] = []
    # 当前登录用户的做题进度：None=未做 / done=已做 / mastered=已掌握。
    my_status: str | None = None

    @field_validator("tags", mode="before")
    @classmethod
    def split_tags(cls, v: object) -> list[str]:
        if isinstance(v, str):
            return [t.strip() for t in v.split(",") if t.strip()]
        return v if isinstance(v, list) else []


class SqlProgressIn(BaseModel):
    status: Literal["none", "done", "mastered"]


class SqlQuestionDetail(SqlQuestionListItem):
    # 题目级门控：未获授权时题干与答案都不返回（locked=True）。
    prompt_md: str = ""
    answer_md: str | None = None
    locked: bool = False
    # 访问状态（供前端展示"剩余免费名额 / 解锁模块"）。
    module_unlocked: bool = False
    free_used: int = 0
    free_limit: int = 0
    unlock_points: int = 0
