"""从 ZIP 包手动导入 QA Skill 到本地 library/。

自动解析常见 ZIP 结构：
- 根目录直接包含 SKILL.md
- 单层目录包裹（如 my-skill/SKILL.md）
- 深层路径（如 skills/zh/testing-types/my-skill/SKILL.md，取最浅 SKILL.md）

作者：Zhao Wang
"""

from __future__ import annotations

import io
import re
import zipfile
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath

from loguru import logger

from app.ai.skills.github_importer import (
    MAX_FILE_BYTES,
    MAX_FILES,
    MAX_TOTAL_BYTES,
    validate_skill_md_text,
)
from app.ai.skills.loader import SkillLoader, get_skill_loader

SKILL_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$", re.I)
SKIP_ZIP_PREFIXES = ("__MACOSX/",)
SKIP_ZIP_NAMES = {".DS_Store", "Thumbs.db", "desktop.ini"}


class ZipSkillImportError(Exception):
    """ZIP Skill 导入失败。"""


@dataclass
class ZipSkillAnalysis:
    """ZIP 包解析结果。"""

    skill_id: str
    skill_root: str
    detected_from: str
    archive_name: str
    file_count: int = 0
    total_bytes: int = 0
    sample_files: list[str] = field(default_factory=list)
    skill_md_preview: dict[str, str] = field(default_factory=dict)
    ambiguous_candidates: list[str] = field(default_factory=list)


@dataclass
class ZipImportPreview:
    """ZIP 导入预览。"""

    analysis: ZipSkillAnalysis
    exists_locally: bool
    local_path: str


@dataclass
class ZipImportResult:
    """ZIP 导入执行结果。"""

    skill_id: str
    dest_path: str
    files_written: int
    bytes_written: int
    overwritten: bool
    validation_message: str = ""
    detected_from: str = ""


def _normalize_skill_id(raw: str) -> str:
    """校验并规范化 skill_id。"""
    sid = (raw or "").strip().strip("/")
    if not sid or not SKILL_ID_PATTERN.match(sid):
        raise ZipSkillImportError(
            f"skill_id 非法：{raw!r}。仅允许字母、数字、点、下划线、连字符，且长度 ≤ 64。"
        )
    return sid


def _slugify_from_name(name: str) -> str:
    """从 frontmatter name 生成备用 skill_id。"""
    slug = re.sub(r"[^a-z0-9._-]+", "-", (name or "").lower()).strip("-")
    slug = re.sub(r"-{2,}", "-", slug)
    if slug and SKILL_ID_PATTERN.match(slug):
        return slug
    raise ZipSkillImportError("无法从 ZIP 推断 skill_id，请在表单中指定本地 ID。")


def _should_skip_zip_entry(name: str) -> bool:
    """判断是否跳过 ZIP 条目。"""
    norm = name.replace("\\", "/").lstrip("/")
    if not norm or norm.endswith("/"):
        return True
    base = PurePosixPath(norm).name
    if base in SKIP_ZIP_NAMES or base.startswith("._"):
        return True
    return any(norm.startswith(prefix) for prefix in SKIP_ZIP_PREFIXES)


def _assert_safe_relative_path(rel_name: str) -> None:
    """防止 Zip Slip。"""
    pure = PurePosixPath(rel_name)
    if pure.is_absolute() or ".." in pure.parts:
        raise ZipSkillImportError(f"非法文件路径：{rel_name}")


def _parse_frontmatter_field(text: str, field_name: str) -> str:
    """从 SKILL.md frontmatter 读取简单字段。"""
    if not text.startswith("---"):
        return ""
    end = text.find("\n---", 3)
    if end < 0:
        return ""
    fm = text[3:end]
    for line in fm.splitlines():
        if line.strip().startswith(f"{field_name}:"):
            return line.split(":", 1)[1].strip().strip('"').strip("'")
    return ""


def _collect_zip_files(data: bytes) -> list[tuple[str, bytes]]:
    """读取 ZIP 内有效文件列表。"""
    if not data:
        raise ZipSkillImportError("ZIP 文件为空。")
    if len(data) > MAX_TOTAL_BYTES:
        raise ZipSkillImportError(f"ZIP 包体积超过上限 {MAX_TOTAL_BYTES} bytes。")

    collected: list[tuple[str, bytes]] = []
    try:
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            for info in zf.infolist():
                name = info.filename.replace("\\", "/").lstrip("/")
                if _should_skip_zip_entry(name):
                    continue
                if info.is_dir() or name.endswith("/"):
                    continue
                _assert_safe_relative_path(name)
                if len(collected) >= MAX_FILES:
                    raise ZipSkillImportError(f"ZIP 内文件数超过上限 {MAX_FILES}。")
                content = zf.read(info)
                if len(content) > MAX_FILE_BYTES:
                    raise ZipSkillImportError(
                        f"单文件过大：{name} ({len(content)} bytes)"
                    )
                collected.append((name, content))
    except zipfile.BadZipFile as exc:
        raise ZipSkillImportError("无效的 ZIP 文件，请确认上传的是 .zip 压缩包。") from exc

    if not collected:
        raise ZipSkillImportError("ZIP 包内没有可导入的文件。")
    return collected


def analyze_zip_skill(
    data: bytes,
    *,
    archive_name: str = "",
    skill_id_override: str | None = None,
) -> ZipSkillAnalysis:
    """解析 ZIP 包并自动定位 Skill 根目录。

    :param data: ZIP 二进制内容
    :param archive_name: 原始文件名，用于推断 skill_id
    :param skill_id_override: 用户指定的本地 skill_id
    :return: ZipSkillAnalysis
    """
    files = _collect_zip_files(data)
    skill_md_paths = sorted(
        name for name, _ in files if PurePosixPath(name).name == "SKILL.md"
    )
    if not skill_md_paths:
        raise ZipSkillImportError("ZIP 包内未找到 SKILL.md，请确认压缩的是 Skill 目录。")

    ambiguous: list[str] = []
    if len(skill_md_paths) > 1:
        min_depth = min(len(PurePosixPath(p).parts) for p in skill_md_paths)
        shallow = [p for p in skill_md_paths if len(PurePosixPath(p).parts) == min_depth]
        if len(shallow) > 1:
            ambiguous = shallow
            raise ZipSkillImportError(
                "ZIP 包内存在多个 Skill（多个 SKILL.md），请拆分为单独 ZIP 或指定本地 ID。"
                f" 候选：{', '.join(shallow)}"
            )
        skill_md_path = shallow[0]
        detected_from = "shallowest_skill_md"
    else:
        skill_md_path = skill_md_paths[0]
        detected_from = "single_skill_md"

    skill_root = str(PurePosixPath(skill_md_path).parent)
    if skill_root == ".":
        skill_root = ""

    rel_files: list[tuple[str, bytes]] = []
    prefix = f"{skill_root}/" if skill_root else ""
    total_bytes = 0
    for name, content in files:
        if skill_root:
            if name != skill_md_path and not name.startswith(prefix):
                continue
            rel_name = name[len(prefix):] if name.startswith(prefix) else name
        else:
            # SKILL.md 在 ZIP 根目录：保留包内全部有效文件
            rel_name = name
        _assert_safe_relative_path(rel_name)
        rel_files.append((rel_name, content))
        total_bytes += len(content)

    if not rel_files:
        raise ZipSkillImportError("未能从 ZIP 中提取 Skill 文件。")
    if total_bytes > MAX_TOTAL_BYTES:
        raise ZipSkillImportError(f"Skill 总体积超过上限 {MAX_TOTAL_BYTES} bytes。")

    skill_md_bytes = next(
        (content for rel, content in rel_files if rel == "SKILL.md"),
        None,
    )
    if skill_md_bytes is None:
        raise ZipSkillImportError("Skill 目录缺少 SKILL.md。")

    skill_md_text = skill_md_bytes.decode("utf-8", errors="replace")
    ok, msg = validate_skill_md_text(skill_md_text)
    if not ok:
        raise ZipSkillImportError(f"SKILL.md 校验失败：{msg}")

    if skill_id_override:
        skill_id = _normalize_skill_id(skill_id_override)
        detected_from = f"{detected_from}:override"
    elif skill_root:
        skill_id = _normalize_skill_id(PurePosixPath(skill_root).name)
        detected_from = f"{detected_from}:folder"
    else:
        stem = Path(archive_name or "").stem
        if stem and SKILL_ID_PATTERN.match(stem):
            skill_id = _normalize_skill_id(stem)
            detected_from = f"{detected_from}:archive_name"
        else:
            fm_name = _parse_frontmatter_field(skill_md_text, "name")
            skill_id = _slugify_from_name(fm_name)
            detected_from = f"{detected_from}:frontmatter_name"

    return ZipSkillAnalysis(
        skill_id=skill_id,
        skill_root=skill_root or "(zip root)",
        detected_from=detected_from,
        archive_name=archive_name or "",
        file_count=len(rel_files),
        total_bytes=total_bytes,
        sample_files=[name for name, _ in rel_files[:12]],
        skill_md_preview={
            "name": _parse_frontmatter_field(skill_md_text, "name"),
            "description": _parse_frontmatter_field(skill_md_text, "description"),
            "version": _parse_frontmatter_field(skill_md_text, "version"),
            "lang": _parse_frontmatter_field(skill_md_text, "lang"),
        },
        ambiguous_candidates=ambiguous,
    )


class ZipSkillImporter:
    """ZIP Skill 导入器。"""

    def __init__(self, loader: SkillLoader | None = None) -> None:
        self.loader = loader or get_skill_loader()
        self.library_dir = self.loader.library_dir

    def preview(
        self,
        data: bytes,
        *,
        archive_name: str = "",
        skill_id_override: str | None = None,
    ) -> ZipImportPreview:
        """预览 ZIP Skill，不写入磁盘。"""
        analysis = analyze_zip_skill(
            data,
            archive_name=archive_name,
            skill_id_override=skill_id_override,
        )
        dest = self.library_dir / analysis.skill_id
        return ZipImportPreview(
            analysis=analysis,
            exists_locally=dest.exists(),
            local_path=str(dest),
        )

    def import_skill(
        self,
        data: bytes,
        *,
        archive_name: str = "",
        skill_id_override: str | None = None,
        overwrite: bool = False,
    ) -> ZipImportResult:
        """从 ZIP 导入 skill 到本地 library/。"""
        preview = self.preview(
            data,
            archive_name=archive_name,
            skill_id_override=skill_id_override,
        )
        analysis = preview.analysis
        dest = self.library_dir / analysis.skill_id

        if dest.exists() and not overwrite:
            raise ZipSkillImportError(
                f"本地已存在 skill `{analysis.skill_id}`（{dest}）。如需覆盖请勾选 overwrite。"
            )

        files = _collect_zip_files(data)
        skill_md_path = None
        for name in (p for p, _ in files if PurePosixPath(p).name == "SKILL.md"):
            root = str(PurePosixPath(name).parent)
            if root == ".":
                root = ""
            expected_root = "" if analysis.skill_root == "(zip root)" else analysis.skill_root
            if root == expected_root:
                skill_md_path = name
                break
        if not skill_md_path:
            raise ZipSkillImportError("导入时未能重新定位 SKILL.md。")

        skill_root = str(PurePosixPath(skill_md_path).parent)
        if skill_root == ".":
            skill_root = ""
        prefix = f"{skill_root}/" if skill_root else ""

        if dest.exists() and overwrite:
            self._clear_skill_dir(dest)

        dest.mkdir(parents=True, exist_ok=True)
        written = 0
        total_bytes = 0
        for name, content in files:
            if skill_root:
                if name != skill_md_path and not name.startswith(prefix):
                    continue
                rel_name = name[len(prefix):] if name.startswith(prefix) else name
            else:
                rel_name = name
            _assert_safe_relative_path(rel_name)
            target = dest / rel_name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            written += 1
            total_bytes += len(content)

        skill_md_text = (dest / "SKILL.md").read_text(encoding="utf-8", errors="replace")
        ok, msg = validate_skill_md_text(skill_md_text)
        if not ok:
            raise ZipSkillImportError(f"写入后 SKILL.md 校验失败：{msg}")

        self.loader.reset_cache()
        logger.info(
            "[skill-import-zip] imported skill_id={} files={} bytes={} from {}",
            analysis.skill_id, written, total_bytes, archive_name or "upload.zip",
        )
        return ZipImportResult(
            skill_id=analysis.skill_id,
            dest_path=str(dest),
            files_written=written,
            bytes_written=total_bytes,
            overwritten=bool(preview.exists_locally and overwrite),
            validation_message=msg,
            detected_from=analysis.detected_from,
        )

    def _clear_skill_dir(self, dest: Path) -> None:
        """清空已有 skill 目录。"""
        if not dest.is_dir():
            return
        for child in sorted(dest.rglob("*"), reverse=True):
            if child.is_file():
                child.unlink(missing_ok=True)
            elif child.is_dir():
                try:
                    child.rmdir()
                except OSError:
                    pass
