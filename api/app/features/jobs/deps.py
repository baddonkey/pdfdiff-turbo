from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.features.jobs.repository import JobFileRepository, JobPageResultRepository, JobRepository
from app.features.jobs.service import JobService


def get_job_repository(session: AsyncSession = Depends(get_session)) -> JobRepository:
    return JobRepository(session)


def get_job_file_repository(session: AsyncSession = Depends(get_session)) -> JobFileRepository:
    return JobFileRepository(session)


def get_job_page_result_repository(session: AsyncSession = Depends(get_session)) -> JobPageResultRepository:
    return JobPageResultRepository(session)


def get_job_service(
    session: AsyncSession = Depends(get_session),
    job_repo: JobRepository = Depends(get_job_repository),
    file_repo: JobFileRepository = Depends(get_job_file_repository),
    page_repo: JobPageResultRepository = Depends(get_job_page_result_repository),
) -> JobService:
    return JobService(session, job_repo, file_repo, page_repo)
