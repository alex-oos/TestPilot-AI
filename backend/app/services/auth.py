from datetime import datetime, timedelta, timezone

import jwt
from fastapi import HTTPException
from loguru import logger

from app.core import database
from app.core.config import settings
from app.schemas.user import LoginRequest


def _create_access_token(username: str) -> str:
    expire_at = datetime.now(timezone.utc) + timedelta(days=settings.JWT_EXPIRE_DAYS)
    payload = {
        "sub": username,
        "username": username,
        "exp": expire_at,
    }
    return jwt.encode(payload, settings.JWT_SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def authenticate_user(request: LoginRequest) -> dict:
    logger.info(f"Attempting login for user: {request.username}")

    user = database.get_user_by_username(request.username)
    if not user:
        logger.warning(f"Failed login attempt for user: {request.username} (not found)")
        raise HTTPException(status_code=401, detail="账号或密码不正确")

    if not user.get("is_active", 0):
        raise HTTPException(status_code=403, detail="账号已禁用")

    if request.password != user.get("password"):
        logger.warning(f"Failed login attempt for user: {request.username} (wrong password)")
        raise HTTPException(status_code=401, detail="账号或密码不正确")

    token = _create_access_token(request.username)
    logger.success(f"User {request.username} authenticated successfully.")
    return {
        "token": token,
        "user": request.username,
        "user_id": user["id"],
    }
