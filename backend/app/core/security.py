from __future__ import annotations

import datetime as dt

import bcrypt
import jwt

from app.core.config import get_settings

settings = get_settings()
ALGORITHM = "HS256"


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def _create_token(subject: int | str, expires_delta: dt.timedelta, token_type: str) -> str:
    now = dt.datetime.now(dt.UTC)
    payload = {
        "sub": str(subject),
        "type": token_type,
        "iat": now,
        "exp": now + expires_delta,
    }
    return jwt.encode(payload, settings.app_secret_key, algorithm=ALGORITHM)


def create_access_token(subject: int | str) -> str:
    return _create_token(
        subject, dt.timedelta(minutes=settings.access_token_expire_minutes), "access"
    )


def create_refresh_token(subject: int | str) -> str:
    return _create_token(subject, dt.timedelta(days=settings.refresh_token_expire_days), "refresh")


def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.app_secret_key, algorithms=[ALGORITHM])
