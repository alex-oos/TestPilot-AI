from typing import Dict, Optional

from app.modules.domain import user_domain


async def get_user_by_username(username: str) -> Optional[Dict[str, object]]:
    return await user_domain.get_user_by_username(username)


async def update_user_password_hash(username: str, password_hash: str) -> bool:
    return await user_domain.update_user_password_hash(username, password_hash)


async def ensure_user(username: str, password: str = "123456") -> Dict[str, object]:
    return await user_domain.ensure_user(username, password=password)
