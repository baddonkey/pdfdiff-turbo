from fastapi import APIRouter, Depends, HTTPException, Request, status
import httpx

from app.features.auth.deps import get_auth_service, get_current_user
from app.features.auth.schemas import ChangePasswordCommand, LoginCommand, LogoutCommand, RefreshCommand, RegisterCommand, TokenPairMessage, UserMessage
from app.features.auth.service import AuthService
from app.features.auth.models import User
from app.features.config.deps import get_app_config_service
from app.features.config.service import AppConfigService
from app.core.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])


async def _verify_recaptcha(token: str, remote_ip: str | None, action: str) -> None:
    if not settings.recaptcha_secret_key:
        return
    payload = {
        "secret": settings.recaptcha_secret_key,
        "response": token,
    }
    if remote_ip:
        payload["remoteip"] = remote_ip
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post("https://www.google.com/recaptcha/api/siteverify", data=payload)
            response.raise_for_status()
            result = response.json()
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="Captcha verification failed") from exc

    if not result.get("success"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Captcha validation failed")
    score = result.get("score")
    if score is not None and score < settings.recaptcha_min_score:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Captcha score too low")
    expected_action = settings.recaptcha_action or "register"
    if result.get("action") and result.get("action") != expected_action:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Captcha action mismatch")


@router.post("/register", response_model=UserMessage)
async def register(
    command: RegisterCommand,
    request: Request,
    service: AuthService = Depends(get_auth_service),
    config_service: AppConfigService = Depends(get_app_config_service),
) -> UserMessage:
    config = await config_service.get_config()
    if not config.allow_registration:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Registration disabled")
    if settings.recaptcha_secret_key and settings.recaptcha_site_key:
        if not command.captcha_token:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Captcha required")
        remote_ip = request.client.host if request.client else None
        action = command.captcha_action or settings.recaptcha_action
        await _verify_recaptcha(command.captcha_token, remote_ip, action)
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


@router.post("/change-password")
async def change_password(
    command: ChangePasswordCommand,
    user: User = Depends(get_current_user),
    service: AuthService = Depends(get_auth_service),
) -> dict:
    return await service.change_password(user, command)
