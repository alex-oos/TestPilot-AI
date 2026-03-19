"""
Task Manager - task state backed by SQLite + in-memory cache for SSE polling.
Pipeline phases:
  upload -> analysis -> generation -> review -> notify
"""
import uuid
import asyncio
import json
from typing import Dict, Any, Optional, AsyncGenerator
from loguru import logger

from app.core import database


# in-memory cache to reduce repeated DB reads during active SSE sessions
_tasks: Dict[str, Dict[str, Any]] = {}


def create_task(
    task_name: Optional[str] = None,
    source_type: Optional[str] = None,
    doc_url: Optional[str] = None,
    file_name: Optional[str] = None,
    file_path: Optional[str] = None,
    status: str = "uploaded",
    status_text: Optional[str] = "文件已上传",
    user_id: Optional[int] = None,
    submitter: Optional[str] = None,
) -> str:
    """Create a new task, persist it in DB, and return task_id."""
    task_id = str(uuid.uuid4())
    if submitter and not user_id:
        user = database.ensure_user(submitter)
        user_id = user.get("id")

    database.create_task_record(
        task_id,
        task_name=task_name,
        source_type=source_type,
        doc_url=doc_url,
        file_name=file_name,
        file_path=file_path,
        status=status,
        status_text=status_text,
        user_id=user_id,
    )

    task = database.get_task_record(task_id)
    if task:
        _tasks[task_id] = task

    logger.info(f"Task created: {task_id}")
    return task_id


def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    task = _tasks.get(task_id)
    if task:
        return task

    task = database.get_task_record(task_id)
    if task:
        _tasks[task_id] = task
    return task


def update_phase(task_id: str, phase: str, status: str, data: Any = None):
    """Update a phase status: pending | running | completed | failed"""
    database.update_task_phase(task_id, phase, status, data=data)
    task = database.get_task_record(task_id)
    if task:
        _tasks[task_id] = task
    logger.debug(f"Task {task_id} | Phase '{phase}' -> {status}")


def set_task_status(task_id: str, status: str, error: str = None, status_text: str = None):
    database.update_task_status(task_id, status, error=error, status_text=status_text)
    task = database.get_task_record(task_id)
    if task:
        _tasks[task_id] = task


def set_task_mindmap(task_id: str, mindmap: str):
    database.update_task_mindmap(task_id, mindmap)
    task = database.get_task_record(task_id)
    if task:
        _tasks[task_id] = task


def set_task_decision(
    task_id: str,
    *,
    decision_status: str,
    decision_by: Optional[str] = None,
    decision_note: Optional[str] = None,
) -> bool:
    ok = database.update_task_decision(
        task_id,
        decision_status=decision_status,
        decision_by=decision_by,
        decision_note=decision_note,
    )
    task = database.get_task_record(task_id)
    if task:
        _tasks[task_id] = task
    return ok


def reset_task_for_retry(task_id: str, status_text: Optional[str] = None) -> Optional[Dict[str, Any]]:
    ok = database.reset_task_for_retry(task_id, status_text=status_text)
    if not ok:
        return None
    task = database.get_task_record(task_id)
    if task:
        _tasks[task_id] = task
    return task


def delete_task(task_id: str) -> bool:
    deleted = database.delete_task_record(task_id)
    _tasks.pop(task_id, None)
    return deleted


def delete_tasks(task_ids: list[str]) -> int:
    deleted_count = database.delete_task_records(task_ids)
    for task_id in task_ids:
        _tasks.pop(task_id, None)
    return deleted_count


def list_tasks(
    page: int = 1,
    page_size: int = 10,
    task_name: Optional[str] = None,
    task_id: Optional[str] = None,
    source_type: Optional[str] = None,
    status: Optional[str] = None,
    submitter: Optional[str] = None,
):
    return database.list_tasks(
        page=page,
        page_size=page_size,
        task_name=task_name,
        task_id=task_id,
        source_type=source_type,
        status=status,
        submitter=submitter,
    )


async def stream_task_events(task_id: str) -> AsyncGenerator[str, None]:
    """SSE generator: yields task state updates until task is completed or failed."""
    task = get_task(task_id)
    if not task:
        yield _sse_event({"error": "Task not found"})
        return

    while True:
        task = get_task(task_id)
        if not task:
            break

        yield _sse_event(task)

        if task["status"] in (
            "completed",
            "waiting_decision",
            "analysis_failed",
            "generation_failed",
            "review_failed",
            "failed",
        ):
            break

        await asyncio.sleep(0.8)


def _sse_event(data: Any) -> str:
    """Format as SSE event string."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\\n\\n"
