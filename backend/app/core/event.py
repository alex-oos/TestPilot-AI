from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.db_initializer import init_db
from app.core.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    try:
        from app.ai.skills.health import assert_startup_health
        from app.ai.skills.audit import init_audit_storage
        assert_startup_health()
        await init_audit_storage()
    except RuntimeError:
        raise
    except Exception as exc:
        logger.warning("[skill] 启动检查异常（已降级）: {}", exc)
    logger.info("Application started up successfully.")
    yield
    logger.info("Application shutting down.")
