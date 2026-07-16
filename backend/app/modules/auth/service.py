from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.modules.auth.schemas import LoginIn, RegisterIn
from app.modules.users.models import User
from app.modules.users.repository import UserRepository


class AuthService:
    def __init__(self, db: AsyncSession) -> None:
        self.users = UserRepository(db)

    async def register(self, data: RegisterIn) -> User:
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
