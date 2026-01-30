from pathlib import Path

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
from app.features.jobs.deps import get_job_service, get_job_repository, get_job_file_repository
from app.features.jobs.schemas import (
    JobCreatedMessage,
    JobFileMessage,
    JobPageMessage,
    JobStartedMessage,
    JobStatusMessage,
    JobSummaryMessage,
)
from app.features.jobs.service import JobService
from app.features.jobs.repository import JobRepository, JobPageResultRepository
from app.features.jobs.models import PageStatus

router = APIRouter(prefix="/jobs", tags=["jobs"])


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


@router.options("")
async def options_jobs() -> Response:
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("", response_model=JobCreatedMessage)
async def create_job(
    service: JobService = Depends(get_job_service),
    user: User = Depends(get_current_user),
) -> JobCreatedMessage:
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
    files: UploadFile | list[UploadFile] | None = File(default=None),
    relative_paths: str | list[str] | None = Form(default=None),
    service: JobService = Depends(get_job_service),
    repo=Depends(get_job_repository),
    user: User = Depends(get_current_user),
) -> dict:
    job = await repo.get_by_id_and_user(job_id, str(user.id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")

    if zip_file is not None:
        zip_bytes = await zip_file.read()
        await service.upload_zip(job, "setA" if set_name == "A" else "setB", zip_bytes)
        return {"status": "ok", "mode": "zip"}

    if files:
        file_list = files if isinstance(files, list) else [files]
        path_list: list[str] = []
        if isinstance(relative_paths, list):
            path_list = relative_paths
        elif isinstance(relative_paths, str):
            path_list = [relative_paths]

        if not path_list or len(path_list) != len(file_list):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="relative_paths required for multipart")
        payload = []
        for upload, rel in zip(file_list, path_list):
            payload.append((rel, await upload.read()))
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
) -> dict:
    job = await repo.get_by_id_and_user(job_id, str(user.id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    zip_bytes = await zip_file.read()
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
    return await service.start_job(job)


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
    user: User = Depends(get_current_user),
) -> list[JobFileMessage]:
    job = await repo.get_by_id_and_user(job_id, str(user.id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
    return await service.list_files(job)


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
