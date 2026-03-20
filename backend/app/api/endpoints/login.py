from fastapi import APIRouter, Request

from app.core.response import success
from app.schemas.user import LoginRequest
from app.services.auth import authenticate_user

router = APIRouter()

@router.post("/auth/tokens")
async def login(request: Request, payload: LoginRequest):
    data = await authenticate_user(payload)
    return success(data, request.state.tid)
