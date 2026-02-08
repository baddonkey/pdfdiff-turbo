from datetime import datetime
from pydantic import BaseModel, EmailStr


class RegisterCommand(BaseModel):
    email: EmailStr
    password: str
    captcha_token: str | None = None
    captcha_action: str | None = None


class LoginCommand(BaseModel):
    email: EmailStr
    password: str


class RefreshCommand(BaseModel):
    refresh_token: str


class LogoutCommand(BaseModel):
    refresh_token: str


class ChangePasswordCommand(BaseModel):
    current_password: str
    new_password: str


class TokenPairMessage(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class UserMessage(BaseModel):
    id: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime
