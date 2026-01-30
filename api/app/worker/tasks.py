import asyncio
import uuid
from pathlib import Path
from typing import Iterable

import cv2
import fitz
import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from app.core.celery_app import celery_app
from app.core.config import settings
import app.models  # noqa: F401
from app.features.jobs.models import Job, JobFile, JobPageResult, JobStatus, PageStatus


@celery_app.task(name="run_job")
def run_job(job_id: str) -> None:
    asyncio.run(_run_job_async(job_id))


@celery_app.task(name="compare_page")
def compare_page(page_result_id: str) -> None:
    asyncio.run(_compare_page_async(page_result_id))


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
        pending_ids: list[str] = []

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

        for page_result in page_results:
            if page_result.status == PageStatus.pending:
                pending_ids.append(str(page_result.id))

        if job.status == JobStatus.cancelled:
            return

        for page_result_id in pending_ids:
            async_result = celery_app.send_task("compare_page", args=[page_result_id])
            result = await session.execute(select(JobPageResult).where(JobPageResult.id == page_result_id))
            page_row = result.scalar_one_or_none()
            if page_row:
                page_row.task_id = async_result.id

        await session.commit()

        job.status = JobStatus.running
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
                return

            diff_score, overlay_svg = _diff_and_overlay(image_a, image_b)
            overlay_path = _overlay_path(job.id, job_file.id, page_result.page_index)
            overlay_path.parent.mkdir(parents=True, exist_ok=True)
            overlay_path.write_text(overlay_svg, encoding="utf-8")

            page_result.diff_score = diff_score
            page_result.overlay_svg_path = str(overlay_path)
            page_result.status = PageStatus.done
            await session.commit()
            await _try_complete_job(session, job.id)
        except Exception as exc:  # pragma: no cover - runtime safety
            page_result.status = PageStatus.failed
            page_result.error_message = str(exc)
            await session.commit()
            await _try_complete_job(session, job.id)
    await engine.dispose()


async def _get_job(session: AsyncSession, job_id: uuid.UUID) -> Job | None:
    result = await session.execute(select(Job).where(Job.id == job_id))
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
            job.status = JobStatus.completed
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
