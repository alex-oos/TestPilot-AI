"""
Task Manager - task state backed by SQLite + in-memory cache for SSE polling.
Pipeline phases:
  upload -> analysis -> generation -> review -> manual_review
"""
import asyncio
import json
import uuid
from typing import Any, AsyncGenerator, Dict, Optional

from loguru import logger

from app.modules.persistence import task_store


_tasks: Dict[str, Dict[str, Any]] = {}


async def create_task(
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
    task_id = str(uuid.uuid4())
    if submitter and not user_id:
        user = await task_store.ensure_user(submitter)
        user_id = user.get("id")

    await task_store.create_task_record(
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

    task = await task_store.get_task_record(task_id)
    if task:
        _tasks[task_id] = task

    logger.info(f"Task created: {task_id}")
    return task_id


async def get_task(task_id: str) -> Optional[Dict[str, Any]]:
    task = _tasks.get(task_id)
    if task:
        return task

    task = await task_store.get_task_record(task_id)
    if task:
        _tasks[task_id] = task
    return task


async def update_phase(task_id: str, phase: str, status: str, data: Any = None, error: str = None):
    await task_store.update_task_phase(task_id, phase, status, data=data, error=error)
    task = await task_store.get_task_record(task_id)
    if task:
        _tasks[task_id] = task
    logger.debug(f"Task {task_id} | Phase '{phase}' -> {status}")


async def set_task_status(task_id: str, status: str, error: str = None, status_text: str = None):
    await task_store.update_task_status(task_id, status, error=error, status_text=status_text)
    task = await task_store.get_task_record(task_id)
    if task:
        _tasks[task_id] = task


async def set_task_mindmap(task_id: str, mindmap: str):
    await task_store.update_task_mindmap(task_id, mindmap)
    task = await task_store.get_task_record(task_id)
    if task:
        _tasks[task_id] = task


async def set_task_decision(
    task_id: str,
    *,
    decision_status: str,
    decision_by: Optional[str] = None,
    decision_note: Optional[str] = None,
) -> bool:
    ok = await task_store.update_task_decision(
        task_id,
        decision_status=decision_status,
        decision_by=decision_by,
        decision_note=decision_note,
    )
    task = await task_store.get_task_record(task_id)
    if task:
        _tasks[task_id] = task
    return ok


async def reset_task_for_retry(task_id: str, status_text: Optional[str] = None) -> Optional[Dict[str, Any]]:
    ok = await task_store.reset_task_for_retry(task_id, status_text=status_text)
    if not ok:
        return None
    task = await task_store.get_task_record(task_id)
    if task:
        _tasks[task_id] = task
    return task


async def delete_task(task_id: str) -> bool:
    deleted = await task_store.delete_task_record(task_id)
    _tasks.pop(task_id, None)
    return deleted


async def delete_tasks(task_ids: list[str]) -> int:
    deleted_count = await task_store.delete_task_records(task_ids)
    for task_id in task_ids:
        _tasks.pop(task_id, None)
    return deleted_count


async def list_tasks(
    page: int = 1,
    page_size: int = 10,
    task_name: Optional[str] = None,
    task_id: Optional[str] = None,
    source_type: Optional[str] = None,
    status: Optional[str] = None,
    submitter: Optional[str] = None,
):
    return await task_store.list_tasks(
        page=page,
        page_size=page_size,
        task_name=task_name,
        task_id=task_id,
        source_type=source_type,
        status=status,
        submitter=submitter,
    )


async def stream_task_events(task_id: str) -> AsyncGenerator[str, None]:
    task = await get_task(task_id)
    if not task:
        yield _sse_event({"error": "Task not found"})
        return

    while True:
        task = await get_task(task_id)
        if not task:
            break

        yield _sse_event(task)

        if task["status"] in (
            "completed",
            "analysis_failed",
            "generation_failed",
            "review_failed",
            "failed",
        ):
            break

        await asyncio.sleep(0.8)


def _sse_event(data: Any) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False)}\\n\\n"
