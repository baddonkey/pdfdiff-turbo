from fastapi import APIRouter, Depends

from app.features.auth.deps import get_auth_service, get_current_user
from app.features.auth.schemas import LoginCommand, LogoutCommand, RefreshCommand, RegisterCommand, TokenPairMessage, UserMessage
from app.features.auth.service import AuthService
from app.features.auth.models import User

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=UserMessage)
async def register(command: RegisterCommand, service: AuthService = Depends(get_auth_service)) -> UserMessage:
    return await service.register(command)


@router.post("/login", response_model=TokenPairMessage)
async def login(command: LoginCommand, service: AuthService = Depends(get_auth_service)) -> TokenPairMessage:
    return await service.login(command)


@router.post("/refresh", response_model=TokenPairMessage)
async def refresh(command: RefreshCommand, service: AuthService = Depends(get_auth_service)) -> TokenPairMessage:
    return await service.refresh(command)


@router.post("/logout")
async def logout(command: LogoutCommand, service: AuthService = Depends(get_auth_service)) -> dict:
    return await service.logout(command)


@router.get("/me", response_model=UserMessage)
async def me(user: User = Depends(get_current_user)) -> UserMessage:
    return UserMessage(
        id=str(user.id),
        email=user.email,
        role=user.role.value,
        is_active=user.is_active,
        created_at=user.created_at,
    )
