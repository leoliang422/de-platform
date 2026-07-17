from __future__ import annotations

import json
import uuid
from collections.abc import Mapping
from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol, runtime_checkable

from app.core.config import get_settings


@dataclass
class ChargeResult:
    """下单结果。

    - ``settled=True``：同步结算完成（如 mock），调用方可立即发放权益。
    - ``settled=False``：异步支付（微信/支付宝），需引导用户到 ``pay_url`` / 扫
      ``qr_code`` 付款，最终以 webhook 回调结算。
    """

    provider_ref: str
    settled: bool = False
    pay_url: str | None = None
    qr_code: str | None = None


@dataclass
class CallbackResult:
    """支付网关异步回调（webhook）解析结果。"""

    order_id: int
    success: bool
    provider_ref: str | None = None


class PaymentNotConfigured(RuntimeError):
    """真实支付通道未配齐凭证时抛出，工厂据此回退到 mock。"""


@runtime_checkable
class PaymentProvider(Protocol):
    name: str

    async def create_charge(
        self, *, amount: Decimal, order_id: int, subject: str
    ) -> ChargeResult: ...

    def parse_callback(self, headers: Mapping[str, str], body: bytes) -> CallbackResult: ...

    def callback_ack(self, success: bool) -> str: ...


class MockProvider:
    """始终成功的模拟支付通道（本地/演示默认）。

    - ``create_charge`` 同步结算，行为与 M3 一致。
    - ``parse_callback`` 支持解析 ``{"order_id": N, "success": true}`` 形式的回调，
      便于对异步结算逻辑做端到端测试。
    """

    name = "mock"

    async def create_charge(self, *, amount: Decimal, order_id: int, subject: str) -> ChargeResult:
        return ChargeResult(
            provider_ref=f"mock_{order_id}_{uuid.uuid4().hex[:8]}",
            settled=True,
        )

    def parse_callback(self, headers: Mapping[str, str], body: bytes) -> CallbackResult:
        data = json.loads(body or b"{}")
        return CallbackResult(
            order_id=int(data["order_id"]),
            success=bool(data.get("success", True)),
            provider_ref=data.get("provider_ref"),
        )

    def callback_ack(self, success: bool) -> str:
        return "success"


class WechatPayProvider:
    """微信支付（Native 扫码）对接骨架。

    真实下单需调用微信支付 v3 「Native 下单」接口拿到 ``code_url`` 生成二维码，
    并在回调里用商户 APIv3 密钥验签。凭证获取见 ``docs/deployment.md`` §支付接入。
    未配齐凭证时不会被工厂选中（自动回退 mock），因此不影响现有功能。
    """

    name = "wechat"

    def __init__(self) -> None:
        s = get_settings()
        self.app_id = s.wechat_app_id
        self.mch_id = s.wechat_mch_id
        self.api_v3_key = s.wechat_api_v3_key
        self.cert_serial = s.wechat_cert_serial
        self.private_key_path = s.wechat_private_key_path
        self.notify_url = s.wechat_notify_url

    @staticmethod
    def is_configured() -> bool:
        s = get_settings()
        return bool(
            s.wechat_app_id
            and s.wechat_mch_id
            and s.wechat_api_v3_key
            and s.wechat_cert_serial
            and s.wechat_private_key_path
            and s.wechat_notify_url
        )

    async def create_charge(self, *, amount: Decimal, order_id: int, subject: str) -> ChargeResult:
        # TODO(M5-real): 调用微信支付 v3 Native 下单接口：
        #   POST https://api.mch.weixin.qq.com/v3/pay/transactions/native
        #   body: {appid, mchid, description=subject, out_trade_no=str(order_id),
        #          notify_url, amount:{total: int(amount*100), currency:"CNY"}}
        #   使用 cert_serial + private_key 生成 Authorization 签名，返回 code_url。
        raise PaymentNotConfigured(
            "微信支付真实下单尚未接入（占位）。请在 docs/deployment.md 补齐凭证并实现 v3 下单。"
        )

    def parse_callback(self, headers: Mapping[str, str], body: bytes) -> CallbackResult:
        # TODO(M5-real): 用 Wechatpay-Signature/Timestamp/Nonce + api_v3_key 验签，
        #   AES-GCM 解密 resource，取 out_trade_no 作为 order_id、trade_state 判成功。
        raise PaymentNotConfigured("微信支付回调验签尚未接入（占位）。")

    def callback_ack(self, success: bool) -> str:
        # 微信要求返回 JSON；失败返回非 SUCCESS 触发重试。
        code = "SUCCESS" if success else "FAIL"
        return json.dumps({"code": code, "message": "" if success else "处理失败"})


class AlipayProvider:
    """支付宝（电脑/手机网站支付）对接骨架。

    真实下单可用 ``alipay.trade.page.pay`` 生成支付跳转链接，回调用支付宝公钥验签。
    凭证获取见 ``docs/deployment.md`` §支付接入。未配齐凭证时自动回退 mock。
    """

    name = "alipay"

    def __init__(self) -> None:
        s = get_settings()
        self.app_id = s.alipay_app_id
        self.private_key = s.alipay_private_key
        self.public_key = s.alipay_public_key
        self.gateway = s.alipay_gateway
        self.notify_url = s.alipay_notify_url

    @staticmethod
    def is_configured() -> bool:
        s = get_settings()
        return bool(
            s.alipay_app_id
            and s.alipay_private_key
            and s.alipay_public_key
            and s.alipay_gateway
            and s.alipay_notify_url
        )

    async def create_charge(self, *, amount: Decimal, order_id: int, subject: str) -> ChargeResult:
        # TODO(M5-real): 用 app_id + private_key 组装 alipay.trade.page.pay 参数并签名(RSA2)，
        #   拼成 gateway?<biz_content...&sign=...> 作为 pay_url，out_trade_no=str(order_id)。
        raise PaymentNotConfigured(
            "支付宝真实下单尚未接入（占位）。请在 docs/deployment.md 补齐凭证并实现 page.pay。"
        )

    def parse_callback(self, headers: Mapping[str, str], body: bytes) -> CallbackResult:
        # TODO(M5-real): 解析表单回调，用 alipay_public_key 验签，取 out_trade_no、
        #   trade_status ∈ {TRADE_SUCCESS, TRADE_FINISHED} 判成功。
        raise PaymentNotConfigured("支付宝回调验签尚未接入（占位）。")

    def callback_ack(self, success: bool) -> str:
        # 支付宝要求异步通知处理成功后返回纯文本 "success"。
        return "success" if success else "fail"


def get_payment_provider() -> PaymentProvider:
    """按 ``PAYMENT_PROVIDER`` 分派；真实通道凭证未配齐时安全回退到 mock。"""
    provider = get_settings().payment_provider
    if provider == "wechat" and WechatPayProvider.is_configured():
        return WechatPayProvider()
    if provider == "alipay" and AlipayProvider.is_configured():
        return AlipayProvider()
    return MockProvider()
