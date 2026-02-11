from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.celery_app import celery_app
from app.features.auth.models import User
from app.features.jobs.repository import JobRepository
from app.features.jobs.service import JobService
from app.features.reports.models import Report, ReportStatus, ReportType
from app.features.reports.repository import ReportRepository
from app.features.reports.schemas import ReportCreateCommand, ReportMessage


class ReportService:
    def __init__(
        self,
        session: AsyncSession,
        report_repo: ReportRepository,
        job_repo: JobRepository,
    ):
        self._session = session
        self._report_repo = report_repo
        self._job_repo = job_repo

    async def create_report(self, user: User, command: ReportCreateCommand) -> ReportMessage:
        job = await self._job_repo.get_by_id_and_user(command.source_job_id, str(user.id))
        if not job:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

        if not JobService._files_available(str(job.id)):
            raise HTTPException(
                status_code=status.HTTP_410_GONE,
                detail="Files are no longer available for this job",
            )

        report = Report(
            user_id=user.id,
            source_job_id=job.id,
            report_type=ReportType.both,
            status=ReportStatus.queued,
            progress=0,
        )
        self._report_repo.add(report)
        await self._session.commit()
        await self._session.refresh(report)

        celery_app.send_task("generate_report", args=[str(report.id)])

        return self._to_message(report)

    async def list_reports(self, user: User, source_job_id: str | None = None) -> list[ReportMessage]:
        if source_job_id:
            reports = await self._report_repo.list_for_user_and_job(str(user.id), source_job_id)
        else:
            reports = await self._report_repo.list_for_user(str(user.id))
        return [self._to_message(report) for report in reports]

    async def get_report(self, user: User, report_id: str) -> ReportMessage:
        report = await self._report_repo.get_by_id_and_user(report_id, str(user.id))
        if not report:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
        return self._to_message(report)

    @staticmethod
    def _to_message(report: Report) -> ReportMessage:
        return ReportMessage(
            id=str(report.id),
            source_job_id=str(report.source_job_id),
            status=report.status,
            progress=report.progress,
            visual_filename=report.visual_filename,
            text_filename=report.text_filename,
            bundle_filename=report.bundle_filename,
            error=report.error,
            created_at=report.created_at,
            updated_at=report.updated_at,
        )
