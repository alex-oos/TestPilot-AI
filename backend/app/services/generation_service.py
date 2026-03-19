from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import BackgroundTasks, HTTPException, UploadFile

from app.services import task_manager
from app.services.exporter import convert_cases_to_mindmap
from app.services.file_storage import save_uploaded_bytes
from app.services.ms_sync import sync_cases_to_ms
from app.services.pipeline import run_generation_pipeline


def _default_task_name(source_type: str, file_name: Optional[str], doc_url: Optional[str]) -> str:
    submit_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if source_type == "local" and file_name:
        base_name = Path(file_name).stem
    elif source_type == "manual":
        base_name = "手动输入"
    elif doc_url:
        base_name = doc_url.rstrip("/").split("/")[-1] or "在线文档"
    else:
        base_name = "任务"
    return f"{base_name}_{submit_time}"


def _build_manual_text(
    manual_title: Optional[str],
    manual_description: Optional[str],
    related_project: Optional[str],
) -> tuple[str, bytes]:
    title = (manual_title or "").strip()
    description = (manual_description or "").strip()
    project = (related_project or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="手动输入模式必须填写需求标题")
    if not description:
        raise HTTPException(status_code=400, detail="手动输入模式必须填写需求描述")

    content = f"需求标题: {title}\n"
    if project:
        content += f"关联项目: {project}\n"
    content += f"\n需求描述:\n{description}\n"
    return title, content.encode("utf-8")


async def _create_uploaded_task(
    *,
    source_type: str,
    task_name: Optional[str],
    doc_url: Optional[str],
    submitter: Optional[str],
    file_name: str,
    file_content: bytes,
) -> dict:
    file_id, file_path = save_uploaded_bytes(file_name, file_content)
    final_task_name = (task_name or "").strip() or _default_task_name(source_type, file_name, doc_url)

    task_id = task_manager.create_task(
        task_name=final_task_name,
        source_type=source_type,
        doc_url=doc_url,
        file_name=file_name,
        file_path=file_path,
        status="uploaded",
        status_text="文件已上传，待分析",
        submitter=submitter,
    )
    task_manager.update_phase(
        task_id,
        "upload",
        "completed",
        {
            "file_id": file_id,
            "file_name": file_name,
            "file_path": file_path,
            "file_size": len(file_content),
        },
    )
    return {
        "task_id": task_id,
        "file_id": file_id,
        "file_name": file_name,
        "file_path": file_path,
    }


async def start_generation_task(
    *,
    task_id: str,
    background_tasks: BackgroundTasks,
    submitter: Optional[str] = None,
) -> dict:
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    if task.get("status") == "running":
        raise HTTPException(status_code=400, detail="任务执行中，请勿重复启动")

    source_type = task.get("source_type") or "local"
    doc_url = task.get("doc_url")
    file_name = task.get("file_name")
    file_path = task.get("file_path")

    async def _run() -> None:
        await run_generation_pipeline(
            task_id,
            source_type,
            doc_url,
            file_content=None,
            file_name=file_name,
            file_path=file_path,
            submitter=submitter,
        )

    task_manager.set_task_status(task_id, "queued", status_text="任务已入队，准备开始分析")
    background_tasks.add_task(_run)
    return {"task_id": task_id, "task_status": "任务已启动"}


async def upload_local_file_task(
    *,
    file: UploadFile,
    task_name: Optional[str],
    submitter: Optional[str],
) -> dict:
    if not file:
        raise HTTPException(status_code=400, detail="请上传本地文件")
    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="上传文件不能为空")
    file_name = file.filename or "upload.bin"
    result = await _create_uploaded_task(
        source_type="local",
        task_name=task_name,
        doc_url=None,
        submitter=submitter,
        file_name=file_name,
        file_content=file_content,
    )
    result["task_status"] = "文件已上传，待分析"
    return result


async def submit_generation_task(
    *,
    background_tasks: BackgroundTasks,
    source_type: str,
    task_name: Optional[str],
    doc_url: Optional[str],
    manual_title: Optional[str],
    manual_description: Optional[str],
    related_project: Optional[str],
    submitter: Optional[str],
    file: Optional[UploadFile],
) -> dict:
    source_type = (source_type or "").strip().lower()

    if source_type == "manual":
        title, manual_content = _build_manual_text(manual_title, manual_description, related_project)
        created = await _create_uploaded_task(
            source_type="manual",
            task_name=(task_name or "").strip() or title,
            doc_url=None,
            submitter=submitter,
            file_name="manual_input.txt",
            file_content=manual_content,
        )
        await start_generation_task(task_id=created["task_id"], background_tasks=background_tasks, submitter=submitter)
        return {"task_id": created["task_id"], "task_status": "需求描述分析中", "file_id": created["file_id"]}

    if source_type == "local":
        if not file:
            raise HTTPException(status_code=400, detail="本地文件模式必须上传文件")
        file_content = await file.read()
        if not file_content:
            raise HTTPException(status_code=400, detail="上传文件不能为空")
        created = await _create_uploaded_task(
            source_type="local",
            task_name=task_name,
            doc_url=None,
            submitter=submitter,
            file_name=file.filename or "upload.bin",
            file_content=file_content,
        )
        await start_generation_task(task_id=created["task_id"], background_tasks=background_tasks, submitter=submitter)
        return {"task_id": created["task_id"], "task_status": "本地文件分析中", "file_id": created["file_id"]}

    if source_type not in {"feishu", "dingtalk"}:
        raise HTTPException(status_code=400, detail="不支持的 source_type")
    if not (doc_url or "").strip():
        raise HTTPException(status_code=400, detail="在线文档模式必须提供文档链接")

    final_task_name = (task_name or "").strip() or _default_task_name(source_type, None, doc_url)
    task_id = task_manager.create_task(
        task_name=final_task_name,
        source_type=source_type,
        doc_url=doc_url,
        status="pending",
        status_text="待分析",
        submitter=submitter,
    )
    await start_generation_task(task_id=task_id, background_tasks=background_tasks, submitter=submitter)
    return {"task_id": task_id, "task_status": "需求描述分析中"}


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
    file_name = old_task.get("file_name")
    file_path = old_task.get("file_path")

    status_text = "需求描述分析中" if source_type == "manual" else "本地文件分析中"
    reset_task = task_manager.reset_task_for_retry(task_id, status_text=status_text)
    if not reset_task:
        raise HTTPException(status_code=404, detail="任务不存在，无法重试")

    async def _run() -> None:
        await run_generation_pipeline(
            task_id,
            source_type,
            doc_url,
            file_content=None,
            file_name=file_name,
            file_path=file_path,
        )

    background_tasks.add_task(_run)
    return {"task_id": task_id, "task_status": "重试任务已提交"}


def apply_task_decision(
    task_id: str,
    *,
    decision: str,
    decision_by: Optional[str] = None,
    decision_note: Optional[str] = None,
) -> dict:
    normalized = "accepted" if str(decision).strip().lower() in {"accepted", "accept", "采纳"} else "rejected"
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    ok = task_manager.set_task_decision(
        task_id,
        decision_status=normalized,
        decision_by=decision_by,
        decision_note=decision_note,
    )
    if not ok:
        raise HTTPException(status_code=404, detail="任务不存在")

    task_manager.update_phase(
        task_id,
        "notify",
        "completed",
        {
            "channel": "dingtalk",
            "decision_status": normalized,
            "decision_by": decision_by,
            "decision_note": decision_note,
        },
    )
    status_text = "用户已采纳测试用例" if normalized == "accepted" else "用户未采纳测试用例"
    task_manager.set_task_status(task_id, "completed", status_text=status_text)
    updated_task = task_manager.get_task(task_id)
    return {
        "task_id": task_id,
        "decision_status": normalized,
        "task_status": "completed",
        "task": updated_task,
    }


def delete_task(task_id: str) -> dict:
    deleted = task_manager.delete_task(task_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"task_id": task_id, "deleted": True}


def batch_delete_tasks(task_ids: list[str]) -> dict:
    normalized_ids = [x for x in task_ids if str(x).strip()]
    if not normalized_ids:
        raise HTTPException(status_code=400, detail="task_ids 不能为空")
    deleted_count = task_manager.delete_tasks(normalized_ids)
    return {"deleted_count": deleted_count, "requested_count": len(normalized_ids)}


def update_review_cases(task_id: str, reviewed_cases: list[dict]) -> dict:
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    if not isinstance(reviewed_cases, list) or not reviewed_cases:
        raise HTTPException(status_code=400, detail="评审用例不能为空")

    normalized_cases: list[dict] = []
    for idx, item in enumerate(reviewed_cases, start=1):
        if not isinstance(item, dict):
            continue
        raw_status = str(item.get("adoption_status") or "accepted").strip().lower()
        adoption_status = "rejected" if raw_status in {"rejected", "not_adopted", "不采纳"} else "accepted"
        case_id = item.get("id")
        normalized_cases.append(
            {
                "id": case_id if case_id not in (None, "") else idx,
                "module": str(item.get("module") or ""),
                "title": str(item.get("title") or ""),
                "precondition": str(item.get("precondition") or ""),
                "steps": str(item.get("steps") or ""),
                "expected_result": str(item.get("expected_result") or ""),
                "priority": str(item.get("priority") or "中"),
                "adoption_status": adoption_status,
            }
        )

    adopted_cases = [item for item in normalized_cases if item.get("adoption_status") == "accepted"]
    rejected_count = len(normalized_cases) - len(adopted_cases)

    task_manager.update_phase(task_id, "generation", "completed", {"cases": adopted_cases})
    task_manager.set_task_mindmap(task_id, convert_cases_to_mindmap(adopted_cases))

    review_phase = (task.get("phases") or {}).get("review") or {}
    review_data = review_phase.get("data") or {}
    if not isinstance(review_data, dict):
        review_data = {}
    review_detail = review_data.get("review") if isinstance(review_data.get("review"), dict) else {}
    review_detail["reviewed_cases"] = normalized_cases
    review_detail["adopted_count"] = len(adopted_cases)
    review_detail["rejected_count"] = rejected_count
    task_manager.update_phase(task_id, "review", "completed", {"review": review_detail})

    decision_status = "accepted" if rejected_count == 0 else "partially_accepted"
    task_manager.set_task_decision(
        task_id,
        decision_status=decision_status,
        decision_by="manual_review",
        decision_note=f"adopted={len(adopted_cases)}, rejected={rejected_count}",
    )
    task_manager.set_task_status(task_id, "completed", status_text="任务已完成")

    updated_task = task_manager.get_task(task_id)
    return {
        "task_id": task_id,
        "adopted_count": len(adopted_cases),
        "rejected_count": rejected_count,
        "task": updated_task,
    }


async def sync_to_ms(cases: list[dict]) -> dict:
    if not cases:
        raise HTTPException(status_code=400, detail="用例列表不能为空")
    return await sync_cases_to_ms(cases)
