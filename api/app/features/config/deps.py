from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_session
from app.features.config.repository import AppConfigRepository
from app.features.config.service import AppConfigService


def get_app_config_repository(session: AsyncSession = Depends(get_session)) -> AppConfigRepository:
    return AppConfigRepository(session)


def get_app_config_service(
    session: AsyncSession = Depends(get_session),
    repo: AppConfigRepository = Depends(get_app_config_repository),
) -> AppConfigService:
    return AppConfigService(session, repo)
