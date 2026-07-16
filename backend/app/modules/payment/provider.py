from __future__ import annotations

import uuid
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol

from app.core.config import get_settings


@dataclass
class PaymentResult:
    success: bool
    provider_ref: str


class PaymentProvider(Protocol):
    async def charge(self, amount: Decimal, order_id: int) -> PaymentResult: ...


class MockProvider:
    """始终成功的模拟支付通道，用于骨架演示。"""

    async def charge(self, amount: Decimal, order_id: int) -> PaymentResult:
        return PaymentResult(success=True, provider_ref=f"mock_{order_id}_{uuid.uuid4().hex[:8]}")


def get_payment_provider() -> PaymentProvider:
    # 目前仅 mock；真实通道（微信/支付宝/Stripe）后续在此按 env 分派，零改调用方。
    _ = get_settings().payment_provider
    return MockProvider()
