from sqlalchemy.ext.asyncio import AsyncSession

from app.features.config.models import AppConfig
from app.features.config.repository import AppConfigRepository
from app.features.config.schemas import AppConfigMessage, AppConfigUpdateCommand


class AppConfigService:
    def __init__(self, session: AsyncSession, repo: AppConfigRepository):
        self._session = session
        self._repo = repo

    async def get_config(self) -> AppConfigMessage:
        config = await self._repo.get()
        if not config:
            config = AppConfig()
            self._repo.add(config)
            await self._session.commit()
            await self._session.refresh(config)
        return AppConfigMessage(
            allow_registration=config.allow_registration,
            enable_dropzone=config.enable_dropzone,
        )

    async def update_config(self, command: AppConfigUpdateCommand) -> AppConfigMessage:
        config = await self._repo.get()
        if not config:
            config = AppConfig()
            self._repo.add(config)
        if command.allow_registration is not None:
            config.allow_registration = command.allow_registration
        if command.enable_dropzone is not None:
            config.enable_dropzone = command.enable_dropzone
        await self._session.commit()
        await self._session.refresh(config)
        return AppConfigMessage(
            allow_registration=config.allow_registration,
            enable_dropzone=config.enable_dropzone,
        )
