from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.features.admin.repository import AdminRepository
from app.features.admin.service import AdminService
from app.features.jobs.repository import JobFileRepository, JobPageResultRepository, JobRepository
from app.features.jobs.service import JobService


def get_admin_repository(session: AsyncSession = Depends(get_session)) -> AdminRepository:
    return AdminRepository(session)


def get_admin_service(
    session: AsyncSession = Depends(get_session),
    repo: AdminRepository = Depends(get_admin_repository),
) -> AdminService:
    job_repo = JobRepository(session)
    file_repo = JobFileRepository(session)
    page_repo = JobPageResultRepository(session)
    job_service = JobService(session, job_repo, file_repo, page_repo)
    return AdminService(session, repo, job_service)
