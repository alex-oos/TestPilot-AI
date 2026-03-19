from typing import Optional, Tuple

from sqlalchemy import delete, func, select
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
        file_name: Optional[str],
        file_path: Optional[str],
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

    @staticmethod
    def count_tasks(db: Session) -> int:
        return int(db.scalar(select(func.count()).select_from(Task)) or 0)

    @staticmethod
    def count_tasks_by_status(db: Session) -> dict[str, int]:
        rows = db.execute(
            select(Task.status, func.count()).group_by(Task.status)
        ).all()
        return {str(status or ""): int(count or 0) for status, count in rows}

    @staticmethod
    def count_tasks_by_source_type(db: Session) -> dict[str, int]:
        rows = db.execute(
            select(Task.source_type, func.count()).group_by(Task.source_type)
        ).all()
        return {str(source_type or ""): int(count or 0) for source_type, count in rows}

    @staticmethod
    def list_tasks_basic(db: Session) -> list[Task]:
        return list(db.scalars(select(Task)).all())

    @staticmethod
    def reset_task_for_retry(
        db: Session,
        *,
        task_id: str,
        status: str,
        status_text: Optional[str],
        updated_at: str,
    ) -> bool:
        task = TaskRepository.get_task(db, task_id)
        if not task:
            return False
        task.status = status
        task.status_text = status_text
        task.error = None
        task.mindmap = None
        task.decision_status = None
        task.decision_by = None
        task.decision_note = None
        task.decision_at = None
        task.updated_at = updated_at
        return True

    @staticmethod
    def reset_task_details_for_retry(db: Session, *, task_id: str, updated_at: str) -> int:
        details = TaskRepository.get_task_details(db, task_id)
        for detail in details:
            detail.status = "completed" if detail.phase_key == "upload" else "pending"
            detail.data_json = None
            detail.error = None
            detail.updated_at = updated_at
        return len(details)

    @staticmethod
    def delete_task_details_by_task_ids(db: Session, task_ids: list[str]) -> int:
        if not task_ids:
            return 0
        result = db.execute(delete(TaskDetail).where(TaskDetail.task_id.in_(task_ids)))
        return int(result.rowcount or 0)

    @staticmethod
    def delete_tasks_by_ids(db: Session, task_ids: list[str]) -> int:
        if not task_ids:
            return 0
        result = db.execute(delete(Task).where(Task.id.in_(task_ids)))
        return int(result.rowcount or 0)
