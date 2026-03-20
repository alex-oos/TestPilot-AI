from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import NotificationConfig


class NotificationConfigRepository:
    @staticmethod
    async def list(db: AsyncSession) -> list[NotificationConfig]:
        result = await db.execute(select(NotificationConfig).order_by(NotificationConfig.id.asc()))
        return list(result.scalars().all())

    @staticmethod
    async def clear(db: AsyncSession) -> int:
        result = await db.execute(delete(NotificationConfig))
        return int(result.rowcount or 0)

    @staticmethod
    async def create(db: AsyncSession, **kwargs) -> NotificationConfig:
        row = NotificationConfig(**kwargs)
        db.add(row)
        await db.flush()
        return row

    @staticmethod
    async def get_by_channel(db: AsyncSession, channel: str) -> NotificationConfig | None:
        result = await db.execute(select(NotificationConfig).where(NotificationConfig.channel == channel))
        return result.scalars().first()

    @staticmethod
    async def delete_by_channel(db: AsyncSession, channel: str) -> int:
        result = await db.execute(delete(NotificationConfig).where(NotificationConfig.channel == channel))
        return int(result.rowcount or 0)
