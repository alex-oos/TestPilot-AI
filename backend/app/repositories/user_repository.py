from typing import Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User


class UserRepository:
    @staticmethod
    async def get_by_username(db: AsyncSession, username: str) -> Optional[User]:
        result = await db.execute(select(User).where(User.username == username))
        return result.scalars().first()

    @staticmethod
    async def create(db: AsyncSession, *, username: str, password: str, created_at: str, updated_at: str) -> User:
        user = User(
            username=username,
            password=password,
            is_active=True,
            created_at=created_at,
            updated_at=updated_at,
        )
        db.add(user)
        await db.flush()
        return user

    @staticmethod
    async def update_password(db: AsyncSession, user: User, *, password: str, updated_at: str) -> User:
        user.password = password
        user.updated_at = updated_at
        db.add(user)
        await db.flush()
        return user
