from pydantic import BaseModel


class AppConfigMessage(BaseModel):
    allow_registration: bool
    enable_dropzone: bool
    max_files_per_set: int
    max_upload_mb: int
    max_pages_per_job: int
    max_jobs_per_user_per_day: int
    file_retention_hours: int
    job_retention_days: int
    recaptcha_site_key: str | None = None


class AppConfigUpdateCommand(BaseModel):
    allow_registration: bool | None = None
    enable_dropzone: bool | None = None
    max_files_per_set: int | None = None
    max_upload_mb: int | None = None
    max_pages_per_job: int | None = None
    max_jobs_per_user_per_day: int | None = None
    file_retention_hours: int | None = None
    job_retention_days: int | None = None
