from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.config.models import AppConfig


class AppConfigRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get(self) -> AppConfig | None:
        result = await self._session.execute(select(AppConfig).order_by(AppConfig.id).limit(1))
        return result.scalar_one_or_none()

    def add(self, config: AppConfig) -> None:
        self._session.add(config)
