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
            max_files_per_set=config.max_files_per_set,
            max_upload_mb=config.max_upload_mb,
            max_pages_per_job=config.max_pages_per_job,
            max_jobs_per_user_per_day=config.max_jobs_per_user_per_day,
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
        if command.max_files_per_set is not None:
            config.max_files_per_set = command.max_files_per_set
        if command.max_upload_mb is not None:
            config.max_upload_mb = command.max_upload_mb
        if command.max_pages_per_job is not None:
            config.max_pages_per_job = command.max_pages_per_job
        if command.max_jobs_per_user_per_day is not None:
            config.max_jobs_per_user_per_day = command.max_jobs_per_user_per_day
        await self._session.commit()
        await self._session.refresh(config)
        return AppConfigMessage(
            allow_registration=config.allow_registration,
            enable_dropzone=config.enable_dropzone,
            max_files_per_set=config.max_files_per_set,
            max_upload_mb=config.max_upload_mb,
            max_pages_per_job=config.max_pages_per_job,
            max_jobs_per_user_per_day=config.max_jobs_per_user_per_day,
        )
