from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.core.db_initializer import init_db
from app.core.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    try:
        from app.ai.skills.health import assert_startup_health
        from app.ai.skills.audit import init_audit_storage, purge_old
        from app.ai.llm_cache import init_cache_storage, purge_expired
        from app.core.config import settings
        assert_startup_health()
        await init_audit_storage()
        init_cache_storage()
        # 启动时清理过期数据
        try:
            n_audit = purge_old(int(getattr(settings, "AUDIT_RETENTION_DAYS", 30)))
            n_cache = purge_expired()
            if n_audit or n_cache:
                logger.info("[startup] retention 清理 audit={} llm_cache={}", n_audit, n_cache)
        except Exception as exc:
            logger.warning("[startup] retention 清理失败: {}", exc)
    except RuntimeError:
        raise
    except Exception as exc:
        logger.warning("[skill] 启动检查异常（已降级）: {}", exc)
    logger.info("Application started up successfully.")
    yield
    logger.info("Application shutting down.")
