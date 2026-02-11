from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, WebSocket, WebSocketDisconnect, status
from fastapi.responses import FileResponse
from jose import JWTError

from app.core.report_ws import report_ws_manager
from app.features.auth.deps import get_current_user, get_user_repository
from app.features.auth.models import User
from app.features.auth.security import decode_token
from app.features.reports.deps import get_report_repository, get_report_service
from app.features.reports.models import ReportStatus, ReportType
from app.features.reports.repository import ReportRepository
from app.features.reports.schemas import ReportCreateCommand, ReportMessage
from app.features.reports.service import ReportService

router = APIRouter(prefix="/reports", tags=["reports"])


@router.post("", response_model=ReportMessage)
async def create_report(
    command: ReportCreateCommand,
    service: ReportService = Depends(get_report_service),
    user: User = Depends(get_current_user),
) -> ReportMessage:
    return await service.create_report(user, command)


@router.get("", response_model=list[ReportMessage])
async def list_reports(
    source_job_id: str | None = Query(default=None, alias="source_job_id"),
    service: ReportService = Depends(get_report_service),
    user: User = Depends(get_current_user),
) -> list[ReportMessage]:
    return await service.list_reports(user, source_job_id)


@router.get("/{report_id}", response_model=ReportMessage)
async def get_report(
    report_id: str,
    service: ReportService = Depends(get_report_service),
    user: User = Depends(get_current_user),
) -> ReportMessage:
    return await service.get_report(user, report_id)


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    report_type: ReportType = Query(ReportType.visual, alias="type"),
    repo: ReportRepository = Depends(get_report_repository),
    user: User = Depends(get_current_user),
) -> FileResponse:
    report = await repo.get_by_id_and_user(report_id, str(user.id))
    if not report:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")
    if report.status != ReportStatus.done:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Report is not ready")
    if report_type == ReportType.text:
        path_value = report.text_path
        filename = report.text_filename
        media_type = "text/plain; charset=utf-8"
    elif report_type == ReportType.both:
        path_value = report.bundle_path
        filename = report.bundle_filename
        media_type = "application/zip"
    else:
        path_value = report.visual_path
        filename = report.visual_filename
        media_type = "application/pdf"

    if not path_value:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report output missing")
    path = Path(path_value)
    if not path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report output missing")

    return FileResponse(path, media_type=media_type, filename=filename or path.name)


@router.websocket("/ws")
async def reports_ws(
    websocket: WebSocket,
    token: str | None = Query(default=None),
    user_repo=Depends(get_user_repository),
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
    await report_ws_manager.connect(str(user.id), websocket)
    try:
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        await report_ws_manager.disconnect(str(user.id), websocket)


