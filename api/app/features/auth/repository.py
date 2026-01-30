import hashlib
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models import User
from app.features.auth.refresh_token_model import RefreshToken


class UserRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_email(self, email: str) -> Optional[User]:
        result = await self._session.execute(select(User).where(User.email == email))
        return result.scalar_one_or_none()

    async def get_by_id(self, user_id: str) -> Optional[User]:
        result = await self._session.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()

    def add(self, user: User) -> None:
        self._session.add(user)


class RefreshTokenRepository:
    def __init__(self, session: AsyncSession):
        self._session = session

    async def get_by_raw_token(self, raw_token: str) -> Optional[RefreshToken]:
        token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
        result = await self._session.execute(select(RefreshToken).where(RefreshToken.token_hash == token_hash))
        return result.scalar_one_or_none()

    def add(self, token: RefreshToken) -> None:
        self._session.add(token)

    @staticmethod
    def is_expired(token: RefreshToken) -> bool:
        return token.expires_at <= datetime.now(timezone.utc)
