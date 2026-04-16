from fastapi import APIRouter, Depends, Request

from app.core.auth import get_current_user
from app.core.response import success
from app.services import dashboard_service

router = APIRouter()


@router.get("/dashboard")
async def get_dashboard_overview(request: Request, current_user: dict = Depends(get_current_user)):
    data = await dashboard_service.get_dashboard_overview()
    return success(data, request.state.tid)
