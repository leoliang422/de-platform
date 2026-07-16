import datetime as dt

from pydantic import BaseModel, ConfigDict


class LedgerEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    delta: int
    reason: str
    ref_type: str
    ref_id: int
    created_at: dt.datetime


class PointsOverview(BaseModel):
    balance: int
    ledger: list[LedgerEntryOut]
