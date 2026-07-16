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
    answer_md: str
