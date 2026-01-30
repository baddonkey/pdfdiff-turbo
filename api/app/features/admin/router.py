from fastapi import APIRouter, Depends

from app.features.admin.deps import get_admin_service
from app.features.admin.schemas import AdminJobMessage, AdminUserMessage, AdminUserUpdateCommand
from app.features.admin.service import AdminService
from app.features.auth.deps import require_admin
from app.features.auth.models import User

router = APIRouter(prefix="/admin", tags=["admin"], dependencies=[Depends(require_admin)])


@router.get("/jobs", response_model=list[AdminJobMessage])
async def list_jobs(service: AdminService = Depends(get_admin_service)) -> list[AdminJobMessage]:
    return await service.list_jobs()


@router.post("/jobs/{job_id}/cancel")
async def cancel_job(job_id: str, service: AdminService = Depends(get_admin_service)) -> dict:
    return await service.cancel_job(job_id)


@router.get("/users", response_model=list[AdminUserMessage])
async def list_users(service: AdminService = Depends(get_admin_service)) -> list[AdminUserMessage]:
    return await service.list_users()


@router.patch("/users/{user_id}", response_model=AdminUserMessage)
async def update_user(
    user_id: str,
    command: AdminUserUpdateCommand,
    service: AdminService = Depends(get_admin_service),
    admin: User = Depends(require_admin),
) -> AdminUserMessage:
    return await service.update_user(user_id, command)
