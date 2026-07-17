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
    # 同步结算（积分 / mock 现金）返回 entitlement；异步支付（微信/支付宝）返回
    # status="pending" + pay_url/qr_code，entitlement 留空，待回调后再解锁。
    status: str = "paid"
    entitlement: EntitlementOut | None = None
    balance: int
    already_unlocked: bool = False
    order_id: int | None = None
    pay_url: str | None = None
    qr_code: str | None = None
