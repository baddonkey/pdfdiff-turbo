from datetime import datetime
from pydantic import BaseModel

from app.features.reports.models import ReportStatus


class ReportCreateCommand(BaseModel):
    source_job_id: str


class ReportMessage(BaseModel):
    id: str
    source_job_id: str
    status: ReportStatus
    progress: int
    visual_filename: str | None = None
    text_filename: str | None = None
    bundle_filename: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class ReportEventMessage(BaseModel):
    report_id: str
    source_job_id: str
    status: ReportStatus
    progress: int
    visual_filename: str | None = None
    text_filename: str | None = None
    bundle_filename: str | None = None
    error: str | None = None


