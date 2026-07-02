from __future__ import annotations

import os
import uuid
from pathlib import Path


def get_upload_root() -> Path:
    root = Path(__file__).resolve().parents[2] / "data" / "uploads"
    root.mkdir(parents=True, exist_ok=True)
    return root


def sanitize_file_name(file_name: str) -> str:
    base = os.path.basename((file_name or "").strip())
    if not base:
        return "upload.bin"
    return "".join(ch for ch in base if ch.isalnum() or ch in (".", "-", "_")) or "upload.bin"


def save_uploaded_bytes(file_name: str, content: bytes) -> tuple[str, str]:
    safe_name = sanitize_file_name(file_name)
    file_id = uuid.uuid4().hex
    target = get_upload_root() / f"{file_id}_{safe_name}"
    target.write_bytes(content)
    return file_id, str(target)


def read_uploaded_bytes(file_path: str) -> bytes:
    path = Path(file_path)
    if not path.exists() or not path.is_file():
        raise FileNotFoundError(f"上传文件不存在: {file_path}")
    return path.read_bytes()
