import os
from loguru import logger
from fastapi import UploadFile
import docx
from pypdf import PdfReader

async def parse_uploaded_file(file: UploadFile) -> str:
    """Read the file content and extract plain text."""
    filename = file.filename
    logger.info(f"Parsing uploaded file: {filename}")
    
    content_text = ""
    # Safe fallback if not matched
    ext = os.path.splitext(filename)[1].lower() if filename else ""

    try:
        if ext == ".md" or ext == ".txt":
            content_bytes = await file.read()
            content_text = content_bytes.decode('utf-8', errors='ignore')
        elif ext == ".docx":
            # read docx
            content_bytes = await file.read()
            # To read from bytes, we can use an in-memory BytesIO
            import io
            doc = docx.Document(io.BytesIO(content_bytes))
            content_text = "\n".join([para.text for para in doc.paragraphs])
        elif ext == ".pdf":
            content_bytes = await file.read()
            import io
            pdf = PdfReader(io.BytesIO(content_bytes))
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    content_text += text + "\n"
        else:
            # Fallback for unknown text types
            content_bytes = await file.read()
            content_text = content_bytes.decode('utf-8', errors='ignore')
            
        logger.success(f"Successfully extracted {len(content_text)} characters from {filename}")
        return content_text.strip()
    except Exception as e:
        logger.error(f"Error parsing file {filename}: {e}")
        raise
