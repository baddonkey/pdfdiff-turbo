import io
import re
import shutil
import zipfile
from pathlib import Path, PurePosixPath
from typing import Iterable

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.celery_app import celery_app
from app.features.jobs.models import Job, JobFile, JobStatus, PageStatus
from app.features.jobs.repository import JobFileRepository, JobPageResultRepository, JobRepository
from app.features.jobs.schemas import (
    JobCreatedMessage,
    JobFileMessage,
    JobPageMessage,
    JobStartedMessage,
    JobStatusMessage,
    JobSummaryMessage,
)
from app.features.jobs.storage import ensure_relative_path, list_relative_files, write_bytes


class JobService:
    def __init__(
        self,
        session: AsyncSession,
        job_repo: JobRepository,
        file_repo: JobFileRepository,
        page_repo: JobPageResultRepository,
    ):
        self._session = session
        self._job_repo = job_repo
        self._file_repo = file_repo
        self._page_repo = page_repo

    async def create_job(self, user_id: str) -> JobCreatedMessage:
        job = Job(user_id=user_id)
        self._job_repo.add(job)
        await self._session.commit()
        await self._session.refresh(job)
        return JobCreatedMessage(
            id=str(job.id),
            display_id=self._display_id(job),
            status=job.status.value,
            set_a_label=job.set_a_label,
            set_b_label=job.set_b_label,
            has_diffs=job.has_diffs,
            created_at=job.created_at,
        )

    async def upload_zip(self, job: Job, set_name: str, zip_bytes: bytes) -> None:
        target_dir = self._job_dir(str(job.id), set_name)
        target_dir.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                rel = ensure_relative_path(info.filename)
                data = zf.read(info)
                write_bytes(target_dir, rel, data)

    async def upload_zip_sets(self, job: Job, zip_bytes: bytes) -> None:
        target_a = self._job_dir(str(job.id), "setA")
        target_b = self._job_dir(str(job.id), "setB")
        target_a.mkdir(parents=True, exist_ok=True)
        target_b.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
            top_folders = sorted(
                {
                    PurePosixPath(info.filename).parts[0]
                    for info in zf.infolist()
                    if not info.is_dir() and PurePosixPath(info.filename).parts
                }
            )

            if len(top_folders) < 2:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Zip must contain at least two top-level folders",
                )

            folder_a, folder_b = top_folders[0], top_folders[1]
            job.set_a_label = folder_a
            job.set_b_label = folder_b
            count_a = 0
            count_b = 0

            for info in zf.infolist():
                if info.is_dir():
                    continue
                posix_path = PurePosixPath(info.filename)
                if not posix_path.parts:
                    continue
                top = posix_path.parts[0]
                rel_parts = posix_path.parts[1:]
                if not rel_parts:
                    continue
                rel = ensure_relative_path(str(PurePosixPath(*rel_parts)))
                data = zf.read(info)

                if top == folder_a:
                    write_bytes(target_a, rel, data)
                    count_a += 1
                elif top == folder_b:
                    write_bytes(target_b, rel, data)
                    count_b += 1

            if count_a == 0 or count_b == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Zip must include files in two top-level folders",
                )
        await self._session.commit()

    async def upload_multipart(self, job: Job, set_name: str, files: Iterable[tuple[str, bytes]]) -> None:
        target_dir = self._job_dir(str(job.id), set_name)
        target_dir.mkdir(parents=True, exist_ok=True)
        for rel, data in files:
            rel_path = ensure_relative_path(rel)
            write_bytes(target_dir, rel_path, data)

    async def start_job(self, job: Job) -> JobStartedMessage:
        set_a_dir = self._job_dir(str(job.id), "setA")
        set_b_dir = self._job_dir(str(job.id), "setB")
        set_a = list_relative_files(set_a_dir)
        set_b = list_relative_files(set_b_dir)

        await self._file_repo.delete_for_job(job.id)
        job.has_diffs = False

        pairs = self._pair_paths(set_a, set_b)
        files = [
            JobFile(
                job_id=job.id,
                relative_path=pair["relative_path"],
                set_a_path=pair["set_a_path"],
                set_b_path=pair["set_b_path"],
                missing_in_set_a=pair["missing_in_set_a"],
                missing_in_set_b=pair["missing_in_set_b"],
                has_diffs=False,
            )
            for pair in pairs
        ]
        self._file_repo.add_many(files)

        job.status = JobStatus.running
        await self._session.commit()
        celery_app.send_task("run_job", args=[str(job.id)])
        return JobStartedMessage(id=str(job.id), status=job.status.value)

    async def list_files(self, job: Job) -> list[JobFileMessage]:
        items = await self._file_repo.list_for_job(job.id)
        return [
            JobFileMessage(
                id=str(item.id),
                relative_path=item.relative_path,
                set_a_path=item.set_a_path,
                set_b_path=item.set_b_path,
                missing_in_set_a=item.missing_in_set_a,
                missing_in_set_b=item.missing_in_set_b,
                has_diffs=item.has_diffs,
                status="missing" if (item.missing_in_set_a or item.missing_in_set_b) else "ready",
                created_at=item.created_at,
            )
            for item in items
        ]

    async def list_pages(self, file_id: str) -> list[JobPageMessage]:
        pages = await self._page_repo.list_for_file(file_id)
        return [
            JobPageMessage(
                id=str(page.id),
                page_index=page.page_index,
                status=page.status.value,
                diff_score=page.diff_score,
                incompatible_size=page.incompatible_size,
                missing_in_set_a=page.missing_in_set_a,
                missing_in_set_b=page.missing_in_set_b,
                overlay_svg_path=page.overlay_svg_path,
                error_message=page.error_message,
                created_at=page.created_at,
            )
            for page in pages
        ]

    async def get_status(self, job: Job) -> JobStatusMessage:
        return JobStatusMessage(
            id=str(job.id),
            display_id=self._display_id(job),
            status=job.status.value,
            set_a_label=job.set_a_label,
            set_b_label=job.set_b_label,
            has_diffs=job.has_diffs,
            created_at=job.created_at,
        )

    async def list_jobs(self, user_id: str) -> list[JobSummaryMessage]:
        jobs = await self._job_repo.list_for_user(user_id)
        return [
            JobSummaryMessage(
                id=str(job.id),
                display_id=self._display_id(job),
                status=job.status.value,
                set_a_label=job.set_a_label,
                set_b_label=job.set_b_label,
                has_diffs=job.has_diffs,
                created_at=job.created_at,
            )
            for job in jobs
        ]

    async def clear_jobs(self, user_id: str) -> dict:
        jobs = await self._job_repo.list_for_user(user_id)
        for job in jobs:
            await self._page_repo.delete_for_job(job.id)
            await self._file_repo.delete_for_job(job.id)
            job_dir = Path(settings.data_dir) / "jobs" / str(job.id)
            shutil.rmtree(job_dir, ignore_errors=True)
        await self._job_repo.delete_for_user(user_id)
        await self._session.commit()
        return {"status": "ok", "deleted": len(jobs)}

    def list_samples(self) -> list[dict]:
        samples_dir = Path(settings.data_dir) / "samples"
        if not samples_dir.exists():
            return []
        samples: list[dict] = []
        for item in sorted(samples_dir.iterdir()):
            if not item.is_dir():
                continue
            set_a = item / "A"
            set_b = item / "B"
            if not set_a.exists() or not set_b.exists():
                continue
            samples.append(
                {
                    "name": item.name,
                    "filesA": sorted([str(p.relative_to(set_a)).replace('\\', '/') for p in set_a.rglob('*') if p.is_file()]),
                    "filesB": sorted([str(p.relative_to(set_b)).replace('\\', '/') for p in set_b.rglob('*') if p.is_file()]),
                }
            )
        return samples

    async def use_sample(self, job: Job, sample_name: str) -> dict:
        samples_dir = Path(settings.data_dir) / "samples"
        source = samples_dir / sample_name
        set_a = source / "A"
        set_b = source / "B"
        if not set_a.exists() or not set_b.exists():
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Sample not found")

        target_a = self._job_dir(str(job.id), "setA")
        target_b = self._job_dir(str(job.id), "setB")
        target_a.mkdir(parents=True, exist_ok=True)
        target_b.mkdir(parents=True, exist_ok=True)

        for src in set_a.rglob('*'):
            if src.is_file():
                rel = src.relative_to(set_a)
                dest = target_a / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)

        for src in set_b.rglob('*'):
            if src.is_file():
                rel = src.relative_to(set_b)
                dest = target_b / rel
                dest.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dest)

        job.set_a_label = f"{sample_name}-A"
        job.set_b_label = f"{sample_name}-B"
        await self._session.commit()
        return {"status": "ok"}

    @staticmethod
    def _sanitize_label(label: str, fallback: str) -> str:
        if not label:
            return fallback
        cleaned = re.sub(r"[^A-Za-z0-9_-]+", "-", label.strip())
        return cleaned.strip("-") or fallback

    @staticmethod
    def _display_id(job: Job) -> str:
        ts = job.created_at.strftime("%Y%m%d-%H%M")
        set_a = JobService._sanitize_label(job.set_a_label or "", "setA")
        set_b = JobService._sanitize_label(job.set_b_label or "", "setB")
        return f"{ts}-{set_a}_{set_b}"

    async def cancel_job(self, job: Job) -> JobStatusMessage:
        job.status = JobStatus.cancelled
        pages = await self._page_repo.list_for_job(job.id)
        for page in pages:
            if page.task_id:
                celery_app.control.revoke(page.task_id, terminate=False)
            if page.status in {PageStatus.pending, PageStatus.running}:
                page.status = PageStatus.failed
                page.error_message = "cancelled"
        await self._session.commit()
        return JobStatusMessage(id=str(job.id), status=job.status.value, created_at=job.created_at)

    async def get_progress(self, job: Job) -> dict:
        counts = dict(await self._page_repo.count_status_for_job(job.id))
        total = sum(counts.values())
        completed = counts.get(PageStatus.done.value, 0)
        missing = counts.get(PageStatus.missing.value, 0)
        incompatible = counts.get(PageStatus.incompatible_size.value, 0)
        failed = counts.get(PageStatus.failed.value, 0)
        running = counts.get(PageStatus.running.value, 0)
        pending = counts.get(PageStatus.pending.value, 0)
        finished = completed + missing + incompatible + failed
        percent = int((finished / total) * 100) if total else 0
        return {
            "total": total,
            "finished": finished,
            "percent": percent,
            "counts": counts,
            "completed": completed,
            "missing": missing,
            "incompatible": incompatible,
            "failed": failed,
            "running": running,
            "pending": pending,
        }

    @staticmethod
    def _pair_paths(set_a: Iterable[str], set_b: Iterable[str]) -> list[dict[str, str | bool | None]]:
        set_a_set = set(set_a)
        set_b_set = set(set_b)
        all_paths = sorted(set_a_set | set_b_set)
        pairs: list[dict[str, str | bool | None]] = []
        for rel in all_paths:
            in_a = rel in set_a_set
            in_b = rel in set_b_set
            pairs.append(
                {
                    "relative_path": rel,
                    "set_a_path": rel if in_a else None,
                    "set_b_path": rel if in_b else None,
                    "missing_in_set_a": not in_a,
                    "missing_in_set_b": not in_b,
                }
            )
        return pairs

    @staticmethod
    def _job_dir(job_id: str, set_name: str) -> Path:
        if set_name not in {"setA", "setB"}:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid set")
        return Path(settings.data_dir) / "jobs" / job_id / set_name
