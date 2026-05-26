"""将本地 Skill 目录打包为 ZIP。

作者：Zhao Wang
"""

from __future__ import annotations

import io
import zipfile
from pathlib import Path

from app.ai.skills.loader import SkillLoader, get_skill_loader
from app.ai.skills.loader import SkillNotFoundError


class ZipSkillExportError(Exception):
    """Skill ZIP 导出失败。"""


class ZipSkillExporter:
    """Skill 目录 ZIP 导出器。"""

    def __init__(self, loader: SkillLoader | None = None) -> None:
        self._loader = loader or get_skill_loader()

    def export_bytes(self, skill_id: str) -> tuple[bytes, str]:
        """打包 Skill 为 ZIP 字节流。

        Args:
            skill_id: Skill 目录名

        Returns:
            (zip_bytes, archive_filename)
        """
        sid = (skill_id or "").strip()
        skill_dir = self._loader.library_dir / sid
        if not skill_dir.is_dir():
            raise SkillNotFoundError(f"Skill 不存在: {sid}")

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
            for path in sorted(skill_dir.rglob("*")):
                if not path.is_file():
                    continue
                rel = path.relative_to(skill_dir).as_posix()
                if rel.startswith("__pycache__/") or path.name == ".DS_Store":
                    continue
                zf.write(path, arcname=f"{sid}/{rel}")
        return buf.getvalue(), f"{sid}.zip"
