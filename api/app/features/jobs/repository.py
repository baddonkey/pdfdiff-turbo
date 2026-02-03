from typing import Iterable, Optional

from sqlalchemy import delete, func, select, update
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.jobs.models import Job, JobFile, JobPageResult


class JobRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_id_and_user(self, job_id: str, user_id: str) -> Optional[Job]:
        result = await self._session.execute(select(Job).where(Job.id == job_id, Job.user_id == user_id))
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: str) -> list[Job]:
        result = await self._session.execute(select(Job).where(Job.user_id == user_id))
        return list(result.scalars().all())

    async def count_for_user_on_day(self, user_id: str, day: datetime) -> int:
        start = day.replace(hour=0, minute=0, second=0, microsecond=0)
        end = start + timedelta(days=1)
        result = await self._session.execute(
            select(func.count())
            .select_from(Job)
            .where(Job.user_id == user_id)
            .where(Job.created_at >= start)
            .where(Job.created_at < end)
        )
        return int(result.scalar_one() or 0)

    async def delete_for_user(self, user_id: str) -> None:
        await self._session.execute(delete(Job).where(Job.user_id == user_id))

    async def delete_for_job(self, job_id: str, user_id: str) -> None:
        await self._session.execute(delete(Job).where(Job.id == job_id, Job.user_id == user_id))

    async def get_by_id(self, job_id: str) -> Optional[Job]:
        result = await self._session.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    def add(self, job: Job) -> None:
        self._session.add(job)


class JobFileRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def delete_for_job(self, job_id: str) -> None:
        await self._session.execute(delete(JobFile).where(JobFile.job_id == job_id))

    def add_many(self, files: Iterable[JobFile]) -> None:
        for item in files:
            self._session.add(item)

    async def list_for_job(self, job_id: str) -> list[JobFile]:
        result = await self._session.execute(select(JobFile).where(JobFile.job_id == job_id))
        return list(result.scalars().all())

    async def update_has_diffs_for_job(self, job_id: str) -> None:
        result = await self._session.execute(
            select(JobPageResult.job_file_id)
            .where(JobPageResult.diff_score.is_not(None))
            .where(JobPageResult.diff_score > 0)
            .join(JobFile, JobPageResult.job_file_id == JobFile.id)
            .where(JobFile.job_id == job_id)
            .distinct()
        )
        diff_file_ids = [row[0] for row in result.all()]
        await self._session.execute(update(JobFile).where(JobFile.job_id == job_id).values(has_diffs=False))
        if diff_file_ids:
            await self._session.execute(
                update(JobFile).where(JobFile.id.in_(diff_file_ids)).values(has_diffs=True)
            )

    async def diff_flags_for_job(self, job_id: str) -> dict[str, bool]:
        result = await self._session.execute(
            select(
                JobPageResult.job_file_id,
                func.bool_or(JobPageResult.diff_score > 0)
            )
            .join(JobFile, JobPageResult.job_file_id == JobFile.id)
            .where(JobFile.job_id == job_id)
            .where(JobPageResult.diff_score.is_not(None))
            .group_by(JobPageResult.job_file_id)
        )
        return {str(file_id): bool(flag) for file_id, flag in result.all()}

    async def get_by_id_and_job(self, file_id: str, job_id: str) -> Optional[JobFile]:
        result = await self._session.execute(
            select(JobFile).where(JobFile.id == file_id, JobFile.job_id == job_id)
        )
        return result.scalar_one_or_none()


class JobPageResultRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def list_for_file(self, file_id: str) -> list[JobPageResult]:
        pages_result = await self._session.execute(select(JobPageResult).where(JobPageResult.job_file_id == file_id))
        return list(pages_result.scalars().all())

    async def list_for_job(self, job_id: str) -> list[JobPageResult]:
        result = await self._session.execute(
            select(JobPageResult)
            .join(JobFile, JobPageResult.job_file_id == JobFile.id)
            .where(JobFile.job_id == job_id)
        )
        return list(result.scalars().all())

    async def count_status_for_job(self, job_id: str) -> list[tuple[str, int]]:
        result = await self._session.execute(
            select(JobPageResult.status, func.count())
            .join(JobFile, JobPageResult.job_file_id == JobFile.id)
            .where(JobFile.job_id == job_id)
            .group_by(JobPageResult.status)
        )
        return [(status.value if hasattr(status, "value") else str(status), count) for status, count in result.all()]

    async def count_status_for_file(self, file_id: str) -> list[tuple[str, int]]:
        result = await self._session.execute(
            select(JobPageResult.status, func.count())
            .where(JobPageResult.job_file_id == file_id)
            .group_by(JobPageResult.status)
        )
        return [(status.value if hasattr(status, "value") else str(status), count) for status, count in result.all()]

    async def delete_for_job(self, job_id: str) -> None:
        file_ids = select(JobFile.id).where(JobFile.job_id == job_id)
        await self._session.execute(delete(JobPageResult).where(JobPageResult.job_file_id.in_(file_ids)))
