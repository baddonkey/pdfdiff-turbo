from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field

from app.features.reports.models import ReportStatus, ReportType


class ReportCreateCommand(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    source_job_id: str = Field(..., min_length=1)
    report_type: ReportType = Field(..., alias="type")


class ReportMessage(BaseModel):
    id: str
    source_job_id: str
    report_type: ReportType
    status: ReportStatus
    progress: int
    output_filename: str | None = None
    error: str | None = None
    created_at: datetime
    updated_at: datetime


class ReportEventMessage(BaseModel):
    report_id: str
    source_job_id: str
    report_type: ReportType
    status: ReportStatus
    progress: int
    output_filename: str | None = None
    error: str | None = None


