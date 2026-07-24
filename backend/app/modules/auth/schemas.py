from pydantic import BaseModel, EmailStr, Field


class RegisterIn(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6, max_length=128)
    nickname: str = Field(min_length=1, max_length=50)
    # 邮箱验证码：仅当 EMAIL_VERIFICATION_REQUIRED=true 时校验；否则忽略（向后兼容）。
    code: str | None = None


class SendEmailCodeIn(BaseModel):
    email: EmailStr


class SendEmailCodeOut(BaseModel):
    sent: bool = True
    # 仅 mock 邮件通道下返回，便于无 SMTP 时自测/自动填入；真实 SMTP 通道为 None。
    dev_code: str | None = None


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class RefreshIn(BaseModel):
    refresh_token: str


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class ForgotPasswordIn(BaseModel):
    email: EmailStr


class ForgotPasswordOut(BaseModel):
    # 不泄露邮箱是否注册：无论如何都返回 sent=True。
    # reset_token 仅在 mock 邮件通道下返回，便于本地自测（生产用真实 SMTP 时为 None）。
    sent: bool = True
    reset_token: str | None = None


class ResetPasswordIn(BaseModel):
    token: str = Field(min_length=1)
    new_password: str = Field(min_length=6, max_length=128)
