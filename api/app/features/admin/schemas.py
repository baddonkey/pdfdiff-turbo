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
    max_files_per_set: int
    max_upload_mb: int
    max_pages_per_job: int
    max_jobs_per_user_per_day: int
    created_at: datetime


class AdminUserUpdateCommand(BaseModel):
    role: str | None = None
    is_active: bool | None = None
    max_files_per_set: int | None = None
    max_upload_mb: int | None = None
    max_pages_per_job: int | None = None
    max_jobs_per_user_per_day: int | None = None
