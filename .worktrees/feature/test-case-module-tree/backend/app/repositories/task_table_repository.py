from typing import Optional

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Task, User


class TaskTableRepository:
    HIDDEN_STATUSES = {"quality_blocked"}
    @staticmethod
    async def create(
        db: AsyncSession,
        *,
        task_id: str,
        task_name: Optional[str],
        source_type: Optional[str],
        doc_url: Optional[str],
        file_name: Optional[str],
        file_path: Optional[str],
        status: str,
        status_text: Optional[str],
        user_id: Optional[int],
        created_at: str,
        updated_at: str,
    ) -> Task:
        row = Task(
            id=task_id,
            task_name=task_name,
            user_id=user_id,
            source_type=source_type,
            doc_url=doc_url,
            file_name=file_name,
            file_path=file_path,
            status=status,
            status_text=status_text,
            decision_status=None,
            decision_by=None,
            decision_note=None,
            decision_at=None,
            error=None,
            mindmap=None,
            feishu_mindmap_url=None,
            created_at=created_at,
            updated_at=updated_at,
        )
        db.add(row)
        await db.flush()
        return row

    @staticmethod
    async def get_by_id(db: AsyncSession, task_id: str) -> Optional[Task]:
        result = await db.execute(select(Task).where(Task.id == task_id))
        return result.scalars().first()

    @staticmethod
    async def list_with_submitter(
        db: AsyncSession,
        *,
        page: int,
        page_size: int,
        task_name: Optional[str],
        task_id: Optional[str],
        source_type: Optional[str],
        status: Optional[str],
        submitter: Optional[str],
    ):
        stmt = select(Task, User.username).outerjoin(User, Task.user_id == User.id)
        if task_name:
            stmt = stmt.where(Task.task_name.like(f"%{task_name}%"))
        if task_id:
            stmt = stmt.where(Task.id.like(f"%{task_id}%"))
        if source_type:
            stmt = stmt.where(Task.source_type == source_type)
        if status:
            stmt = stmt.where(Task.status == status)
        else:
            stmt = stmt.where(Task.status.notin_(tuple(TaskTableRepository.HIDDEN_STATUSES)))
        if submitter:
            stmt = stmt.where(User.username.like(f"%{submitter}%"))

        total_stmt = select(func.count()).select_from(stmt.subquery())
        total_result = await db.execute(total_stmt)
        total = int(total_result.scalar() or 0)

        paged_stmt = stmt.order_by(Task.updated_at.desc()).offset((page - 1) * page_size).limit(page_size)
        rows_result = await db.execute(paged_stmt)
        return total, list(rows_result.all())

    @staticmethod
    async def count_all(db: AsyncSession) -> int:
        result = await db.execute(select(func.count()).select_from(Task))
        return int(result.scalar() or 0)

    @staticmethod
    async def count_by_status(db: AsyncSession) -> dict[str, int]:
        result = await db.execute(select(Task.status, func.count()).group_by(Task.status))
        rows = result.all()
        return {str(status or ""): int(count or 0) for status, count in rows}

    @staticmethod
    async def count_by_source_type(db: AsyncSession) -> dict[str, int]:
        result = await db.execute(select(Task.source_type, func.count()).group_by(Task.source_type))
        rows = result.all()
        return {str(source_type or ""): int(count or 0) for source_type, count in rows}

    @staticmethod
    async def list_all(db: AsyncSession) -> list[Task]:
        result = await db.execute(select(Task))
        return list(result.scalars().all())

    @staticmethod
    async def delete_by_ids(db: AsyncSession, task_ids: list[str]) -> int:
        if not task_ids:
            return 0
        result = await db.execute(delete(Task).where(Task.id.in_(task_ids)))
        return int(result.rowcount or 0)
