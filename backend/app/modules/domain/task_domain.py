import json
from typing import Any, Dict, List, Optional

from app.core.database import AsyncSessionLocal, transactional_session
from app.util.time_utils import to_beijing_time_text, utc_now_text
from app.repositories import TaskDetailRepository, TaskTableRepository


async def create_task_record(
    task_id: str,
    task_name: Optional[str],
    source_type: Optional[str],
    doc_url: Optional[str],
    file_name: Optional[str] = None,
    file_path: Optional[str] = None,
    status: str = "uploaded",
    status_text: Optional[str] = "文件已上传",
    user_id: Optional[int] = None,
) -> None:
    now = utc_now_text()
    async with transactional_session() as db:
        await TaskTableRepository.create(
            db,
            task_id=task_id,
            task_name=task_name,
            source_type=source_type,
            doc_url=doc_url,
            file_name=file_name,
            file_path=file_path,
            status=status,
            status_text=status_text,
            user_id=user_id,
            created_at=now,
            updated_at=now,
        )
        for phase_key, phase_label, phase_status in (
            ("upload", "文件上传", "completed"),
            ("analysis", "需求分析", "pending"),
            ("generation", "用例编写", "pending"),
            ("review", "用例评审", "pending"),
            ("manual_review", "人工审核", "pending"),
        ):
            await TaskDetailRepository.create(
                db,
                task_id=task_id,
                phase_key=phase_key,
                phase_label=phase_label,
                status=phase_status,
                created_at=now,
                updated_at=now,
            )


async def reset_task_for_retry(task_id: str, status_text: Optional[str] = None) -> bool:
    now = utc_now_text()
    async with transactional_session() as db:
        task = await TaskTableRepository.get_by_id(db, task_id)
        found = task is not None
        if not found:
            return False
        task.status = "running"
        task.status_text = status_text
        task.error = None
        task.mindmap = None
        task.decision_status = None
        task.decision_by = None
        task.decision_note = None
        task.decision_at = None
        task.updated_at = now
        details = await TaskDetailRepository.list_by_task_id(db, task_id)
        for detail in details:
            detail.status = "completed" if detail.phase_key == "upload" else "pending"
            detail.data_json = None
            detail.error = None
            detail.updated_at = now
        return True


async def update_task_status(
    task_id: str,
    status: str,
    error: Optional[str] = None,
    status_text: Optional[str] = None,
) -> None:
    now = utc_now_text()
    async with transactional_session() as db:
        task = await TaskTableRepository.get_by_id(db, task_id)
        if not task:
            return
        task.status = status
        task.error = error
        if status_text is not None:
            task.status_text = status_text
        task.updated_at = now


async def update_task_mindmap(task_id: str, mindmap: str) -> None:
    now = utc_now_text()
    async with transactional_session() as db:
        task = await TaskTableRepository.get_by_id(db, task_id)
        if not task:
            return
        task.mindmap = mindmap
        task.updated_at = now


async def update_task_phase(
    task_id: str,
    phase_key: str,
    status: str,
    data: Optional[Any] = None,
    error: Optional[str] = None,
) -> None:
    now = utc_now_text()
    async with transactional_session() as db:
        detail = await TaskDetailRepository.get_by_task_phase(db, task_id, phase_key)
        if not detail:
            return
        detail.status = status
        if data is not None:
            detail.data_json = json.dumps(data, ensure_ascii=False)
        detail.error = error
        detail.updated_at = now


async def get_task_record(task_id: str) -> Optional[Dict[str, Any]]:
    async with AsyncSessionLocal() as db:
        task = await TaskTableRepository.get_by_id(db, task_id)
        if not task:
            return None
        details = await TaskDetailRepository.list_by_task_id(db, task_id)

    phases: Dict[str, Dict[str, Any]] = {}
    for row in details:
        parsed_data = None
        if row.data_json:
            try:
                parsed_data = json.loads(row.data_json)
            except json.JSONDecodeError:
                parsed_data = None
        phases[row.phase_key] = {
            "status": row.status,
            "label": row.phase_label,
            "data": parsed_data,
        }

    return {
        "id": task.id,
        "task_name": task.task_name,
        "user_id": task.user_id,
        "source_type": task.source_type,
        "doc_url": task.doc_url,
        "file_name": task.file_name,
        "file_path": task.file_path,
        "status": task.status,
        "status_text": task.status_text,
        "decision_status": task.decision_status,
        "decision_by": task.decision_by,
        "decision_note": task.decision_note,
        "decision_at": to_beijing_time_text(task.decision_at),
        "phases": phases,
        "mindmap": task.mindmap,
        "error": task.error,
    }


async def list_tasks(
    page: int = 1,
    page_size: int = 10,
    task_name: Optional[str] = None,
    task_id: Optional[str] = None,
    source_type: Optional[str] = None,
    status: Optional[str] = None,
    submitter: Optional[str] = None,
) -> Dict[str, Any]:
    async with AsyncSessionLocal() as db:
        total, rows = await TaskTableRepository.list_with_submitter(
            db,
            page=page,
            page_size=page_size,
            task_name=task_name,
            task_id=task_id,
            source_type=source_type,
            status=status,
            submitter=submitter,
        )

    items = []
    for task, username in rows:
        items.append(
            {
                "id": task.id,
                "task_name": task.task_name or "",
                "user_id": task.user_id,
                "source_type": task.source_type,
                "doc_url": task.doc_url,
                "file_name": task.file_name,
                "status": task.status,
                "status_text": task.status_text,
                "decision_status": task.decision_status,
                "error": task.error,
                "created_at": to_beijing_time_text(task.created_at),
                "updated_at": to_beijing_time_text(task.updated_at),
                "submitter": username or "admin",
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


async def delete_task_record(task_id: str) -> bool:
    return await delete_task_records([task_id]) > 0


async def delete_task_records(task_ids: List[str]) -> int:
    unique_task_ids = [x for x in dict.fromkeys(task_ids or []) if x]
    if not unique_task_ids:
        return 0

    async with transactional_session() as db:
        await TaskDetailRepository.delete_by_task_ids(db, unique_task_ids)
        deleted_count = await TaskTableRepository.delete_by_ids(db, unique_task_ids)
    return deleted_count


async def update_task_decision(
    task_id: str,
    *,
    decision_status: str,
    decision_by: Optional[str] = None,
    decision_note: Optional[str] = None,
) -> bool:
    now = utc_now_text()
    async with transactional_session() as db:
        task = await TaskTableRepository.get_by_id(db, task_id)
        if not task:
            return False
        task.decision_status = decision_status
        task.decision_by = decision_by
        task.decision_note = decision_note
        task.decision_at = now
        task.updated_at = now
        return True
