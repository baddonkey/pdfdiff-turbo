import asyncio
import os

from sqlalchemy import select

from app.db.session import SessionLocal
from app.features.auth.models import User, UserRole
from app.features.auth.security import hash_password


def _get_env(name: str, default: str) -> str:
    value = os.getenv(name)
    return value if value else default


async def seed_users() -> None:
    admin_email = _get_env("SEED_ADMIN_EMAIL", "admin@example.com")
    admin_password = _get_env("SEED_ADMIN_PASSWORD", "admin123")
    user_email = _get_env("SEED_USER_EMAIL", "user@example.com")
    user_password = _get_env("SEED_USER_PASSWORD", "user123")

    async with SessionLocal() as session:
        result = await session.execute(select(User).where(User.email.in_([admin_email, user_email])))
        existing = {user.email for user in result.scalars().all()}

        if admin_email not in existing:
            session.add(
                User(
                    email=admin_email,
                    hashed_password=hash_password(admin_password),
                    role=UserRole.admin,
                )
            )

        if user_email not in existing:
            session.add(
                User(
                    email=user_email,
                    hashed_password=hash_password(user_password),
                    role=UserRole.user,
                )
            )

        await session.commit()


def main() -> None:
    asyncio.run(seed_users())


if __name__ == "__main__":
    main()
