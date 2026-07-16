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
