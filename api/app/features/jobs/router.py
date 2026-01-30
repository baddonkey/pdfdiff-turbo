from pathlib import Path

from typing import Iterable

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Response, UploadFile, status
from fastapi.responses import FileResponse

from app.core.config import settings
from app.features.auth.deps import get_current_user
from app.features.auth.models import User
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

router = APIRouter(prefix="/jobs", tags=["jobs"])


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
    service: JobService = Depends(get_job_service),
    repo=Depends(get_job_repository),
    user: User = Depends(get_current_user),
) -> JobStartedMessage:
    job = await repo.get_by_id_and_user(job_id, str(user.id))
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Job not found")
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
