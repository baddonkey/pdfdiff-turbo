from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models import User
from app.features.jobs.models import Job
from app.features.reports.models import Report


class AdminRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_jobs(self) -> list[Job]:
        result = await self._session.execute(select(Job))
        return list(result.scalars().all())

    async def get_job(self, job_id: str) -> Optional[Job]:
        result = await self._session.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    async def list_users(self) -> list[User]:
        result = await self._session.execute(select(User))
        return list(result.scalars().all())

    async def get_user(self, user_id: str) -> Optional[User]:
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def list_job_ids_for_user(self, user_id: str) -> list[str]:
        result = await self._session.execute(select(Job.id).where(Job.user_id == user_id))
        return [str(job_id) for job_id in result.scalars().all()]

    async def list_report_ids_for_user(self, user_id: str) -> list[str]:
        result = await self._session.execute(select(Report.id).where(Report.user_id == user_id))
        return [str(report_id) for report_id in result.scalars().all()]

    async def delete_user(self, user: User) -> None:
        await self._session.delete(user)
