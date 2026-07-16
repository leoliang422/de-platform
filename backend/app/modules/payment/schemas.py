import datetime as dt
from typing import Literal

from pydantic import BaseModel, ConfigDict

PayableType = Literal["project", "knowledge"]
UnlockMethod = Literal["cash", "points"]


class UnlockIn(BaseModel):
    content_type: PayableType
    content_id: int
    method: UnlockMethod


class EntitlementOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    content_type: str
    content_id: int
    source: str
    created_at: dt.datetime


class UnlockResult(BaseModel):
    entitlement: EntitlementOut
    balance: int
    already_unlocked: bool = False
