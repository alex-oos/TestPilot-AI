import pytest

from app.services import file_service


def test_validate_upload_accepts_png_signature():
    png_bytes = b"\x89PNG\r\n\x1a\n" + b"mock-image-content"
    ext = file_service.validate_upload("demo.png", len(png_bytes), png_bytes)
    assert ext == ".png"


@pytest.mark.asyncio
async def test_create_uploaded_task_uses_image_ocr(monkeypatch):
    calls = {"ocr_called": False, "ingest_text": ""}

    async def fake_extract_text_from_image_bytes(*, image_bytes: bytes, file_name: str) -> str:
        calls["ocr_called"] = True
        assert file_name == "req.png"
        assert image_bytes.startswith(b"\x89PNG")
        return "这是图片中识别出的需求文本：登录失败 5 次锁定"

    async def fake_create_task(**kwargs):
        return "task-img-001"

    async def fake_update_phase(task_id, phase, status, data):
        return None

    def fake_ingest_requirement_document(**kwargs):
        calls["ingest_text"] = kwargs["text"]
        return {"task_id": kwargs["task_id"], "chunk_count": 1}

    monkeypatch.setattr(file_service, "extract_text_from_image_bytes", fake_extract_text_from_image_bytes)
    monkeypatch.setattr(file_service.task_manager, "create_task", fake_create_task)
    monkeypatch.setattr(file_service.task_manager, "update_phase", fake_update_phase)
    monkeypatch.setattr(file_service, "ingest_requirement_document", fake_ingest_requirement_document)

    png_bytes = b"\x89PNG\r\n\x1a\n" + b"mock-image-content"
    result = await file_service.create_uploaded_task(
        source_type="local",
        task_name="图片需求上传",
        doc_url=None,
        submitter="tester",
        file_name="req.png",
        file_content=png_bytes,
    )

    assert result["task_id"] == "task-img-001"
    assert calls["ocr_called"] is True
    assert "登录失败 5 次锁定" in calls["ingest_text"]
