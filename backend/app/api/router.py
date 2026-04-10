from fastapi import APIRouter
from app.api.endpoints import login, task, config_center, dashboard

api_router = APIRouter()
api_router.include_router(login.router, tags=["Authentication"])
api_router.include_router(task.router, tags=["test Cases Generation"])
api_router.include_router(config_center.router, tags=["Config Center"])
api_router.include_router(dashboard.router, tags=["Dashboard"])
