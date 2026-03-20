from fastapi import APIRouter, Request

from app.core.response import success
from app.services import dashboard_service

router = APIRouter()


@router.get("/dashboard/overview")
async def get_dashboard_overview(request: Request):
    data = await dashboard_service.get_dashboard_overview()
    return success(data, request.state.tid)
