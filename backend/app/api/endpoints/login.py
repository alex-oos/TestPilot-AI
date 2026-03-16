from fastapi import APIRouter
from app.schemas.user import LoginRequest
from app.services.auth import authenticate_user

router = APIRouter()

@router.post("/login")
async def login(request: LoginRequest):
    return authenticate_user(request)
