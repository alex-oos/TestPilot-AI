from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import GenerationBehaviorConfig


class GenerationBehaviorConfigRepository:
    @staticmethod
    async def list(db: AsyncSession) -> list[GenerationBehaviorConfig]:
        result = await db.execute(select(GenerationBehaviorConfig).order_by(GenerationBehaviorConfig.id.asc()))
        return list(result.scalars().all())

    @staticmethod
    async def clear(db: AsyncSession) -> int:
        result = await db.execute(delete(GenerationBehaviorConfig))
        return int(result.rowcount or 0)

    @staticmethod
    async def create(db: AsyncSession, **kwargs) -> GenerationBehaviorConfig:
        row = GenerationBehaviorConfig(**kwargs)
        db.add(row)
        await db.flush()
        return row

    @staticmethod
    async def get_by_config_id(db: AsyncSession, config_id: str) -> GenerationBehaviorConfig | None:
        result = await db.execute(select(GenerationBehaviorConfig).where(GenerationBehaviorConfig.config_id == config_id))
        return result.scalars().first()

    @staticmethod
    async def delete_by_config_id(db: AsyncSession, config_id: str) -> int:
        result = await db.execute(delete(GenerationBehaviorConfig).where(GenerationBehaviorConfig.config_id == config_id))
        return int(result.rowcount or 0)
