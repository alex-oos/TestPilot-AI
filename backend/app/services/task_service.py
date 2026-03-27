from typing import Any
from typing import Optional

from fastapi import HTTPException

from app.services import task_manager
async def create_task(
    *,
    task_name: Optional[str],
    source_type: Optional[str],
    doc_url: Optional[str] = None,
    file_name: Optional[str] = None,
    file_path: Optional[str] = None,
    status: str = "pending",
    status_text: Optional[str] = None,
    submitter: Optional[str] = None,
) -> str:
    return await task_manager.create_task(
        task_name=task_name,
        source_type=source_type,
        doc_url=doc_url,
        file_name=file_name,
        file_path=file_path,
        status=status,
        status_text=status_text,
        submitter=submitter,
    )


async def get_task(task_id: str) -> Optional[dict]:
    return await task_manager.get_task(task_id)


async def get_task_or_404(task_id: str) -> dict:
    task = await get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


async def update_phase(task_id: str, phase: str, status: str, data: Any = None, error: str = None):
    await task_manager.update_phase(task_id, phase, status, data=data, error=error)


async def set_task_status(task_id: str, status: str, error: str = None, status_text: str = None):
    await task_manager.set_task_status(task_id, status, error=error, status_text=status_text)


async def set_task_mindmap(task_id: str, mindmap: str):
    await task_manager.set_task_mindmap(task_id, mindmap)


async def set_task_decision(
    task_id: str,
    *,
    decision_status: str,
    decision_by: Optional[str] = None,
    decision_note: Optional[str] = None,
) -> bool:
    return await task_manager.set_task_decision(
        task_id,
        decision_status=decision_status,
        decision_by=decision_by,
        decision_note=decision_note,
    )


async def list_tasks(
    *,
    page: int,
    page_size: int,
    task_name: Optional[str],
    task_id: Optional[str],
    source_type: Optional[str],
    status: Optional[str],
    submitter: Optional[str],
) -> dict:
    return await task_manager.list_tasks(
        page=page,
        page_size=page_size,
        task_name=task_name,
        task_id=task_id,
        source_type=source_type,
        status=status,
        submitter=submitter,
    )


async def reset_task_for_retry(task_id: str, status_text: Optional[str] = None) -> Optional[dict]:
    return await task_manager.reset_task_for_retry(task_id, status_text=status_text)


async def get_task_status(task_id: str) -> dict:
    return await get_task_or_404(task_id)


async def delete_task(task_id: str) -> dict:
    deleted = await task_manager.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"task_id": task_id, "deleted": True}


async def batch_delete_tasks(task_ids: list[str]) -> dict:
    normalized_ids = [x for x in task_ids if str(x).strip()]
    if not normalized_ids:
        raise HTTPException(status_code=400, detail="task_ids 不能为空")
    deleted_count = await task_manager.delete_tasks(normalized_ids)
    return {"deleted_count": deleted_count, "requested_count": len(normalized_ids)}
