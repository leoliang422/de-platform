from __future__ import annotations

import datetime as dt
import hashlib
import logging
import secrets

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.security import hash_password, verify_password
from app.modules.auth.models import EmailVerificationCode, PasswordResetToken
from app.modules.auth.schemas import (
    ForgotPasswordIn,
    ForgotPasswordOut,
    LoginIn,
    RegisterIn,
    ResetPasswordIn,
    SendEmailCodeIn,
    SendEmailCodeOut,
)
from app.modules.mail.sender import get_email_sender
from app.modules.users.models import User
from app.modules.users.repository import UserRepository

logger = logging.getLogger(__name__)

RESET_TOKEN_TTL = dt.timedelta(minutes=30)


def _hash_token(raw: str) -> str:
    return hashlib.sha256(raw.encode()).hexdigest()


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.users = UserRepository(db)

    async def send_registration_code(self, data: SendEmailCodeIn) -> SendEmailCodeOut:
        """发送注册邮箱验证码。不泄露邮箱是否已注册（都返回 sent=True）。"""
        settings = get_settings()
        out = SendEmailCodeOut(sent=True)
        code = f"{secrets.randbelow(1_000_000):06d}"
        ttl = dt.timedelta(minutes=settings.email_code_ttl_minutes)
        record = EmailVerificationCode(
            email=data.email.lower(),
            code_hash=_hash_token(code),
            expires_at=dt.datetime.now(dt.UTC) + ttl,
        )
        self.db.add(record)
        await self.db.commit()

        sender = get_email_sender()
        try:
            await sender.send(
                to=data.email,
                subject="你的 DE Platform 注册验证码",
                body=(
                    f"你的注册验证码是：{code}\n"
                    f"{settings.email_code_ttl_minutes} 分钟内有效。若非本人操作请忽略。"
                ),
            )
        except Exception:  # noqa: BLE001 - 发信失败不应暴露给调用方
            logger.exception("发送注册验证码失败 email=%s", data.email)

        if sender.name == "mock":
            out.dev_code = code  # 无真实 SMTP 时便于自测/前端自动填入
        return out

    async def _consume_email_code(self, email: str, code: str | None) -> None:
        if not code:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="请先获取并填写邮箱验证码"
            )
        result = await self.db.execute(
            select(EmailVerificationCode)
            .where(
                EmailVerificationCode.email == email.lower(),
                EmailVerificationCode.code_hash == _hash_token(code),
            )
            .order_by(EmailVerificationCode.id.desc())
        )
        record = result.scalars().first()
        now = dt.datetime.now(dt.UTC)
        expires_at = record.expires_at if record else None
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=dt.UTC)
        if record is None or record.used_at is not None or expires_at is None or expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="验证码错误或已过期"
            )
        record.used_at = now

    async def register(self, data: RegisterIn) -> User:
        if get_settings().email_verification_required:
            await self._consume_email_code(data.email, data.code)
        if await self.users.get_by_email(data.email):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="邮箱已注册")
        user = User(
            email=data.email,
            password_hash=hash_password(data.password),
            nickname=data.nickname,
            role="user",
        )
        return await self.users.create(user)

    async def authenticate(self, data: LoginIn) -> User:
        user = await self.users.get_by_email(data.email)
        if user is None or not verify_password(data.password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="邮箱或密码错误")
        return user

    async def request_password_reset(self, data: ForgotPasswordIn) -> ForgotPasswordOut:
        """发起找回密码。无论邮箱是否注册都返回 sent=True，避免枚举用户。"""
        out = ForgotPasswordOut(sent=True)
        user = await self.users.get_by_email(data.email)
        if user is None:
            return out

        raw = secrets.token_urlsafe(32)
        token = PasswordResetToken(
            user_id=user.id,
            token_hash=_hash_token(raw),
            expires_at=dt.datetime.now(dt.UTC) + RESET_TOKEN_TTL,
        )
        self.db.add(token)
        await self.db.commit()

        settings = get_settings()
        link = f"{settings.frontend_base_url.rstrip('/')}/reset-password?token={raw}"
        sender = get_email_sender()
        try:
            await sender.send(
                to=user.email,
                subject="重置你的 DE Platform 密码",
                body=f"点击以下链接重置密码（30 分钟内有效）：\n{link}\n\n若非本人操作请忽略。",
            )
        except Exception:  # noqa: BLE001 - 发信失败不应暴露给调用方
            logger.exception("发送重置邮件失败 user_id=%s", user.id)

        if sender.name == "mock":
            out.reset_token = raw  # 本地自测便利；真实 SMTP 通道下不返回
        return out

    async def reset_password(self, data: ResetPasswordIn) -> None:
        token_hash = _hash_token(data.token)
        result = await self.db.execute(
            select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
        )
        token = result.scalar_one_or_none()
        now = dt.datetime.now(dt.UTC)
        expires_at = token.expires_at if token else None
        # SQLite 存的是 naive datetime，比较前统一按 UTC 处理。
        if expires_at is not None and expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=dt.UTC)
        if token is None or token.used_at is not None or expires_at is None or expires_at < now:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="重置链接无效或已过期"
            )

        user = await self.users.get_by_id(token.user_id)
        if user is None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户不存在")

        user.password_hash = hash_password(data.new_password)
        token.used_at = now
        await self.db.commit()
