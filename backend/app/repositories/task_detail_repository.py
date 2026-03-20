from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TaskDetail


class TaskDetailRepository:
    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        task_id: str,
        phase_key: str,
        phase_label: str,
        status: str,
        created_at: str,
        updated_at: str,
    ) -> TaskDetail:
        row = TaskDetail(
            task_id=task_id,
            phase_key=phase_key,
            phase_label=phase_label,
            status=status,
            data_json=None,
            error=None,
            created_at=created_at,
            updated_at=updated_at,
        )
        db.add(row)
        await db.flush()
        return row

    @staticmethod
    async def list_by_task_id(db: AsyncSession, task_id: str) -> list[TaskDetail]:
        result = await db.execute(select(TaskDetail).where(TaskDetail.task_id == task_id))
        return list(result.scalars().all())

    @staticmethod
    async def get_by_task_phase(db: AsyncSession, task_id: str, phase_key: str) -> Optional[TaskDetail]:
        result = await db.execute(
            select(TaskDetail).where(TaskDetail.task_id == task_id, TaskDetail.phase_key == phase_key)
        )
        return result.scalars().first()

    @staticmethod
    async def delete_by_task_ids(db: AsyncSession, task_ids: list[str]) -> int:
        if not task_ids:
            return 0
        result = await db.execute(delete(TaskDetail).where(TaskDetail.task_id.in_(task_ids)))
        return int(result.rowcount or 0)
