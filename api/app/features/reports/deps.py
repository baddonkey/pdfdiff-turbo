from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.features.jobs.deps import get_job_repository
from app.features.jobs.repository import JobRepository
from app.features.reports.repository import ReportRepository
from app.features.reports.service import ReportService


def get_report_repository(session: AsyncSession = Depends(get_session)) -> ReportRepository:
    return ReportRepository(session)


def get_report_service(
    session: AsyncSession = Depends(get_session),
    report_repo: ReportRepository = Depends(get_report_repository),
    job_repo: JobRepository = Depends(get_job_repository),
) -> ReportService:
    return ReportService(session, report_repo, job_repo)
