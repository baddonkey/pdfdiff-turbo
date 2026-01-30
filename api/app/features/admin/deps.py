from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.features.admin.repository import AdminRepository
from app.features.admin.service import AdminService
from app.features.jobs.deps import get_job_service
from app.features.jobs.service import JobService


def get_admin_repository(session: AsyncSession = Depends(get_session)) -> AdminRepository:
    return AdminRepository(session)


def get_admin_service(
    session: AsyncSession = Depends(get_session),
    repo: AdminRepository = Depends(get_admin_repository),
    job_service: JobService = Depends(get_job_service),
) -> AdminService:
    return AdminService(session, repo, job_service)
