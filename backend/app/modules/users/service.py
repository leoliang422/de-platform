from __future__ import annotations

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import hash_password, verify_password
from app.modules.users.models import User
from app.modules.users.repository import UserRepository
from app.modules.users.schemas import ChangePasswordIn, UserUpdateIn


class UserService:
    def __init__(self, db: AsyncSession) -> None:
        self.db = db
        self.repo = UserRepository(db)

    async def update_profile(self, user: User, data: UserUpdateIn) -> User:
        fields = data.model_dump(exclude_unset=True)
        for key, value in fields.items():
            setattr(user, key, value)
        await self.db.commit()
        await self.db.refresh(user)
        return user

    async def change_password(self, user: User, data: ChangePasswordIn) -> None:
        if not verify_password(data.old_password, user.password_hash):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="原密码不正确")
        if verify_password(data.new_password, user.password_hash):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST, detail="新密码不能与原密码相同"
            )
        user.password_hash = hash_password(data.new_password)
        await self.db.commit()
