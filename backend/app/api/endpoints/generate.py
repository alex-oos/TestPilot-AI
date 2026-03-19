import io
from fastapi import APIRouter, Form, File, UploadFile, HTTPException, BackgroundTasks
from fastapi.responses import StreamingResponse
from typing import Optional
from app.services import task_manager
from app.services.pipeline import run_generation_pipeline
from app.services.exporter import export_cases_to_excel
from app.services.xmind_exporter import generate_xmind_file
from app.services.ms_sync import sync_cases_to_ms
from app.schemas.use_case import SyncRequest, ExportRequest

router = APIRouter()


@router.post("/use_cases/submit")
async def submit_generation_task(
    background_tasks: BackgroundTasks,
    source_type: str = Form(...),
    doc_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    """
    提交生成任务，立即返回 task_id。
    前端拿到 task_id 后跳转到任务详情页，通过 SSE 接收实时进度。
    """
    # 预读文件内容（在请求上下文中，背景任务无法访问 UploadFile）
    file_content: Optional[bytes] = None
    file_name: Optional[str] = None
    
    if file:
        file_content = await file.read()
        file_name = file.filename
    elif source_type == "local":
        raise HTTPException(status_code=400, detail="本地文件模式必须上传文件")
    
    # 创建任务
    task_id = task_manager.create_task(source_type=source_type, doc_url=doc_url)
    
    # 启动后台执行（在当前事件循环中异步调度）
    async def _run():
        await run_generation_pipeline(task_id, source_type, doc_url, file_content, file_name)
    
    background_tasks.add_task(_run)
    
    return {"status": "success", "task_id": task_id, "task_status": "本地文件分析中"}


@router.get("/use_cases/task/{task_id}/stream")
async def stream_task_progress(task_id: str):
    """SSE 端点：实时推送任务进度更新。"""
    task = task_manager.get_task(task_id)
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


@router.get("/use_cases/task/{task_id}")
async def get_task_status(task_id: str):
    """获取任务当前状态（轮询备用方案）。"""
    task = task_manager.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return {"status": "success", "data": task}


@router.get("/use_cases/tasks")
async def list_tasks(limit: int = 50):
    """获取任务列表（按更新时间倒序）。"""
    return {"status": "success", "data": task_manager.list_tasks(limit=limit)}


@router.post("/use_cases/export/excel")
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


@router.post("/use_cases/export/xmind")
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


@router.post("/use_cases/sync/ms")
async def sync_to_ms(request: SyncRequest):
    """同步测试用例到 MS 测试管理平台"""
    if not request.cases:
        raise HTTPException(status_code=400, detail="用例列表不能为空")
    result = await sync_cases_to_ms(request.cases)
    return {"status": "success", "data": result}
