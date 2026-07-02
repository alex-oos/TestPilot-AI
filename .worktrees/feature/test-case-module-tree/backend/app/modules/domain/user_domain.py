from typing import Any, Dict, Optional

from app.core.database import AsyncSessionLocal, transactional_session
from app.util.time_utils import to_beijing_time_text, utc_now_text
from app.repositories import UserRepository
from app.security.password_hasher import hash_password


async def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    async with AsyncSessionLocal() as db:
        user = await UserRepository.get_by_username(db, username)
        if not user:
            return None
        return {
            "id": user.id,
            "username": user.username,
            "password": user.password,
            "is_active": user.is_active,
            "created_at": to_beijing_time_text(user.created_at),
            "updated_at": to_beijing_time_text(user.updated_at),
        }


async def ensure_user(username: str, password: str = "123456") -> Dict[str, Any]:
    existing = await get_user_by_username(username)
    if existing:
        return existing

    now = utc_now_text()
    async with transactional_session() as db:
        user = await UserRepository.create(
            db,
            username=username,
            password=hash_password(password),
            created_at=now,
            updated_at=now,
        )
        return {
            "id": user.id,
            "username": user.username,
            "password": user.password,
            "is_active": user.is_active,
            "created_at": to_beijing_time_text(user.created_at),
            "updated_at": to_beijing_time_text(user.updated_at),
        }


async def update_user_password_hash(username: str, password_hash: str) -> bool:
    now = utc_now_text()
    async with transactional_session() as db:
        user = await UserRepository.get_by_username(db, username)
        if not user:
            return False
        await UserRepository.update_password(db, user, password=password_hash, updated_at=now)
        return True
