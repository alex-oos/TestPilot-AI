from fastapi import APIRouter
from app.api.endpoints import login, generate, config_center, dashboard

api_router = APIRouter()
api_router.include_router(login.router, tags=["Authentication"])
api_router.include_router(generate.router, tags=["Use Cases Generation"])
api_router.include_router(config_center.router, tags=["Config Center"])
api_router.include_router(dashboard.router, tags=["Dashboard"])
