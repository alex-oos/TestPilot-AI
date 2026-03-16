from fastapi import APIRouter, Form, File, UploadFile
from typing import Optional
from app.services.generation import process_generation_request

router = APIRouter()

@router.post("/use_cases/generate")
async def generate_use_cases(
    source_type: str = Form(...),
    doc_url: Optional[str] = Form(None),
    file: Optional[UploadFile] = File(None)
):
    data = await process_generation_request(source_type, doc_url, file)
    return {"status": "success", "data": data}
