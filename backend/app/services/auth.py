from fastapi import HTTPException
from loguru import logger

from app.core import database
from app.schemas.user import LoginRequest


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

    logger.success(f"User {request.username} authenticated successfully.")
    return {
        "token": "mock-jwt-token-12345",
        "user": request.username,
        "user_id": user["id"],
    }
