from __future__ import annotations

import logging
from typing import Protocol, runtime_checkable

from app.core.config import get_settings

logger = logging.getLogger(__name__)


class EmailNotConfigured(RuntimeError):
    """真实 SMTP 未配齐时抛出，工厂据此回退 mock。"""


@runtime_checkable
class EmailSender(Protocol):
    name: str

    async def send(self, *, to: str, subject: str, body: str) -> None: ...


class MockEmailSender:
    """不真正发信，仅记录日志（本地/演示默认）。"""

    name = "mock"

    async def send(self, *, to: str, subject: str, body: str) -> None:
        logger.info("[MockEmail] to=%s subject=%s\n%s", to, subject, body)


class SmtpEmailSender:
    """SMTP 发信对接骨架；凭证获取见 docs/deployment.md。

    未配齐凭证时不会被工厂选中（自动回退 mock），因此不影响现有功能。
    """

    name = "smtp"

    def __init__(self) -> None:
        s = get_settings()
        self.host = s.smtp_host
        self.port = s.smtp_port
        self.user = s.smtp_user
        self.password = s.smtp_password
        self.sender = s.smtp_from or s.smtp_user
        self.use_tls = s.smtp_use_tls

    @staticmethod
    def is_configured() -> bool:
        s = get_settings()
        has_from = bool(s.smtp_from or s.smtp_user)
        return bool(s.smtp_host and s.smtp_user and s.smtp_password and has_from)

    async def send(self, *, to: str, subject: str, body: str) -> None:
        # TODO(M6-real): 用 aiosmtplib 或线程内 smtplib 发送：
        #   msg = EmailMessage(); msg["From"]=self.sender; msg["To"]=to; msg["Subject"]=subject
        #   msg.set_content(body); 通过 host/port + STARTTLS + 登录 user/password 发送。
        raise EmailNotConfigured("SMTP 发信尚未接入（占位）。请补齐凭证并实现发送逻辑。")


def get_email_sender() -> EmailSender:
    if get_settings().email_provider == "smtp" and SmtpEmailSender.is_configured():
        return SmtpEmailSender()
    return MockEmailSender()
