from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models import User
from app.features.jobs.models import Job


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
