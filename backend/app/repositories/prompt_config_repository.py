from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import PromptConfig


class PromptConfigRepository:
    @staticmethod
    async def list(db: AsyncSession) -> list[PromptConfig]:
        result = await db.execute(select(PromptConfig).order_by(PromptConfig.id.asc()))
        return list(result.scalars().all())

    @staticmethod
    async def clear(db: AsyncSession) -> int:
        result = await db.execute(delete(PromptConfig))
        return int(result.rowcount or 0)

    @staticmethod
    async def create(db: AsyncSession, **kwargs) -> PromptConfig:
        row = PromptConfig(**kwargs)
        db.add(row)
        await db.flush()
        return row

    @staticmethod
    async def get_by_config_id(db: AsyncSession, config_id: str) -> PromptConfig | None:
        result = await db.execute(select(PromptConfig).where(PromptConfig.config_id == config_id))
        return result.scalars().first()

    @staticmethod
    async def delete_by_config_id(db: AsyncSession, config_id: str) -> int:
        result = await db.execute(delete(PromptConfig).where(PromptConfig.config_id == config_id))
        return int(result.rowcount or 0)
