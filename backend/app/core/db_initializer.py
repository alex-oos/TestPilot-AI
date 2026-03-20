from loguru import logger

from app.core.database import async_engine
from app.models import Base
from app.modules.domain import config_center_domain, user_domain


async def init_db() -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await user_domain.ensure_user("admin", password="123456")
    await config_center_domain.seed_default_config_center()
    logger.info("SQLAlchemy initialized")
