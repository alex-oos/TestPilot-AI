import os
import io
from loguru import logger
from fastapi import UploadFile
import docx
from pypdf import PdfReader

async def parse_local_file(file: UploadFile) -> str:
    """本地解析模块 - 解析多种本地格式文档"""
    filename = file.filename
    logger.info(f"Local Parser Module: Parsing uploaded file {filename}")
    
    content_text = ""
    ext = os.path.splitext(filename)[1].lower() if filename else ""

    try:
        if ext in [".md", ".txt"]:
            content_bytes = await file.read()
            content_text = content_bytes.decode('utf-8', errors='ignore')
        elif ext == ".docx":
            content_bytes = await file.read()
            doc = docx.Document(io.BytesIO(content_bytes))
            content_text = "\n".join([para.text for para in doc.paragraphs])
        elif ext == ".pdf":
            content_bytes = await file.read()
            pdf = PdfReader(io.BytesIO(content_bytes))
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    content_text += text + "\n"
        else:
            # Fallback
            content_bytes = await file.read()
            content_text = content_bytes.decode('utf-8', errors='ignore')
            
        logger.success(f"Successfully extracted {len(content_text)} characters from {filename}")
        return content_text.strip()
    except Exception as e:
        logger.error(f"Error parsing file {filename}: {e}")
        raise
