from loguru import logger
from fastapi import UploadFile
from app.services.file_service import parse_text_from_uploaded_file

async def parse_uploaded_file(file: UploadFile) -> str:
    """Read the file content and extract plain text."""
    filename = file.filename
    logger.info(f"Parsing uploaded file: {filename}")
    
    try:
        content_bytes = await file.read()
        content_text = await parse_text_from_uploaded_file(
            file_name=filename or "upload.bin",
            file_content=content_bytes,
        )
            
        logger.success(f"Successfully extracted {len(content_text)} characters from {filename}")
        return content_text.strip()
    except Exception as e:
        logger.error(f"Error parsing file {filename}: {e}")
        raise
