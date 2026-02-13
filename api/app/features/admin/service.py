import os
import shutil
from datetime import datetime
from pathlib import Path

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select, or_

from app.features.admin.repository import AdminRepository
from app.features.admin.schemas import (
    AdminJobMessage,
    AdminUserMessage,
    AdminUserUpdateCommand,
    AdminUserDeleteMessage,
    AdminStatsMessage,
    AdminStorageStatsMessage,
    AdminStorageBucketMessage,
    AdminCountsMessage,
    AdminSystemStatsMessage,
)
from app.features.auth.models import UserRole
from app.core.celery_app import celery_app
from app.features.jobs.service import JobService
from app.features.jobs.models import Job, JobFile, JobPageResult
from app.core.config import settings


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

    async def delete_user(self, user_id: str, actor_user_id: str) -> AdminUserDeleteMessage:
        user = await self._repo.get_user(user_id)
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
        if str(user.id) == actor_user_id:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Admins cannot delete themselves")

        job_ids = await self._repo.list_job_ids_for_user(user_id)
        report_ids = await self._repo.list_report_ids_for_user(user_id)

        await self._repo.delete_user(user)
        await self._session.commit()

        data_dir = Path(settings.data_dir)
        jobs_dir = data_dir / "jobs"
        reports_dir = data_dir / "reports"
        for job_id in job_ids:
            shutil.rmtree(jobs_dir / job_id, ignore_errors=True)
        for report_id in report_ids:
            shutil.rmtree(reports_dir / report_id, ignore_errors=True)

        return AdminUserDeleteMessage(
            status="ok",
            deleted_user_id=user_id,
            deleted_jobs=len(job_ids),
            deleted_reports=len(report_ids),
        )

    async def trigger_cleanup(self) -> dict:
        celery_app.send_task("cleanup_retention")
        return {"status": "ok"}

    async def get_stats(self) -> AdminStatsMessage:
        counts = await self._get_counts()
        storage = self._get_storage_stats()
        system = self._get_system_stats()
        return AdminStatsMessage(
            generated_at=datetime.utcnow(),
            storage=storage,
            counts=counts,
            system=system,
        )

    async def _get_counts(self) -> AdminCountsMessage:
        jobs_total_result = await self._session.execute(select(func.count()).select_from(Job))
        jobs_total = int(jobs_total_result.scalar_one() or 0)

        jobs_by_status_result = await self._session.execute(
            select(Job.status, func.count()).group_by(Job.status)
        )
        jobs_by_status = {str(status.value): int(count) for status, count in jobs_by_status_result.all()}

        job_files_result = await self._session.execute(select(func.count()).select_from(JobFile))
        job_files_total = int(job_files_result.scalar_one() or 0)

        pages_result = await self._session.execute(select(func.count()).select_from(JobPageResult))
        pages_total = int(pages_result.scalar_one() or 0)

        pdf_files_result = await self._session.execute(
            select(func.count()).select_from(JobFile).where(
                or_(
                    JobFile.set_a_path.ilike("%.pdf"),
                    JobFile.set_b_path.ilike("%.pdf"),
                )
            )
        )
        pdf_files_total = int(pdf_files_result.scalar_one() or 0)

        overlays_result = await self._session.execute(
            select(func.count()).select_from(JobPageResult).where(JobPageResult.overlay_svg_path.is_not(None))
        )
        overlay_images_total = int(overlays_result.scalar_one() or 0)

        return AdminCountsMessage(
            jobs_total=jobs_total,
            jobs_by_status=jobs_by_status,
            job_files_total=job_files_total,
            pages_total=pages_total,
            pdf_files_total=pdf_files_total,
            overlay_images_total=overlay_images_total,
        )

    def _get_storage_stats(self) -> AdminStorageStatsMessage:
        data_dir = Path(settings.data_dir)
        total_bytes = None
        used_bytes = None
        free_bytes = None
        if data_dir.exists():
            try:
                usage = shutil.disk_usage(data_dir)
                total_bytes = int(usage.total)
                used_bytes = int(usage.used)
                free_bytes = int(usage.free)
            except OSError:
                pass

        buckets: list[AdminStorageBucketMessage] = []

        jobs_dir = data_dir / "jobs"
        jobs_totals, jobs_buckets = self._scan_jobs_storage(jobs_dir)
        buckets.extend(jobs_buckets)
        if jobs_dir.exists():
            buckets.insert(
                0,
                AdminStorageBucketMessage(
                    name="Jobs Total",
                    path=str(jobs_dir),
                    bytes=jobs_totals[0],
                    files=jobs_totals[1],
                    pdf_files=jobs_totals[2],
                    image_files=jobs_totals[3],
                ),
            )

        samples_dir = data_dir / "samples"
        samples_stats = self._scan_path(samples_dir)
        if samples_dir.exists():
            buckets.append(
                AdminStorageBucketMessage(
                    name="Samples",
                    path=str(samples_dir),
                    bytes=samples_stats[0],
                    files=samples_stats[1],
                    pdf_files=samples_stats[2],
                    image_files=samples_stats[3],
                )
            )

        other_stats = self._scan_other_storage(data_dir, exclude={"jobs", "samples"})
        buckets.append(
            AdminStorageBucketMessage(
                name="Other Data",
                path=str(data_dir),
                bytes=other_stats[0],
                files=other_stats[1],
                pdf_files=other_stats[2],
                image_files=other_stats[3],
            )
        )

        return AdminStorageStatsMessage(
            data_dir=str(data_dir),
            total_bytes=total_bytes,
            used_bytes=used_bytes,
            free_bytes=free_bytes,
            buckets=buckets,
        )

    def _scan_jobs_storage(
        self, jobs_dir: Path
    ) -> tuple[tuple[int, int, int, int], list[AdminStorageBucketMessage]]:
        totals = [0, 0, 0, 0]
        categories = {
            "Uploads Set A": [0, 0, 0, 0],
            "Uploads Set B": [0, 0, 0, 0],
            "Artifacts": [0, 0, 0, 0],
            "Temp Reports": [0, 0, 0, 0],
            "Other Job Files": [0, 0, 0, 0],
        }

        if jobs_dir.exists():
            for root, _, files in os.walk(jobs_dir):
                for name in files:
                    file_path = Path(root) / name
                    try:
                        stat = file_path.stat()
                    except OSError:
                        continue
                    size = int(stat.st_size)
                    ext = file_path.suffix.lower()
                    rel_parts = file_path.relative_to(jobs_dir).parts
                    bucket = "Other Job Files"
                    if len(rel_parts) > 1:
                        category = rel_parts[1]
                        if category == "setA":
                            bucket = "Uploads Set A"
                        elif category == "setB":
                            bucket = "Uploads Set B"
                        elif category == "artifacts":
                            bucket = "Artifacts"
                        elif category == "temp_report":
                            bucket = "Temp Reports"

                    self._accumulate(categories[bucket], size, ext)
                    self._accumulate(totals, size, ext)

        buckets = []
        for name, stats in categories.items():
            path_hint = ""
            if name == "Uploads Set A":
                path_hint = str(jobs_dir / "*" / "setA")
            elif name == "Uploads Set B":
                path_hint = str(jobs_dir / "*" / "setB")
            elif name == "Artifacts":
                path_hint = str(jobs_dir / "*" / "artifacts")
            elif name == "Temp Reports":
                path_hint = str(jobs_dir / "*" / "temp_report")
            else:
                path_hint = str(jobs_dir)

            buckets.append(
                AdminStorageBucketMessage(
                    name=name,
                    path=path_hint,
                    bytes=stats[0],
                    files=stats[1],
                    pdf_files=stats[2],
                    image_files=stats[3],
                )
            )

        return (totals[0], totals[1], totals[2], totals[3]), buckets

    def _scan_path(self, path: Path) -> tuple[int, int, int, int]:
        totals = [0, 0, 0, 0]
        if not path.exists():
            return (0, 0, 0, 0)
        for root, _, files in os.walk(path):
            for name in files:
                file_path = Path(root) / name
                try:
                    stat = file_path.stat()
                except OSError:
                    continue
                size = int(stat.st_size)
                ext = file_path.suffix.lower()
                self._accumulate(totals, size, ext)
        return (totals[0], totals[1], totals[2], totals[3])

    def _scan_other_storage(self, data_dir: Path, exclude: set[str]) -> tuple[int, int, int, int]:
        totals = [0, 0, 0, 0]
        if not data_dir.exists():
            return (0, 0, 0, 0)
        for child in data_dir.iterdir():
            if child.name in exclude:
                continue
            if child.is_file():
                try:
                    stat = child.stat()
                except OSError:
                    continue
                size = int(stat.st_size)
                ext = child.suffix.lower()
                self._accumulate(totals, size, ext)
            elif child.is_dir():
                child_totals = self._scan_path(child)
                totals[0] += child_totals[0]
                totals[1] += child_totals[1]
                totals[2] += child_totals[2]
                totals[3] += child_totals[3]
        return (totals[0], totals[1], totals[2], totals[3])

    def _accumulate(self, stats: list[int], size: int, ext: str) -> None:
        stats[0] += size
        stats[1] += 1
        if ext == ".pdf":
            stats[2] += 1
        if ext in {".png", ".jpg", ".jpeg", ".svg", ".webp"}:
            stats[3] += 1

    def _get_system_stats(self) -> AdminSystemStatsMessage:
        cpu_count = os.cpu_count()
        load_avg_1m = None
        load_avg_5m = None
        load_avg_15m = None
        try:
            load_avg_1m, load_avg_5m, load_avg_15m = os.getloadavg()
        except (AttributeError, OSError):
            pass

        mem_total = None
        mem_available = None
        mem_used = None
        mem_used_percent = None
        meminfo_path = Path("/proc/meminfo")
        if meminfo_path.exists():
            meminfo = {}
            for line in meminfo_path.read_text(encoding="utf-8").splitlines():
                parts = line.split(":", 1)
                if len(parts) != 2:
                    continue
                key = parts[0].strip()
                value = parts[1].strip().split(" ")[0]
                try:
                    meminfo[key] = int(value) * 1024
                except ValueError:
                    continue
            mem_total = meminfo.get("MemTotal")
            mem_available = meminfo.get("MemAvailable")
            if mem_total is not None and mem_available is not None:
                mem_used = mem_total - mem_available
                if mem_total > 0:
                    mem_used_percent = (mem_used / mem_total) * 100.0

        return AdminSystemStatsMessage(
            cpu_count=cpu_count,
            load_avg_1m=load_avg_1m,
            load_avg_5m=load_avg_5m,
            load_avg_15m=load_avg_15m,
            memory_total_bytes=mem_total,
            memory_used_bytes=mem_used,
            memory_available_bytes=mem_available,
            memory_used_percent=mem_used_percent,
        )
