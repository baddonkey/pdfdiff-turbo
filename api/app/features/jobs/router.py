from pathlib import Path
from datetime import datetime

from typing import Iterable

import asyncio

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse
from jose import JWTError

from app.core.config import settings
from app.features.auth.deps import get_current_user, get_user_repository
from app.features.auth.models import User
from app.features.auth.security import decode_token
from app.features.auth.repository import UserRepository
from app.db.session import SessionLocal
from app.features.jobs.deps import get_job_service, get_job_repository, get_job_file_repository, get_job_page_result_repository
from app.features.config.deps import get_app_config_service
from app.features.config.service import AppConfigService
from app.features.jobs.schemas import (
    JobCreatedMessage,
    JobFileMessage,
    JobPageMessage,
    JobStartedMessage,
    JobStatusMessage,
    JobSummaryMessage,
)
from app.features.jobs.service import JobService
from app.features.jobs.repository import JobRepository, JobPageResultRepository, JobFileRepository
from app.features.jobs.models import PageStatus

router = APIRouter(prefix="/jobs", tags=["jobs"])


def _status_from_counts(counts: dict[str, int], missing_a: bool, missing_b: bool) -> str:
    if missing_a or missing_b:
        return "missing"
    running = counts.get(PageStatus.running.value, 0)
    pending = counts.get(PageStatus.pending.value, 0)
    failed = counts.get(PageStatus.failed.value, 0)
    incompatible = counts.get(PageStatus.incompatible_size.value, 0)
    if running or pending:
        return "running"
    if failed:
        return "failed"
    if incompatible:
        return "incompatible"
    return "completed"


@router.websocket("/ws")
async def jobs_ws(
    websocket: WebSocket,
    token: str | None = Query(default=None),
    user_repo: UserRepository = Depends(get_user_repository),
) -> None:
    if not token:
        await websocket.close(code=1008)
        return
    try:
        payload = decode_token(token)
    except JWTError:
        await websocket.close(code=1008)
        return
    if payload.get("type") != "access":
        await websocket.close(code=1008)
        return
    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=1008)
        return
    user = await user_repo.get_by_id(user_id)
    if not user or not user.is_active:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    try:
        while True:
            async with SessionLocal() as session:
                repo = JobRepository(session)
                page_repo = JobPageResultRepository(session)
                jobs = await repo.list_for_user(user_id)
                payload = []
                for job in jobs:
                    item = JobSummaryMessage(
                        id=str(job.id),
                        display_id=JobService._display_id(job),
                        status=job.status.value,
                        set_a_label=job.set_a_label,
                        set_b_label=job.set_b_label,
                        has_diffs=job.has_diffs,
                        created_at=job.created_at,
                    ).dict()
                    item["created_at"] = job.created_at.isoformat()
                    payload.append(item)
                for item, job in zip(payload, jobs):
                    counts = dict(await page_repo.count_status_for_job(job.id))
                    total = sum(counts.values())
                    completed = counts.get(PageStatus.done.value, 0)
                    missing = counts.get(PageStatus.missing.value, 0)
                    incompatible = counts.get(PageStatus.incompatible_size.value, 0)
                    failed = counts.get(PageStatus.failed.value, 0)
                    running = counts.get(PageStatus.running.value, 0)
                    pending = counts.get(PageStatus.pending.value, 0)
                    finished = completed + missing + incompatible + failed
                    percent = int((finished / total) * 100) if total else 0
                    item["progress"] = {
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
            await websocket.send_json(payload)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return


@router.websocket("/{job_id}/files/ws")
async def job_files_ws(
    websocket: WebSocket,
    job_id: str,
    token: str | None = Query(default=None),
    user_repo: UserRepository = Depends(get_user_repository),
) -> None:
    if not token:
        await websocket.close(code=1008)
        return
    try:
        payload = decode_token(token)
    except JWTError:
        await websocket.close(code=1008)
        return
    if payload.get("type") != "access":
        await websocket.close(code=1008)
        return
    user_id = payload.get("sub")
    if not user_id:
        await websocket.close(code=1008)
        return
    user = await user_repo.get_by_id(user_id)
    if not user or not user.is_active:
        await websocket.close(code=1008)
        return

    await websocket.accept()
    try:
        while True:
            async with SessionLocal() as session:
                repo = JobRepository(session)
                file_repo = JobFileRepository(session)
                page_repo = JobPageResultRepository(session)
                job = await repo.get_by_id_and_user(job_id, user_id)
                if not job:
                    await websocket.send_json({"error": "Job not found"})
                    await asyncio.sleep(2)
                    continue
                files = await file_repo.list_for_job(job.id)
                diff_flags = await file_repo.diff_flags_for_job(job.id)
                payload = []
                for file in files:
                    counts = dict(await page_repo.count_status_for_file(str(file.id)))
                    payload.append(
                        {
                            "id": str(file.id),
                            "relative_path": file.relative_path,
                            "missing_in_set_a": file.missing_in_set_a,
                            "missing_in_set_b": file.missing_in_set_b,
                            "has_diffs": diff_flags.get(str(file.id), file.has_diffs),
                            "status": _status_from_counts(counts, file.missing_in_set_a, file.missing_in_set_b),
                            "created_at": file.created_at.isoformat(),
                        }
                    )
            await websocket.send_json(payload)
            await asyncio.sleep(2)
    except WebSocketDisconnect:
        return


@router.options("")
async def options_jobs() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("", response_model=JobCreatedMessage)
async def create_job(
    service: JobService = Depends(get_job_service),
    repo=Depends(get_job_repository),
    user: User = Depends(get_current_user),
) -> JobCreatedMessage:
    if user.max_jobs_per_user_per_day and user.max_jobs_per_user_per_day > 0:
        today_count = await repo.count_for_user_on_day(str(user.id), datetime.utcnow())
        if today_count >= user.max_jobs_per_user_per_day:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Daily job limit exceeded",
            )
    return await service.create_job(str(user.id))

@router.get("/samples")
async def list_samples(
    service: JobService = Depends(get_job_service),
    user: User = Depends(get_current_user),
) -> list[dict]:
    return service.list_samples()


@router.get("", response_model=list[JobSummaryMessage])
async def list_jobs(
    service: JobService = Depends(get_job_service),
    user: User = Depends(get_current_user),
) -> list[JobSummaryMessage]:
    return await service.list_jobs(str(user.id))


@router.delete("")
async def clear_jobs(
    service: JobService = Depends(get_job_service),
    user: User = Depends(get_current_user),
) -> dict:
    return await service.clear_jobs(str(user.id))


@router.delete("/{job_id}")
async def delete_job(
    job_id: str,
    service: JobService = Depends(get_job_service),
    repo=Depends(get_job_repository),
    user: User = Depends(get_current_user),
) -> dict:
    job = await repo.get_by_id_and_user(job_id, str(user.id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return await service.delete_job(job)


@router.post("/clear")
async def clear_jobs_post(
    service: JobService = Depends(get_job_service),
    user: User = Depends(get_current_user),
) -> dict:
    return await service.clear_jobs(str(user.id))


@router.post("/{job_id}/upload")
async def upload_job_files(
    job_id: str,
    set_name: str = Query("A", alias="set", pattern="^(A|B)$"),
    zip_file: UploadFile | None = File(default=None),
    files: list[UploadFile] = File(default=[]),
    relative_paths: list[str] = Form(default=[]),
    service: JobService = Depends(get_job_service),
    repo=Depends(get_job_repository),
    user: User = Depends(get_current_user),
    config_service: AppConfigService = Depends(get_app_config_service),
) -> dict:
    config = await config_service.get_config()
    if not config.enable_dropzone:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dropzone disabled")
    max_upload_bytes = user.max_upload_mb * 1024 * 1024
    job = await repo.get_by_id_and_user(job_id, str(user.id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if zip_file is not None:
        zip_bytes = await zip_file.read()
        if max_upload_bytes and len(zip_bytes) > max_upload_bytes:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail="Upload size limit exceeded",
            )
        await service.upload_zip(job, "setA" if set_name == "A" else "setB", zip_bytes)
        return {"status": "ok", "mode": "zip"}

    if files:
        if not relative_paths or len(relative_paths) != len(files):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="relative_paths required for multipart")
        payload = []
        total_size = 0
        for upload, rel in zip(files, relative_paths):
            data = await upload.read()
            total_size += len(data)
            if max_upload_bytes and total_size > max_upload_bytes:
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail="Upload size limit exceeded",
                )
            payload.append((rel, data))
        await service.upload_multipart(job, "setA" if set_name == "A" else "setB", payload)
        return {"status": "ok", "mode": "multipart"}

    raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No files provided")


@router.post("/{job_id}/upload-zip")
async def upload_job_zip_sets(
    job_id: str,
    zip_file: UploadFile = File(...),
    service: JobService = Depends(get_job_service),
    repo=Depends(get_job_repository),
    user: User = Depends(get_current_user),
    config_service: AppConfigService = Depends(get_app_config_service),
) -> dict:
    config = await config_service.get_config()
    if not config.enable_dropzone:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Dropzone disabled")
    max_upload_bytes = user.max_upload_mb * 1024 * 1024
    job = await repo.get_by_id_and_user(job_id, str(user.id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    zip_bytes = await zip_file.read()
    if max_upload_bytes and len(zip_bytes) > max_upload_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Upload size limit exceeded",
        )
    await service.upload_zip_sets(job, zip_bytes)
    return {"status": "ok", "mode": "zip_sets"}

@router.post("/{job_id}/use-sample")
async def use_sample_set(
    job_id: str,
    sample: str = Query(""),
    service: JobService = Depends(get_job_service),
    repo=Depends(get_job_repository),
    user: User = Depends(get_current_user),
) -> dict:
    if not sample:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Sample is required")
    job = await repo.get_by_id_and_user(job_id, str(user.id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return await service.use_sample(job, sample)


@router.post("/{job_id}/start", response_model=JobStartedMessage)
async def start_job(
    job_id: str,
    set_a_label: str | None = Query(default=None, alias="setA"),
    set_b_label: str | None = Query(default=None, alias="setB"),
    service: JobService = Depends(get_job_service),
    repo=Depends(get_job_repository),
    user: User = Depends(get_current_user),
) -> JobStartedMessage:
    job = await repo.get_by_id_and_user(job_id, str(user.id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if set_a_label:
        job.set_a_label = set_a_label
    if set_b_label:
        job.set_b_label = set_b_label
    return await service.start_job(
        job,
        max_files_per_set=user.max_files_per_set,
        max_pages_per_job=user.max_pages_per_job,
    )


@router.post("/{job_id}/continue", response_model=JobStartedMessage)
async def continue_job(
    job_id: str,
    service: JobService = Depends(get_job_service),
    repo=Depends(get_job_repository),
    user: User = Depends(get_current_user),
) -> JobStartedMessage:
    job = await repo.get_by_id_and_user(job_id, str(user.id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return await service.continue_job(job)


@router.get("/{job_id}", response_model=JobStatusMessage)
async def get_job_status(
    job_id: str,
    service: JobService = Depends(get_job_service),
    repo=Depends(get_job_repository),
    user: User = Depends(get_current_user),
) -> JobStatusMessage:
    job = await repo.get_by_id_and_user(job_id, str(user.id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return await service.get_status(job)


@router.get("/{job_id}/progress")
async def get_job_progress(
    job_id: str,
    service: JobService = Depends(get_job_service),
    repo=Depends(get_job_repository),
    user: User = Depends(get_current_user),
) -> dict:
    job = await repo.get_by_id_and_user(job_id, str(user.id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return await service.get_progress(job)


@router.post("/{job_id}/cancel", response_model=JobStatusMessage)
async def cancel_job(
    job_id: str,
    service: JobService = Depends(get_job_service),
    repo=Depends(get_job_repository),
    user: User = Depends(get_current_user),
) -> JobStatusMessage:
    job = await repo.get_by_id_and_user(job_id, str(user.id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return await service.cancel_job(job)


@router.get("/{job_id}/files", response_model=list[JobFileMessage])
async def list_job_files(
    job_id: str,
    service: JobService = Depends(get_job_service),
    repo=Depends(get_job_repository),
    file_repo=Depends(get_job_file_repository),
    page_repo: JobPageResultRepository = Depends(get_job_page_result_repository),
    user: User = Depends(get_current_user),
) -> list[JobFileMessage]:
    job = await repo.get_by_id_and_user(job_id, str(user.id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    diff_flags = await file_repo.diff_flags_for_job(job.id)
    items = await service.list_files(job)
    for item in items:
        item.has_diffs = diff_flags.get(item.id, item.has_diffs)
        counts = dict(await page_repo.count_status_for_file(item.id))
        item.status = _status_from_counts(counts, item.missing_in_set_a, item.missing_in_set_b)
    return items


@router.get("/{job_id}/files/{file_id}/pages", response_model=list[JobPageMessage])
async def list_file_pages(
    job_id: str,
    file_id: str,
    service: JobService = Depends(get_job_service),
    repo=Depends(get_job_repository),
    file_repo=Depends(get_job_file_repository),
    user: User = Depends(get_current_user),
) -> list[JobPageMessage]:
    job = await repo.get_by_id_and_user(job_id, str(user.id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    job_file = await file_repo.get_by_id_and_job(file_id, job.id)
    if not job_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return await service.list_pages(file_id)


@router.get("/{job_id}/files/{file_id}/pages/{page_index}/overlay")
async def get_page_overlay(
    job_id: str,
    file_id: str,
    page_index: int,
    repo=Depends(get_job_repository),
    file_repo=Depends(get_job_file_repository),
    user: User = Depends(get_current_user),
) -> FileResponse:
    job = await repo.get_by_id_and_user(job_id, str(user.id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    if not await file_repo.get_by_id_and_job(file_id, job.id):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    overlay_path = Path(settings.data_dir) / "jobs" / job_id / "artifacts" / file_id / f"page_{page_index}.svg"
    if not overlay_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Overlay not found")
    return FileResponse(path=str(overlay_path), media_type="image/svg+xml")


@router.get("/{job_id}/files/{file_id}/content")
async def get_file_content(
    job_id: str,
    file_id: str,
    set_name: str = Query("A", alias="set", pattern="^(A|B)$"),
    repo=Depends(get_job_repository),
    file_repo=Depends(get_job_file_repository),
    user: User = Depends(get_current_user),
) -> FileResponse:
    job = await repo.get_by_id_and_user(job_id, str(user.id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    job_file = await file_repo.get_by_id_and_job(file_id, job.id)
    if not job_file:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    rel_path = job_file.set_a_path if set_name == "A" else job_file.set_b_path
    if not rel_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    base = Path(settings.data_dir) / "jobs" / job_id / ("setA" if set_name == "A" else "setB")
    target = base / rel_path
    if not target.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="File not found")
    return FileResponse(path=str(target), media_type="application/pdf")


@router.get("/{job_id}/report")
async def get_job_report(
    job_id: str,
    service: JobService = Depends(get_job_service),
    repo=Depends(get_job_repository),
    user: User = Depends(get_current_user),
) -> Response:
    job = await repo.get_by_id_and_user(job_id, str(user.id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    
    report_bytes = await service.generate_report(job)
    
    return Response(
        content=report_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=diff-report-{job_id}.pdf"}
    )
