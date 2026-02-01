from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.features.auth.models import User
from app.features.auth.refresh_token_model import RefreshToken
from app.features.auth.repository import RefreshTokenRepository, UserRepository
from app.features.auth.schemas import ChangePasswordCommand, LoginCommand, LogoutCommand, RefreshCommand, RegisterCommand, TokenPairMessage, UserMessage
from app.features.auth.security import create_access_token, create_refresh_token, hash_password, verify_password


class AuthService:
    def __init__(self, session: AsyncSession, user_repo: UserRepository, token_repo: RefreshTokenRepository):
        self._session = session
        self._user_repo = user_repo
        self._token_repo = token_repo

    async def register(self, command: RegisterCommand) -> UserMessage:
        existing = await self._user_repo.get_by_email(command.email)
        if existing:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

        user = User(email=command.email, hashed_password=hash_password(command.password))
        self._user_repo.add(user)
        await self._session.commit()
        await self._session.refresh(user)
        return self._to_user_message(user)

    async def login(self, command: LoginCommand) -> TokenPairMessage:
        user = await self._user_repo.get_by_email(command.email)
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")
        if not verify_password(command.password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        access_token = create_access_token(str(user.id), user.role.value)
        refresh_raw, refresh_hash, expires_at = create_refresh_token()
        token = RefreshToken(user_id=user.id, token_hash=refresh_hash, expires_at=expires_at)
        self._token_repo.add(token)
        await self._session.commit()

        return TokenPairMessage(access_token=access_token, refresh_token=refresh_raw)

    async def refresh(self, command: RefreshCommand) -> TokenPairMessage:
        token = await self._token_repo.get_by_raw_token(command.refresh_token)
        if not token or token.revoked or self._token_repo.is_expired(token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid refresh token")

        user = await self._user_repo.get_by_id(str(token.user_id))
        if not user or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Inactive user")

        token.revoked = True
        access_token = create_access_token(str(user.id), user.role.value)
        refresh_raw, refresh_hash, expires_at = create_refresh_token()
        new_token = RefreshToken(user_id=user.id, token_hash=refresh_hash, expires_at=expires_at)
        self._token_repo.add(new_token)
        await self._session.commit()

        return TokenPairMessage(access_token=access_token, refresh_token=refresh_raw)

    async def logout(self, command: LogoutCommand) -> dict:
        token = await self._token_repo.get_by_raw_token(command.refresh_token)
        if token:
            token.revoked = True
            await self._session.commit()
        return {"status": "ok"}

    async def change_password(self, user: User, command: ChangePasswordCommand) -> dict:
        if not verify_password(command.current_password, user.hashed_password):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid credentials")

        user.hashed_password = hash_password(command.new_password)
        await self._session.commit()
        return {"status": "ok"}

    @staticmethod
    def _to_user_message(user: User) -> UserMessage:
        return UserMessage(
            id=str(user.id),
            email=user.email,
            role=user.role.value,
            is_active=user.is_active,
            created_at=user.created_at,
        )
