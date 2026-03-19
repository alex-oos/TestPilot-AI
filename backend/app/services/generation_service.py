from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, HTTPException, UploadFile

from app.services import task_manager
from app.services.ms_sync import sync_cases_to_ms
from app.services.pipeline import run_generation_pipeline


def _default_task_name(source_type: str, file_name: Optional[str], doc_url: Optional[str]) -> str:
    submit_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if source_type == "local" and file_name:
        base_name = Path(file_name).stem
    elif doc_url:
        base_name = doc_url.rstrip("/").split("/")[-1] or "在线文档"
    else:
        base_name = "任务"
    return f"{base_name}_{submit_time}"


async def submit_generation_task(
    *,
    background_tasks: BackgroundTasks,
    source_type: str,
    task_name: Optional[str],
    doc_url: Optional[str],
    submitter: Optional[str],
    file: Optional[UploadFile],
) -> dict:
    file_content: Optional[bytes] = None
    file_name: Optional[str] = None

    if file:
        file_content = await file.read()
        file_name = file.filename
    elif source_type == "local":
        raise HTTPException(status_code=400, detail="本地文件模式必须上传文件")

    final_task_name = (task_name or "").strip() or _default_task_name(source_type, file_name, doc_url)
    task_id = task_manager.create_task(
        task_name=final_task_name,
        source_type=source_type,
        doc_url=doc_url,
        submitter=submitter,
    )

    async def _run() -> None:
        await run_generation_pipeline(task_id, source_type, doc_url, file_content, file_name)

    background_tasks.add_task(_run)
    return {"task_id": task_id, "task_status": "本地文件分析中"}


def get_task_status(task_id: str) -> dict:
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return task


def list_tasks(
    *,
    page: int,
    page_size: int,
    task_name: Optional[str],
    task_id: Optional[str],
    source_type: Optional[str],
    status: Optional[str],
    submitter: Optional[str],
) -> dict:
    return task_manager.list_tasks(
        page=page,
        page_size=page_size,
        task_name=task_name,
        task_id=task_id,
        source_type=source_type,
        status=status,
        submitter=submitter,
    )


async def retry_task(*, task_id: str, background_tasks: BackgroundTasks) -> dict:
    old_task = task_manager.get_task(task_id)
    if not old_task:
        raise HTTPException(status_code=404, detail="原任务不存在")
    if old_task.get("status") == "running":
        raise HTTPException(status_code=400, detail="任务执行中，暂不支持重试")

    source_type = old_task.get("source_type") or "local"
    doc_url = old_task.get("doc_url")
    user_id = old_task.get("user_id")
    file_content: Optional[bytes] = None
    file_name: Optional[str] = None

    if source_type == "local":
        source_text = (
            (old_task.get("phases") or {})
            .get("analysis", {})
            .get("data", {})
            .get("source_text")
        )
        if not source_text:
            raise HTTPException(status_code=400, detail="该任务缺少可重试源文本，请重新上传文档发起新任务")
        file_content = str(source_text).encode("utf-8")
        file_name = "retry_source.txt"

    old_task_name = old_task.get("task_name") or "重试任务"
    retry_task_name = f"{old_task_name}_重试_{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    new_task_id = task_manager.create_task(
        task_name=retry_task_name,
        source_type=source_type,
        doc_url=doc_url,
        user_id=user_id,
    )

    async def _run() -> None:
        await run_generation_pipeline(new_task_id, source_type, doc_url, file_content, file_name)

    background_tasks.add_task(_run)
    return {"task_id": new_task_id, "task_status": "重试任务已提交"}


async def sync_to_ms(cases: list[dict]) -> dict:
    if not cases:
        raise HTTPException(status_code=400, detail="用例列表不能为空")
    return await sync_cases_to_ms(cases)
