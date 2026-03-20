from typing import Any, Dict, List, Optional

from app.modules.domain import task_domain, user_domain


async def ensure_user(username: str, password: str = "123456") -> Dict[str, Any]:
    return await user_domain.ensure_user(username, password=password)


async def create_task_record(task_id: str, **kwargs) -> None:
    await task_domain.create_task_record(task_id=task_id, **kwargs)


async def get_task_record(task_id: str) -> Optional[Dict[str, Any]]:
    return await task_domain.get_task_record(task_id)


async def update_task_phase(task_id: str, phase: str, status: str, data: Any = None, error: Optional[str] = None) -> None:
    await task_domain.update_task_phase(task_id, phase_key=phase, status=status, data=data, error=error)


async def update_task_status(task_id: str, status: str, error: Optional[str] = None, status_text: Optional[str] = None) -> None:
    await task_domain.update_task_status(task_id, status, error=error, status_text=status_text)


async def update_task_mindmap(task_id: str, mindmap: str) -> None:
    await task_domain.update_task_mindmap(task_id, mindmap)


async def update_task_decision(
    task_id: str,
    *,
    decision_status: str,
    decision_by: Optional[str] = None,
    decision_note: Optional[str] = None,
) -> bool:
    return await task_domain.update_task_decision(
        task_id,
        decision_status=decision_status,
        decision_by=decision_by,
        decision_note=decision_note,
    )


async def reset_task_for_retry(task_id: str, status_text: Optional[str] = None) -> bool:
    return await task_domain.reset_task_for_retry(task_id, status_text=status_text)


async def delete_task_record(task_id: str) -> bool:
    return await task_domain.delete_task_record(task_id)


async def delete_task_records(task_ids: List[str]) -> int:
    return await task_domain.delete_task_records(task_ids)


async def list_tasks(
    *,
    page: int,
    page_size: int,
    task_name: Optional[str],
    task_id: Optional[str],
    source_type: Optional[str],
    status: Optional[str],
    submitter: Optional[str],
):
    return await task_domain.list_tasks(
        page=page,
        page_size=page_size,
        task_name=task_name,
        task_id=task_id,
        source_type=source_type,
        status=status,
        submitter=submitter,
    )
