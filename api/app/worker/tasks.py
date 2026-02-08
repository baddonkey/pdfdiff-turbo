import asyncio
import shutil
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Iterable

import cv2
import fitz
import httpx
import numpy as np
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.celery_app import celery_app
from app.core.config import settings
import app.models  # noqa: F401
from app.features.config.models import AppConfig
from app.features.jobs.models import Job, JobFile, JobPageResult, JobStatus, PageStatus, TextStatus
from app.features.jobs.repository import JobFileRepository, JobPageResultRepository


PAGE_BATCH_SIZE = 50


@celery_app.task(name="run_job")
def run_job(job_id: str) -> None:
    asyncio.run(_run_job_async(job_id))


@celery_app.task(name="compare_page")
def compare_page(page_result_id: str) -> None:
    asyncio.run(_compare_page_async(page_result_id))


@celery_app.task(name="enqueue_pages")
def enqueue_pages(job_id: str) -> None:
    asyncio.run(_enqueue_pages_async(job_id))


@celery_app.task(name="extract_text")
def extract_text(job_file_id: str) -> None:
    asyncio.run(_extract_text_async(job_file_id))


@celery_app.task(name="cleanup_retention")
def cleanup_retention() -> None:
    asyncio.run(_cleanup_retention_async())


async def _run_job_async(job_id: str) -> None:
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        return
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    sessionmaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sessionmaker() as session:
        job = await _get_job(session, job_uuid)
        if not job:
            await engine.dispose()
            return
        if job.status == JobStatus.cancelled:
            await engine.dispose()
            return

        files = await _get_job_files(session, job.id)
        page_results: list[JobPageResult] = []

        for job_file in files:
            if job_file.missing_in_set_a or job_file.missing_in_set_b:
                page_result = JobPageResult(
                    job_file_id=job_file.id,
                    page_index=0,
                    status=PageStatus.missing,
                    missing_in_set_a=job_file.missing_in_set_a,
                    missing_in_set_b=job_file.missing_in_set_b,
                )
                page_results.append(page_result)
                continue

            path_a = _resolve_file_path(job.id, "setA", job_file.set_a_path)
            path_b = _resolve_file_path(job.id, "setB", job_file.set_b_path)
            if not path_a.exists() or not path_b.exists():
                page_result = JobPageResult(
                    job_file_id=job_file.id,
                    page_index=0,
                    status=PageStatus.missing,
                    missing_in_set_a=not path_a.exists(),
                    missing_in_set_b=not path_b.exists(),
                )
                page_results.append(page_result)
                continue

            with fitz.open(path_a) as doc_a, fitz.open(path_b) as doc_b:
                count_a = doc_a.page_count
                count_b = doc_b.page_count

            max_pages = max(count_a, count_b)
            for page_index in range(max_pages):
                missing_a = page_index >= count_a
                missing_b = page_index >= count_b
                status = PageStatus.pending
                if missing_a or missing_b:
                    status = PageStatus.missing
                page_result = JobPageResult(
                    job_file_id=job_file.id,
                    page_index=page_index,
                    status=status,
                    missing_in_set_a=missing_a,
                    missing_in_set_b=missing_b,
                )
                page_results.append(page_result)

        session.add_all(page_results)
        await session.commit()

        job.status = JobStatus.running
        await session.commit()
        await _enqueue_text_tasks(session, job.id)
        await _enqueue_next_batch(session, job.id)
    await engine.dispose()


async def _extract_text_async(job_file_id: str) -> None:
    try:
        job_file_uuid = uuid.UUID(job_file_id)
    except ValueError:
        return
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    sessionmaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sessionmaker() as session:
        result = await session.execute(
            select(JobFile, Job)
            .join(Job, JobFile.job_id == Job.id)
            .where(JobFile.id == job_file_uuid)
        )
        row = result.first()
        if not row:
            await engine.dispose()
            return

        job_file, job = row
        if job.status == JobStatus.cancelled:
            await engine.dispose()
            return

        job_file.text_status = TextStatus.running
        job_file.text_error = None
        await session.commit()

        text_dir = Path(settings.data_dir) / "jobs" / str(job.id) / "text" / str(job_file.id)
        text_dir.mkdir(parents=True, exist_ok=True)

        success_a = False
        success_b = False

        try:
            if job_file.set_a_path:
                path_a = _resolve_file_path(job.id, "setA", job_file.set_a_path)
                if path_a.exists():
                    text_a = await _extract_text_from_pdf(path_a)
                    text_path_a = text_dir / "setA.txt"
                    text_path_a.write_text(text_a, encoding="utf-8")
                    job_file.text_set_a_path = str(text_path_a)
                    success_a = True

            if job_file.set_b_path:
                path_b = _resolve_file_path(job.id, "setB", job_file.set_b_path)
                if path_b.exists():
                    text_b = await _extract_text_from_pdf(path_b)
                    text_path_b = text_dir / "setB.txt"
                    text_path_b.write_text(text_b, encoding="utf-8")
                    job_file.text_set_b_path = str(text_path_b)
                    success_b = True

            if not success_a and not success_b:
                job_file.text_status = TextStatus.missing
            elif job_file.missing_in_set_a or job_file.missing_in_set_b:
                job_file.text_status = TextStatus.missing
            else:
                job_file.text_status = TextStatus.done
            await session.commit()
        except Exception as exc:  # pragma: no cover - runtime safety
            job_file.text_status = TextStatus.failed
            job_file.text_error = str(exc)
            await session.commit()
    await engine.dispose()


async def _compare_page_async(page_result_id: str) -> None:
    try:
        page_uuid = uuid.UUID(page_result_id)
    except ValueError:
        return
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    sessionmaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sessionmaker() as session:
        result = await session.execute(
            select(JobPageResult, JobFile, Job)
            .join(JobFile, JobPageResult.job_file_id == JobFile.id)
            .join(Job, JobFile.job_id == Job.id)
            .where(JobPageResult.id == page_uuid)
        )
        row = result.first()
        if not row:
            await engine.dispose()
            return

        page_result, job_file, job = row
        if job.status == JobStatus.cancelled:
            page_result.status = PageStatus.failed
            page_result.error_message = "cancelled"
            await session.commit()
            return
        page_result.status = PageStatus.running
        await session.commit()

        if page_result.missing_in_set_a or page_result.missing_in_set_b:
            page_result.status = PageStatus.missing
            await session.commit()
            await _enqueue_next_batch(session, job.id)
            await _try_complete_job(session, job.id)
            return

        try:
            path_a = _resolve_file_path(job.id, "setA", job_file.set_a_path)
            path_b = _resolve_file_path(job.id, "setB", job_file.set_b_path)

            image_a = _render_page(path_a, page_result.page_index)
            image_b = _render_page(path_b, page_result.page_index)

            if image_a.shape != image_b.shape:
                page_result.status = PageStatus.incompatible_size
                page_result.incompatible_size = True
                page_result.diff_score = None
                await session.commit()
                await _enqueue_next_batch(session, job.id)
                await _try_complete_job(session, job.id)
                return

            diff_score, overlay_svg = _diff_and_overlay(image_a, image_b)
            overlay_path = _overlay_path(job.id, job_file.id, page_result.page_index)
            overlay_path.parent.mkdir(parents=True, exist_ok=True)
            overlay_path.write_text(overlay_svg, encoding="utf-8")

            page_result.diff_score = diff_score
            page_result.overlay_svg_path = str(overlay_path)
            page_result.status = PageStatus.done
            if diff_score > 0:
                job_file.has_diffs = True
                job.has_diffs = True
            await session.commit()
            await _enqueue_next_batch(session, job.id)
            await _try_complete_job(session, job.id)
        except Exception as exc:  # pragma: no cover - runtime safety
            page_result.status = PageStatus.failed
            page_result.error_message = str(exc)
            await session.commit()
            await _enqueue_next_batch(session, job.id)
            await _try_complete_job(session, job.id)
    await engine.dispose()


async def _enqueue_pages_async(job_id: str) -> None:
    try:
        job_uuid = uuid.UUID(job_id)
    except ValueError:
        return
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    sessionmaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sessionmaker() as session:
        await _enqueue_next_batch(session, job_uuid)
    await engine.dispose()


async def _cleanup_retention_async() -> None:
    engine = create_async_engine(settings.database_url, poolclass=NullPool)
    sessionmaker = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with sessionmaker() as session:
        config = await _get_app_config(session)
        file_retention_hours = max(1, config.file_retention_hours if config else 24)
        job_retention_days = max(1, config.job_retention_days if config else 7)
        now = datetime.utcnow()
        file_cutoff = now - timedelta(hours=file_retention_hours)
        job_cutoff = now - timedelta(days=job_retention_days)

        result = await session.execute(
            select(Job.id, Job.status).where(Job.created_at < file_cutoff)
        )
        for job_id, status in result.all():
            if status == JobStatus.running:
                continue
            job_dir = Path(settings.data_dir) / "jobs" / str(job_id)
            shutil.rmtree(job_dir, ignore_errors=True)

        result = await session.execute(select(Job).where(Job.created_at < job_cutoff))
        jobs = list(result.scalars().all())
        page_repo = JobPageResultRepository(session)
        file_repo = JobFileRepository(session)
        for job in jobs:
            if job.status == JobStatus.running:
                continue
            await page_repo.delete_for_job(job.id)
            await file_repo.delete_for_job(job.id)
            await session.execute(delete(Job).where(Job.id == job.id))
            job_dir = Path(settings.data_dir) / "jobs" / str(job.id)
            shutil.rmtree(job_dir, ignore_errors=True)

        await session.commit()
    await engine.dispose()


async def _get_job(session: AsyncSession, job_id: uuid.UUID) -> Job | None:
    result = await session.execute(select(Job).where(Job.id == job_id))
    return result.scalar_one_or_none()


async def _get_app_config(session: AsyncSession) -> AppConfig | None:
    result = await session.execute(select(AppConfig).order_by(AppConfig.id).limit(1))
    return result.scalar_one_or_none()


async def _get_job_files(session: AsyncSession, job_id: str) -> list[JobFile]:
    result = await session.execute(select(JobFile).where(JobFile.job_id == job_id))
    return list(result.scalars().all())


async def _try_complete_job(session: AsyncSession, job_id: str) -> None:
    pending = await session.execute(
        select(JobPageResult)
        .join(JobFile, JobPageResult.job_file_id == JobFile.id)
        .where(JobFile.job_id == job_id)
        .where(JobPageResult.status.in_([PageStatus.pending, PageStatus.running]))
    )
    if pending.scalars().first() is None:
        result = await session.execute(select(Job).where(Job.id == job_id))
        job = result.scalar_one_or_none()
        if job and job.status != JobStatus.cancelled:
            file_repo = JobFileRepository(session)
            await file_repo.update_has_diffs_for_job(job.id)
            diff_any = await session.execute(
                select(JobPageResult)
                .join(JobFile, JobPageResult.job_file_id == JobFile.id)
                .where(JobFile.job_id == job.id)
                .where(JobPageResult.diff_score.is_not(None))
                .where(JobPageResult.diff_score > 0)
                .limit(1)
            )
            job.has_diffs = diff_any.scalar_one_or_none() is not None
            job.status = JobStatus.completed
            await session.commit()


async def _enqueue_next_batch(session: AsyncSession, job_id: uuid.UUID) -> None:
    result = await session.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job or job.status == JobStatus.cancelled:
        return

    in_flight_result = await session.execute(
        select(func.count())
        .select_from(JobPageResult)
        .join(JobFile, JobPageResult.job_file_id == JobFile.id)
        .where(JobFile.job_id == job_id)
        .where(JobPageResult.status.in_([PageStatus.pending, PageStatus.running]))
        .where(JobPageResult.task_id.is_not(None))
    )
    in_flight = int(in_flight_result.scalar_one() or 0)
    available_slots = max(0, PAGE_BATCH_SIZE - in_flight)
    if available_slots == 0:
        return

    pending_result = await session.execute(
        select(JobPageResult)
        .join(JobFile, JobPageResult.job_file_id == JobFile.id)
        .where(JobFile.job_id == job_id)
        .where(JobPageResult.status == PageStatus.pending)
        .where(JobPageResult.task_id.is_(None))
        .order_by(JobPageResult.created_at, JobPageResult.id)
        .limit(available_slots)
    )
    pages = list(pending_result.scalars().all())
    if not pages:
        return

    for page in pages:
        async_result = celery_app.send_task("compare_page", args=[str(page.id)])
        page.task_id = async_result.id
    await session.commit()


async def _enqueue_text_tasks(session: AsyncSession, job_id: uuid.UUID) -> None:
    result = await session.execute(select(JobFile).where(JobFile.job_id == job_id))
    files = list(result.scalars().all())
    for job_file in files:
        if job_file.missing_in_set_a and job_file.missing_in_set_b:
            job_file.text_status = TextStatus.missing
            continue
        celery_app.send_task("extract_text", args=[str(job_file.id)])
    await session.commit()


def _resolve_file_path(job_id: str, set_name: str, rel_path: str | None) -> Path:
    if not rel_path:
        return Path(settings.data_dir) / "missing"
    return Path(settings.data_dir) / "jobs" / str(job_id) / set_name / rel_path


def _render_page(pdf_path: Path, page_index: int) -> np.ndarray:
    with fitz.open(pdf_path) as doc:
        page = doc.load_page(page_index)
        scale = settings.render_dpi / 72.0
        matrix = fitz.Matrix(scale, scale)
        pix = page.get_pixmap(matrix=matrix, colorspace=fitz.csRGB)
        img = np.frombuffer(pix.samples, dtype=np.uint8)
        return img.reshape(pix.height, pix.width, 3)


def _diff_and_overlay(image_a: np.ndarray, image_b: np.ndarray) -> tuple[float, str]:
    diff = cv2.absdiff(image_a, image_b)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    _, mask = cv2.threshold(gray, settings.diff_threshold, 255, cv2.THRESH_BINARY)

    kernel = np.ones((3, 3), np.uint8)
    mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)
    mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)

    changed = int(np.count_nonzero(mask))
    total = mask.shape[0] * mask.shape[1]
    diff_score = (changed / total) * 100.0 if total else 0.0

    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    boxes = [cv2.boundingRect(cnt) for cnt in contours]

    height, width = mask.shape
    svg = _build_overlay_svg(width, height, boxes)
    return diff_score, svg


def _build_overlay_svg(width: int, height: int, boxes: Iterable[tuple[int, int, int, int]]) -> str:
    circles = "\n".join(
        f'<circle cx="{x + w / 2:.2f}" cy="{y + h / 2:.2f}" r="30" '
        f'style="fill:none;stroke:currentColor;stroke-width:3" />'
        for x, y, w, h in boxes
    )
    return (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">\n'
        f'{circles}\n'
        f'</svg>'
    )


def _overlay_path(job_id: str, job_file_id: str, page_index: int) -> Path:
    return Path(settings.data_dir) / "jobs" / str(job_id) / "artifacts" / str(job_file_id) / f"page_{page_index}.svg"


async def _extract_text_from_pdf(pdf_path: Path) -> str:
    headers = {"Accept": "text/plain", "Content-Type": "application/pdf"}
    timeout = httpx.Timeout(60.0, connect=10.0)
    async with httpx.AsyncClient(timeout=timeout) as client:
        data = pdf_path.read_bytes()
        response = await client.put(settings.tika_url, content=data, headers=headers)
        response.raise_for_status()
        return response.text
