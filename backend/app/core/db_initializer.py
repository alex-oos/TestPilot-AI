from sqlalchemy import inspect, text
from loguru import logger

from app.core.database import async_engine
from app.models import Base
from app.modules.domain import config_center_domain, user_domain


async def init_db() -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def _table_missing_custom_keyword(sync_conn) -> bool:
            inspector = inspect(sync_conn)
            if not inspector.has_table("notification_configs"):
                return False
            columns = {col.get("name") for col in inspector.get_columns("notification_configs")}
            return "custom_keyword" not in columns

        missing_custom_keyword = await conn.run_sync(_table_missing_custom_keyword)
        if missing_custom_keyword:
            await conn.execute(text("ALTER TABLE notification_configs ADD COLUMN custom_keyword VARCHAR DEFAULT ''"))
    await user_domain.ensure_user("admin", password="123456")
    # await config_center_domain.seed_default_config_center()
    logger.info("SQLAlchemy initialized")
