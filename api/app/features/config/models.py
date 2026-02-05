from datetime import datetime

from sqlalchemy import Boolean, DateTime, Integer
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class AppConfig(Base):
    __tablename__ = "app_config"

    id: Mapped[int] = mapped_column(primary_key=True, default=1)
    allow_registration: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    enable_dropzone: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    max_files_per_set: Mapped[int] = mapped_column(Integer, default=1000, nullable=False)
    max_upload_mb: Mapped[int] = mapped_column(Integer, default=10, nullable=False)
    max_pages_per_job: Mapped[int] = mapped_column(Integer, default=10000, nullable=False)
    max_jobs_per_user_per_day: Mapped[int] = mapped_column(Integer, default=20, nullable=False)
    file_retention_hours: Mapped[int] = mapped_column(Integer, default=24, nullable=False)
    job_retention_days: Mapped[int] = mapped_column(Integer, default=7, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
