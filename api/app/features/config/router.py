from fastapi import APIRouter, Depends

from app.features.config.deps import get_app_config_service
from app.features.config.schemas import AppConfigMessage
from app.features.config.service import AppConfigService

router = APIRouter(prefix="/config", tags=["config"])


@router.get("", response_model=AppConfigMessage)
async def get_config(service: AppConfigService = Depends(get_app_config_service)) -> AppConfigMessage:
    return await service.get_config()
