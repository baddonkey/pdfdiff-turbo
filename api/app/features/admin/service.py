from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.admin.repository import AdminRepository
from app.features.admin.schemas import AdminJobMessage, AdminUserMessage, AdminUserUpdateCommand
from app.features.auth.models import UserRole
from app.features.jobs.service import JobService


class AdminService:
    def __init__(self, session: AsyncSession, repo: AdminRepository, job_service: JobService):
        self._session = session
        self._repo = repo
        self._job_service = job_service

    async def list_jobs(self) -> list[AdminJobMessage]:
        jobs = await self._repo.list_jobs()
        return [
            AdminJobMessage(
                id=str(job.id),
                user_id=str(job.user_id),
                status=job.status.value,
                created_at=job.created_at,
            )
            for job in jobs
        ]

    async def cancel_job(self, job_id: str) -> dict:
        job = await self._repo.get_job(job_id)
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
        await self._job_service.cancel_job(job)
        return {"status": "ok"}

    async def list_users(self) -> list[AdminUserMessage]:
        users = await self._repo.list_users()
        return [
            AdminUserMessage(
                id=str(user.id),
                email=user.email,
                role=user.role.value,
                is_active=user.is_active,
                max_files_per_set=user.max_files_per_set,
                max_upload_mb=user.max_upload_mb,
                max_pages_per_job=user.max_pages_per_job,
                max_jobs_per_user_per_day=user.max_jobs_per_user_per_day,
                created_at=user.created_at,
            )
            for user in users
        ]

    async def update_user(self, user_id: str, command: AdminUserUpdateCommand) -> AdminUserMessage:
        user = await self._repo.get_user(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if command.role is not None:
            if command.role not in {UserRole.admin.value, UserRole.user.value}:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid role")
            user.role = UserRole(command.role)
        if command.is_active is not None:
            user.is_active = command.is_active
        if command.max_files_per_set is not None:
            if command.max_files_per_set < 1:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="max_files_per_set must be >= 1")
            user.max_files_per_set = command.max_files_per_set
        if command.max_upload_mb is not None:
            if command.max_upload_mb < 1:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="max_upload_mb must be >= 1")
            user.max_upload_mb = command.max_upload_mb
        if command.max_pages_per_job is not None:
            if command.max_pages_per_job < 1:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="max_pages_per_job must be >= 1")
            user.max_pages_per_job = command.max_pages_per_job
        if command.max_jobs_per_user_per_day is not None:
            if command.max_jobs_per_user_per_day < 1:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="max_jobs_per_user_per_day must be >= 1")
            user.max_jobs_per_user_per_day = command.max_jobs_per_user_per_day
        await self._session.commit()
        return AdminUserMessage(
            id=str(user.id),
            email=user.email,
            role=user.role.value,
            is_active=user.is_active,
            max_files_per_set=user.max_files_per_set,
            max_upload_mb=user.max_upload_mb,
            max_pages_per_job=user.max_pages_per_job,
            max_jobs_per_user_per_day=user.max_jobs_per_user_per_day,
            created_at=user.created_at,
        )
