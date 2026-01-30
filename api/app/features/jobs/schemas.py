from datetime import datetime
from pydantic import BaseModel


class JobCreatedMessage(BaseModel):
    id: str
    status: str
    created_at: datetime


class JobStartedMessage(BaseModel):
    id: str
    status: str


class JobStatusMessage(BaseModel):
    id: str
    status: str
    created_at: datetime


class JobSummaryMessage(BaseModel):
    id: str
    status: str
    created_at: datetime


class JobFileMessage(BaseModel):
    id: str
    relative_path: str
    set_a_path: str | None
    set_b_path: str | None
    missing_in_set_a: bool
    missing_in_set_b: bool
    created_at: datetime


class JobPageMessage(BaseModel):
    id: str
    page_index: int
    status: str
    diff_score: float | None
    incompatible_size: bool
    missing_in_set_a: bool
    missing_in_set_b: bool
    overlay_svg_path: str | None
    error_message: str | None
    created_at: datetime
