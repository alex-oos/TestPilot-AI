from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import RoleConfig


class RoleConfigRepository:
    @staticmethod
    async def list(db: AsyncSession) -> list[RoleConfig]:
        result = await db.execute(select(RoleConfig).order_by(RoleConfig.id.asc()))
        return list(result.scalars().all())

    @staticmethod
    async def get_by_config_id(db: AsyncSession, config_id: str) -> RoleConfig | None:
        result = await db.execute(select(RoleConfig).where(RoleConfig.config_id == config_id))
        return result.scalars().first()

    @staticmethod
    async def clear(db: AsyncSession) -> int:
        result = await db.execute(delete(RoleConfig))
        return int(result.rowcount or 0)

    @staticmethod
    async def create(db: AsyncSession, **kwargs) -> RoleConfig:
        row = RoleConfig(**kwargs)
        db.add(row)
        await db.flush()
        return row

    @staticmethod
    async def delete_by_config_id(db: AsyncSession, config_id: str) -> int:
        result = await db.execute(delete(RoleConfig).where(RoleConfig.config_id == config_id))
        return int(result.rowcount or 0)
