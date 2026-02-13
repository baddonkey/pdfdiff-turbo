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


class AdminUserDeleteMessage(BaseModel):
    status: str
    deleted_user_id: str
    deleted_jobs: int
    deleted_reports: int


class AdminStorageBucketMessage(BaseModel):
    name: str
    path: str
    bytes: int
    files: int
    pdf_files: int
    image_files: int


class AdminStorageStatsMessage(BaseModel):
    data_dir: str
    total_bytes: int | None
    used_bytes: int | None
    free_bytes: int | None
    buckets: list[AdminStorageBucketMessage]


class AdminCountsMessage(BaseModel):
    jobs_total: int
    jobs_by_status: dict[str, int]
    job_files_total: int
    pages_total: int
    pdf_files_total: int
    overlay_images_total: int


class AdminSystemStatsMessage(BaseModel):
    cpu_count: int | None
    load_avg_1m: float | None
    load_avg_5m: float | None
    load_avg_15m: float | None
    memory_total_bytes: int | None
    memory_used_bytes: int | None
    memory_available_bytes: int | None
    memory_used_percent: float | None


class AdminStatsMessage(BaseModel):
    generated_at: datetime
    storage: AdminStorageStatsMessage
    counts: AdminCountsMessage
    system: AdminSystemStatsMessage
