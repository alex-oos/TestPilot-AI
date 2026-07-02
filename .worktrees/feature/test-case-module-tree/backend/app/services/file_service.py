import io
import asyncio
from pathlib import Path
from typing import Optional

import docx
from fastapi import HTTPException, UploadFile
from pypdf import PdfReader

from app.rag.knowledge_base import ingest_requirement_document
from app.services.image_ocr import extract_text_from_image_bytes
from app.services import task_manager
from app.services.file_storage import read_uploaded_bytes, save_uploaded_bytes

MAX_UPLOAD_BYTES = 10 * 1024 * 1024
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}
ALLOWED_UPLOAD_EXTENSIONS = {".md", ".markdown", ".txt", ".pdf", ".docx", ".json", ".yaml", ".yml", *IMAGE_EXTENSIONS}
FILE_SIGNATURES = {
    b"%PDF": ".pdf",
    b"PK\x03\x04": ".docx",
    b"\x89PNG\r\n\x1a\n": ".png",
    b"\xff\xd8\xff": ".jpg",
    b"GIF87a": ".gif",
    b"GIF89a": ".gif",
    b"BM": ".bmp",
}


ONLINE_TASK_NAME_PLACEHOLDER = "文档解析中"


def default_task_name(source_type: str, file_name: Optional[str], doc_url: Optional[str]) -> str:
    if source_type == "local" and file_name:
        return file_name
    if source_type == "manual":
        return "手动需求"
    if source_type in {"feishu", "dingtalk"}:
        return ONLINE_TASK_NAME_PLACEHOLDER
    if doc_url:
        return doc_url.rstrip("/").split("/")[-1] or "任务"
    return "任务"


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

    if ext in {".pdf", ".docx"} | IMAGE_EXTENSIONS:
        header = file_content[:8]
        expected = None
        if ext == ".webp":
            if len(file_content) >= 12 and file_content[:4] == b"RIFF" and file_content[8:12] == b"WEBP":
                expected = ".webp"
        for signature, detected_ext in FILE_SIGNATURES.items():
            if header.startswith(signature):
                expected = detected_ext
                break
        if ext == ".jpeg" and expected == ".jpg":
            expected = ".jpeg"
        if expected != ext:
            raise HTTPException(status_code=400, detail="文件类型不匹配或不支持")
    return ext


def validate_upload(file_name: str, file_size: int, file_content: bytes) -> str:
    if file_size > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"文件过大，最大支持 {MAX_UPLOAD_BYTES // (1024 * 1024)}MB")
    return validate_file_type(file_content, file_name)


async def parse_text_from_uploaded_file(file_name: str, file_content: bytes) -> str:
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
    if ext in IMAGE_EXTENSIONS:
        ocr_text = await extract_text_from_image_bytes(image_bytes=file_content, file_name=file_name)
        if ocr_text.lower().startswith("error:"):
            raise HTTPException(status_code=400, detail=f"图片识别失败：{ocr_text}")
        return ocr_text.strip()
    return file_content.decode("utf-8", errors="ignore").strip()


async def build_merged_input_from_file(
    *,
    file_path: str,
    file_name: str,
    context: Optional[str] = None,
    requirements: Optional[str] = None,
) -> str:
    file_content = read_uploaded_bytes(file_path)
    parsed_text = await parse_text_from_uploaded_file(file_name=file_name, file_content=file_content)
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
    parsed_text = await parse_text_from_uploaded_file(file_name=file_name, file_content=file_content)
    if not parsed_text.strip():
        raise HTTPException(status_code=400, detail="无法从文件中提取有效文本，无法写入需求知识库")

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
    kb_ingest = await asyncio.to_thread(
        ingest_requirement_document,
        task_id=task_id,
        text=parsed_text,
        source_type=source_type,
        file_name=file_name,
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
            "knowledge_base": {
                "ingested_chunks": kb_ingest.get("chunk_count", 0),
            },
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
