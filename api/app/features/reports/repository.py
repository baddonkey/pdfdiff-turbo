from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.reports.models import Report


class ReportRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    def add(self, report: Report) -> None:
        self._session.add(report)

    async def get_by_id_and_user(self, report_id: str, user_id: str) -> Optional[Report]:
        result = await self._session.execute(
            select(Report).where(Report.id == report_id, Report.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def list_for_user(self, user_id: str) -> list[Report]:
        result = await self._session.execute(select(Report).where(Report.user_id == user_id))
        return list(result.scalars().all())

    async def list_for_user_and_job(self, user_id: str, job_id: str) -> list[Report]:
        result = await self._session.execute(
            select(Report).where(Report.user_id == user_id, Report.source_job_id == job_id)
        )
        return list(result.scalars().all())

    async def get_by_id(self, report_id: str) -> Optional[Report]:
        result = await self._session.execute(select(Report).where(Report.id == report_id))
        return result.scalar_one_or_none()
