from fastapi import APIRouter
from app.api.endpoints import login, generate

api_router = APIRouter()
api_router.include_router(login.router, tags=["Authentication"])
api_router.include_router(generate.router, tags=["Use Cases Generation"])
