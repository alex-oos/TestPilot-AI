"""
Task Manager - task state backed by SQLite + in-memory cache for SSE polling.
Each generation task runs 3 phases:
  Phase 1: 需求分析 (Requirement Analysis)
  Phase 2: 用例编写 (Test Case Generation)
  Phase 3: 用例评审 (AI Review)
"""
import uuid
import asyncio
import json
from typing import Dict, Any, Optional, AsyncGenerator
from loguru import logger

from app.core import database


# in-memory cache to reduce repeated DB reads during active SSE sessions
_tasks: Dict[str, Dict[str, Any]] = {}


def create_task(source_type: Optional[str] = None, doc_url: Optional[str] = None, user_id: Optional[int] = None) -> str:
    """Create a new task, persist it in DB, and return task_id."""
    task_id = str(uuid.uuid4())
    initial_status_text = "本地文件分析中" if source_type == "local" else "需求文档解析中"
    database.create_task_record(
        task_id,
        source_type=source_type,
        doc_url=doc_url,
        status="running",
        status_text=initial_status_text,
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


def list_tasks(limit: int = 50):
    return database.list_tasks(limit=limit)


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

        if task["status"] in ("completed", "failed"):
            break

        await asyncio.sleep(0.8)


def _sse_event(data: Any) -> str:
    """Format as SSE event string."""
    return f"data: {json.dumps(data, ensure_ascii=False)}\\n\\n"
