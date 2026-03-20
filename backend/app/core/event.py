from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.db_initializer import init_db
from app.core.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    logger.info("Application started up successfully.")
    yield
    logger.info("Application shutting down.")
