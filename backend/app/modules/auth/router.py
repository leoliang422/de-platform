import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.security import create_access_token, create_refresh_token, decode_token
from app.modules.auth.schemas import (
    ForgotPasswordIn,
    ForgotPasswordOut,
    LoginIn,
    RefreshIn,
    RegisterIn,
    ResetPasswordIn,
    TokenPair,
)
from app.modules.auth.service import AuthService
from app.modules.users.schemas import UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


def _issue_tokens(user_id: int) -> TokenPair:
    return TokenPair(
        access_token=create_access_token(user_id),
        refresh_token=create_refresh_token(user_id),
    )


@router.post("/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
async def register(data: RegisterIn, db: AsyncSession = Depends(get_db)) -> UserOut:
    user = await AuthService(db).register(data)
    return UserOut.model_validate(user)


@router.post("/login", response_model=TokenPair)
async def login(data: LoginIn, db: AsyncSession = Depends(get_db)) -> TokenPair:
    user = await AuthService(db).authenticate(data)
    return _issue_tokens(user.id)


@router.post("/forgot-password", response_model=ForgotPasswordOut)
async def forgot_password(
    data: ForgotPasswordIn, db: AsyncSession = Depends(get_db)
) -> ForgotPasswordOut:
    return await AuthService(db).request_password_reset(data)


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(data: ResetPasswordIn, db: AsyncSession = Depends(get_db)) -> None:
    await AuthService(db).reset_password(data)


@router.post("/refresh", response_model=TokenPair)
async def refresh(data: RefreshIn) -> TokenPair:
    try:
        payload = decode_token(data.refresh_token)
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的刷新令牌"
        ) from exc
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="令牌类型错误")
    return _issue_tokens(int(payload["sub"]))
