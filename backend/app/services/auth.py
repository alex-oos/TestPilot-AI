from fastapi import HTTPException
from loguru import logger
from app.schemas.user import LoginRequest

def authenticate_user(request: LoginRequest) -> dict:
    logger.info(f"Attempting login for user: {request.username}")
    if request.username == "admin" and request.password == "123456":
        logger.success(f"User {request.username} authenticated successfully.")
        return {"token": "mock-jwt-token-12345", "user": request.username}
    
    logger.warning(f"Failed login attempt for user: {request.username}")
    raise HTTPException(status_code=401, detail="账号或密码不正确")
