from fastapi import APIRouter, Depends

from app.features.auth.deps import get_current_user
from app.features.auth.models import User
from app.features.config.deps import get_app_config_service
from app.features.config.schemas import AppConfigMessage, PublicAppConfigMessage
from app.features.config.service import AppConfigService

router = APIRouter(prefix="/config", tags=["config"])


@router.get("", response_model=AppConfigMessage)
async def get_config(
    service: AppConfigService = Depends(get_app_config_service),
    _user: User = Depends(get_current_user),
) -> AppConfigMessage:
    return await service.get_config()


@router.get("/public", response_model=PublicAppConfigMessage)
async def get_public_config(
    service: AppConfigService = Depends(get_app_config_service),
) -> PublicAppConfigMessage:
    config = await service.get_config()
    return PublicAppConfigMessage(
        allow_registration=config.allow_registration,
        recaptcha_site_key=config.recaptcha_site_key,
    )
