import io
from fastapi import APIRouter, Form, File, UploadFile, HTTPException, BackgroundTasks, Request
from fastapi.responses import StreamingResponse
from typing import Optional
from loguru import logger
from app.core.response import success
from app.services import generation_service
from app.services import task_manager
from app.services.exporter import export_cases_to_excel
from app.services.xmind_exporter import generate_xmind_file
from app.schemas.use_case import SyncRequest, ExportRequest, DeleteTasksRequest, UpdateReviewCasesRequest

router = APIRouter()


@router.post("/tasks/uploads/local")
async def upload_local_file(
    request: Request,
    file: UploadFile = File(...),
    task_name: Optional[str] = Form(None),
    submitter: Optional[str] = Form(None),
):
    """仅上传本地文件到后台，不立即执行分析。"""
    data = await generation_service.upload_local_file_task(
        file=file,
        task_name=task_name,
        submitter=submitter,
    )
    return success(data, request.state.tid)


@router.post("/tasks/{task_id}/start")
async def start_uploaded_task(
    request: Request,
    task_id: str,
    background_tasks: BackgroundTasks,
    submitter: Optional[str] = Form(None),
):
    """启动已上传任务，进入 AI 需求分析流水线。"""
    data = await generation_service.start_generation_task(
        task_id=task_id,
        background_tasks=background_tasks,
        submitter=submitter,
    )
    return success(data, request.state.tid)


@router.post("/tasks")
async def submit_generation_task_stream(
    request: Request,
    background_tasks: BackgroundTasks,
    source_type: str = Form("local"),
    file: Optional[UploadFile] = File(None),
    context: Optional[str] = Form(None),
    requirements: Optional[str] = Form(None),
    task_name: Optional[str] = Form(None),
    doc_url: Optional[str] = Form(None),
    manual_title: Optional[str] = Form(None),
    manual_description: Optional[str] = Form(None),
    related_project: Optional[str] = Form(None),
    submitter: Optional[str] = Form(None),
):
    """
    提交任务并进入后台队列执行：
    1) 文件大小校验
    2) 文件类型校验
    3) 保存到 uploads
    4) 创建 task + 入队执行（需求分析 -> 用例生成 -> 用例评审）
    """
    normalized_source = (source_type or "local").strip().lower()
    logger.info(
        "Submit task: source_type={}, file_name={}",
        normalized_source,
        file.filename if file else None,
    )
    if normalized_source == "local":
        if not file:
            raise HTTPException(status_code=400, detail="本地文件模式必须上传文件")
        data = await generation_service.submit_stream_generation_task(
            background_tasks=background_tasks,
            file=file,
            context=context,
            requirements=requirements,
            task_name=task_name,
            submitter=submitter,
        )
    else:
        data = await generation_service.submit_generation_task(
            background_tasks=background_tasks,
            source_type=normalized_source,
            task_name=task_name,
            doc_url=doc_url,
            manual_title=manual_title,
            manual_description=manual_description,
            related_project=related_project,
            submitter=submitter,
            file=file,
        )
    return success(data, request.state.tid)


@router.post("/test-cases/generate")
async def generate_test_cases_stream_direct(
    file: UploadFile = File(...),
    context: Optional[str] = Form(None),
    requirements: Optional[str] = Form(None),
):
    """
    新版流式接口：
    1) 文件大小校验
    2) 文件类型校验
    3) 保存到 uploads
    4) 流式返回：需求分析 -> 用例生成 -> 用例评审 -> 最终用例
    """
    logger.info("Submit direct stream generation request: file_name={}", file.filename if file else None)
    prepared = await generation_service.prepare_stream_generation_file(file=file)
    return StreamingResponse(
        generation_service.generate_test_cases_stream(
            file_path=prepared["file_path"],
            file_name=prepared["file_name"],
            context=context,
            requirements=requirements,
        ),
        media_type="text/markdown; charset=utf-8",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.post("/tasks/{task_id}/decision")
@router.get("/tasks/{task_id}/decision")
async def apply_decision(
    request: Request,
    task_id: str,
    decision: str,
    by: Optional[str] = None,
    note: Optional[str] = None,
):
    """
    采纳决策入口（支持钉钉回调链接直接访问）。
    decision: accepted | rejected
    """
    data = await generation_service.apply_task_decision(
        task_id,
        decision=decision,
        decision_by=by,
        decision_note=note,
    )
    return success(data, request.state.tid)


@router.get("/tasks/{task_id}/events")
async def stream_task_progress(task_id: str):
    """SSE 端点：实时推送任务进度更新。"""
    task = await task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    
    return StreamingResponse(
        task_manager.stream_task_events(task_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        }
    )


@router.get("/tasks/{task_id}")
async def get_task_status(request: Request, task_id: str):
    """获取任务当前状态（轮询备用方案）。"""
    return success(await generation_service.get_task_status(task_id), request.state.tid)


@router.post("/tasks/{task_id}/retries")
async def retry_task(request: Request, task_id: str, background_tasks: BackgroundTasks):
    """
    重试任务：复用同一个任务 ID 重置后重新执行。
    本地文件任务会复用历史保存的 source_text。
    """
    data = await generation_service.retry_task(task_id=task_id, background_tasks=background_tasks)
    return success(data, request.state.tid)


@router.put("/tasks/{task_id}/review-cases")
async def update_review_cases(request: Request, task_id: str, payload: UpdateReviewCasesRequest):
    """评审后修改测试用例，并删除不采纳的用例。"""
    data = await generation_service.update_review_cases(task_id, [item.model_dump() for item in payload.cases])
    return success(data, request.state.tid)


@router.get("/tasks")
async def list_tasks(
    request: Request,
    page: int = 1,
    page_size: int = 10,
    task_name: Optional[str] = None,
    task_id: Optional[str] = None,
    source_type: Optional[str] = None,
    status: Optional[str] = None,
    submitter: Optional[str] = None,
):
    """获取任务列表（按更新时间倒序）。"""
    data = await generation_service.list_tasks(
        page=page,
        page_size=page_size,
        task_name=task_name,
        task_id=task_id,
        source_type=source_type,
        status=status,
        submitter=submitter,
    )
    return success(data, request.state.tid)


@router.delete("/tasks/{task_id}")
async def delete_task(request: Request, task_id: str):
    """删除单个任务。"""
    data = await generation_service.delete_task(task_id)
    return success(data, request.state.tid)


@router.delete("/tasks")
async def batch_delete_tasks(request: Request, payload: DeleteTasksRequest):
    """批量删除任务。"""
    data = await generation_service.batch_delete_tasks(payload.task_ids)
    return success(data, request.state.tid)


@router.post("/tasks/exports/excel")
async def export_excel(request: ExportRequest):
    """导出测试用例为 Excel 文件"""
    if not request.cases:
        raise HTTPException(status_code=400, detail="用例列表不能为空")
    excel_bytes = export_cases_to_excel(request.cases)
    return StreamingResponse(
        io.BytesIO(excel_bytes),
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        headers={"Content-Disposition": "attachment; filename=test_cases.xlsx"}
    )


@router.post("/tasks/exports/xmind")
async def export_xmind(request: ExportRequest):
    """导出测试用例为 XMind 文件"""
    if not request.cases:
        raise HTTPException(status_code=400, detail="用例列表不能为空")
    xmind_bytes = generate_xmind_file(request.cases, request.title or "AI自动生成测试用例")
    return StreamingResponse(
        io.BytesIO(xmind_bytes),
        media_type="application/octet-stream",
        headers={"Content-Disposition": "attachment; filename=test_cases.xmind"}
    )


@router.post("/tasks/sync/ms")
async def sync_to_ms(request: Request, payload: SyncRequest):
    """同步测试用例到 MS 测试管理平台"""
    result = await generation_service.sync_to_ms(payload.cases)
    return success(result, request.state.tid)
