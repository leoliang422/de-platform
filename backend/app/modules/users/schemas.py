import datetime as dt

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    nickname: str
    avatar_url: str | None = None
    bio: str | None = None
    job_title: str | None = None
    role: str
    points_balance: int
    created_at: dt.datetime


class UserUpdateIn(BaseModel):
    """个人资料编辑；仅提交需要修改的字段。"""

    nickname: str | None = Field(default=None, min_length=1, max_length=50)
    avatar_url: str | None = Field(default=None, max_length=500)
    bio: str | None = Field(default=None, max_length=500)
    job_title: str | None = Field(default=None, max_length=100)


class ChangePasswordIn(BaseModel):
    old_password: str = Field(min_length=1, max_length=128)
    new_password: str = Field(min_length=6, max_length=128)


class PublicUserOut(BaseModel):
    """公开的用户资料（他人可见，不含邮箱等敏感信息）。"""

    model_config = ConfigDict(from_attributes=True)

    id: int
    nickname: str
    avatar_url: str | None = None
    bio: str | None = None
    job_title: str | None = None
    created_at: dt.datetime
