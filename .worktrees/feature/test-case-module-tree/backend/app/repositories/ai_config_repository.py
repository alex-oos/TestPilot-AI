from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AIConfig


class AIConfigRepository:
    @staticmethod
    async def list(db: AsyncSession) -> list[AIConfig]:
        result = await db.execute(select(AIConfig).order_by(AIConfig.id.asc()))
        return list(result.scalars().all())

    @staticmethod
    async def clear(db: AsyncSession) -> int:
        result = await db.execute(delete(AIConfig))
        return int(result.rowcount or 0)

    @staticmethod
    async def create(db: AsyncSession, **kwargs) -> AIConfig:
        row = AIConfig(**kwargs)
        db.add(row)
        await db.flush()
        return row

    @staticmethod
    async def get_by_config_id(db: AsyncSession, config_id: str) -> AIConfig | None:
        result = await db.execute(select(AIConfig).where(AIConfig.config_id == config_id))
        return result.scalars().first()

    @staticmethod
    async def delete_by_config_id(db: AsyncSession, config_id: str) -> int:
        result = await db.execute(delete(AIConfig).where(AIConfig.config_id == config_id))
        return int(result.rowcount or 0)
