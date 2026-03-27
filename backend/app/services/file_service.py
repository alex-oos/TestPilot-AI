import io
from datetime import datetime
from pathlib import Path
from typing import Optional

import docx
from fastapi import HTTPException, UploadFile
from pypdf import PdfReader

from app.services import task_manager
from app.services.file_storage import read_uploaded_bytes, save_uploaded_bytes

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
ALLOWED_UPLOAD_EXTENSIONS = {".md", ".markdown", ".txt", ".pdf", ".docx", ".json", ".yaml", ".yml"}
FILE_SIGNATURES = {
    b"%PDF": ".pdf",
    b"PK\x03\x04": ".docx",
}


def default_task_name(source_type: str, file_name: Optional[str], doc_url: Optional[str]) -> str:
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


def build_manual_text(
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


def validate_file_type(file_content: bytes, file_name: str) -> str:
    ext = Path(file_name or "").suffix.lower()
    if ext not in ALLOWED_UPLOAD_EXTENSIONS:
        raise HTTPException(status_code=400, detail="文件类型不匹配或不支持")

    if ext in {".pdf", ".docx"}:
        header = file_content[:8]
        expected = None
        for signature, detected_ext in FILE_SIGNATURES.items():
            if header.startswith(signature):
                expected = detected_ext
                break
        if expected != ext:
            raise HTTPException(status_code=400, detail="文件类型不匹配或不支持")
    return ext


def validate_upload(file_name: str, file_size: int, file_content: bytes) -> str:
    if file_size > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"文件过大，最大支持 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB")
    return validate_file_type(file_content, file_name)


def parse_text_from_uploaded_file(file_name: str, file_content: bytes) -> str:
    ext = Path(file_name or "").suffix.lower()
    if ext in {".md", ".markdown", ".txt", ".json", ".yaml", ".yml"}:
        return file_content.decode("utf-8", errors="ignore").strip()
    if ext == ".docx":
        doc = docx.Document(io.BytesIO(file_content))
        return "\n".join([p.text for p in doc.paragraphs]).strip()
    if ext == ".pdf":
        pdf = PdfReader(io.BytesIO(file_content))
        text = ""
        for page in pdf.pages:
            parsed = page.extract_text()
            if parsed:
                text += parsed + "\n"
        return text.strip()
    return file_content.decode("utf-8", errors="ignore").strip()


def build_merged_input_from_file(
    *,
    file_path: str,
    file_name: str,
    context: Optional[str] = None,
    requirements: Optional[str] = None,
) -> str:
    file_content = read_uploaded_bytes(file_path)
    parsed_text = parse_text_from_uploaded_file(file_name=file_name, file_content=file_content)
    if not parsed_text:
        raise HTTPException(status_code=400, detail="无法从文件中提取有效文本")

    merged_input = parsed_text
    if context and context.strip():
        merged_input += f"\n\n补充上下文:\n{context.strip()}"
    if requirements and requirements.strip():
        merged_input += f"\n\n额外要求:\n{requirements.strip()}"
    return merged_input


async def create_uploaded_task(
    *,
    source_type: str,
    task_name: Optional[str],
    doc_url: Optional[str],
    submitter: Optional[str],
    file_name: str,
    file_content: bytes,
) -> dict:
    if source_type == "local":
        validate_upload(file_name=file_name, file_size=len(file_content), file_content=file_content)
    file_id, file_path = save_uploaded_bytes(file_name, file_content)
    final_task_name = (task_name or "").strip() or default_task_name(source_type, file_name, doc_url)

    task_id = await task_manager.create_task(
        task_name=final_task_name,
        source_type=source_type,
        doc_url=doc_url,
        file_name=file_name,
        file_path=file_path,
        status="uploaded",
        status_text="文件已上传，待分析",
        submitter=submitter,
    )
    await task_manager.update_phase(
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
    return {"task_id": task_id, "file_id": file_id, "file_name": file_name, "file_path": file_path}


async def prepare_stream_generation_file(*, file: UploadFile) -> dict:
    if not file:
        raise HTTPException(status_code=400, detail="请上传文件")
    file_content = await file.read()
    if not file_content:
        raise HTTPException(status_code=400, detail="上传文件不能为空")
    file_name = file.filename or "upload.bin"
    validate_upload(file_name=file_name, file_size=len(file_content), file_content=file_content)
    file_id, file_path = save_uploaded_bytes(file_name, file_content)
    return {"file_id": file_id, "file_path": file_path, "file_name": file_name}


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
    result = await create_uploaded_task(
        source_type="local",
        task_name=task_name,
        doc_url=None,
        submitter=submitter,
        file_name=file_name,
        file_content=file_content,
    )
    result["task_status"] = "文件已上传，待分析"
    return result
