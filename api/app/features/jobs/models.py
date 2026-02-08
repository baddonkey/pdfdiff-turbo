import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class JobStatus(str, enum.Enum):
    created = "created"
    running = "running"
    completed = "completed"
    failed = "failed"
    cancelled = "cancelled"


class PageStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    failed = "failed"
    incompatible_size = "incompatible_size"
    missing = "missing"


class TextStatus(str, enum.Enum):
    pending = "pending"
    running = "running"
    done = "done"
    missing = "missing"
    failed = "failed"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.created, nullable=False)
    set_a_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    set_b_label: Mapped[str | None] = mapped_column(String(255), nullable=True)
    has_diffs: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class JobFile(Base):
    __tablename__ = "job_files"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    relative_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    set_a_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    set_b_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    missing_in_set_a: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    missing_in_set_b: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    has_diffs: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    text_status: Mapped[TextStatus] = mapped_column(Enum(TextStatus), default=TextStatus.pending, nullable=False)
    text_set_a_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    text_set_b_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    text_error: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class JobPageResult(Base):
    __tablename__ = "job_page_results"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    job_file_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("job_files.id", ondelete="CASCADE"), index=True)
    page_index: Mapped[int] = mapped_column(nullable=False)
    status: Mapped[PageStatus] = mapped_column(Enum(PageStatus), default=PageStatus.pending, nullable=False)
    diff_score: Mapped[float | None] = mapped_column(nullable=True)
    task_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
    incompatible_size: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    missing_in_set_a: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    missing_in_set_b: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    overlay_svg_path: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    error_message: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
