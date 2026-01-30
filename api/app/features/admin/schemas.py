from datetime import datetime
from pydantic import BaseModel, EmailStr


class AdminJobMessage(BaseModel):
    id: str
    user_id: str
    status: str
    created_at: datetime


class AdminUserMessage(BaseModel):
    id: str
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime


class AdminUserUpdateCommand(BaseModel):
    role: str | None = None
    is_active: bool | None = None
