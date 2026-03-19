from typing import Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models import Task, TaskDetail, User


class TaskRepository:
    @staticmethod
    def create_task(
        db: Session,
        *,
        task_id: str,
        task_name: Optional[str],
        source_type: Optional[str],
        doc_url: Optional[str],
        status: str,
        status_text: Optional[str],
        user_id: Optional[int],
        created_at: str,
        updated_at: str,
    ) -> Task:
        task = Task(
            id=task_id,
            task_name=task_name,
            user_id=user_id,
            source_type=source_type,
            doc_url=doc_url,
            status=status,
            status_text=status_text,
            error=None,
            mindmap=None,
            created_at=created_at,
            updated_at=updated_at,
        )
        db.add(task)
        return task

    @staticmethod
    def create_task_detail(
        db: Session,
        *,
        task_id: str,
        phase_key: str,
        phase_label: str,
        status: str,
        created_at: str,
        updated_at: str,
    ) -> TaskDetail:
        detail = TaskDetail(
            task_id=task_id,
            phase_key=phase_key,
            phase_label=phase_label,
            status=status,
            data_json=None,
            error=None,
            created_at=created_at,
            updated_at=updated_at,
        )
        db.add(detail)
        return detail

    @staticmethod
    def get_task(db: Session, task_id: str) -> Optional[Task]:
        return db.scalar(select(Task).where(Task.id == task_id))

    @staticmethod
    def get_task_details(db: Session, task_id: str) -> list[TaskDetail]:
        return list(db.scalars(select(TaskDetail).where(TaskDetail.task_id == task_id)).all())

    @staticmethod
    def get_task_detail_by_phase(db: Session, task_id: str, phase_key: str) -> Optional[TaskDetail]:
        return db.scalar(
            select(TaskDetail).where(TaskDetail.task_id == task_id, TaskDetail.phase_key == phase_key)
        )

    @staticmethod
    def list_tasks(
        db: Session,
        *,
        page: int,
        page_size: int,
        task_name: Optional[str],
        task_id: Optional[str],
        source_type: Optional[str],
        status: Optional[str],
        submitter: Optional[str],
    ) -> Tuple[int, list[tuple[Task, Optional[str]]]]:
        stmt = select(Task, User.username).join(User, Task.user_id == User.id, isouter=True)

        if task_name:
            stmt = stmt.where(Task.task_name.like(f"%{task_name}%"))
        if task_id:
            stmt = stmt.where(Task.id.like(f"%{task_id}%"))
        if source_type:
            stmt = stmt.where(Task.source_type == source_type)
        if status:
            stmt = stmt.where(Task.status == status)
        if submitter:
            stmt = stmt.where(User.username.like(f"%{submitter}%"))

        total = int(db.scalar(select(func.count()).select_from(stmt.subquery())) or 0)
        rows = db.execute(
            stmt.order_by(Task.updated_at.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        ).all()
        return total, list(rows)
