"""SKILL 加载器：解析 SKILL.md frontmatter + prompts/ + 全量辅助资源。

加载内容：
- SKILL.md frontmatter（name / description / version / lang / tags）
- prompts/ 下所有 .md
- output-templates/ 下所有文件（仅元信息 + 内容预览）
- examples/ 下所有 .md / .json / .tsv（用于 few-shot）
- references/ 下所有 .md
- README.md（描述展示）
- 项目级 overlay（library/_overlays/<project>/<skill_id>/...）会被叠加
"""

from __future__ import annotations

import re
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger

from app.core.config import settings


class SkillNotFoundError(Exception):
    """指定的 skill 未找到。"""


@dataclass
class SkillExample:
    """examples/ 中的一个示例文件。"""
    filename: str
    kind: str           # requirement / analysis / strategy / testcase / review / other
    content: str        # 文本类型才有，二进制为空
    is_binary: bool = False


@dataclass
class SkillBundle:
    """Skill 完整内容包。"""
    skill_id: str
    skill_path: Path
    name: str
    description: str
    version: str = "0.0.0"
    lang: str = "zh"
    tags: list[str] = field(default_factory=list)
    requires: list[str] = field(default_factory=list)  # frontmatter requires:[skill_id,...]
    frontmatter: dict[str, Any] = field(default_factory=dict)
    skill_md_body: str = ""
    readme: str = ""
    prompts: dict[str, str] = field(default_factory=dict)
    primary_prompt_key: str = ""
    output_templates: dict[str, str] = field(default_factory=dict)
    examples: list[SkillExample] = field(default_factory=list)
    references: dict[str, str] = field(default_factory=dict)
    overlays_applied: list[str] = field(default_factory=list)
    dependencies: dict[str, "SkillBundle"] = field(default_factory=dict)
    content_hash: str = ""

    @property
    def primary_prompt(self) -> str:
        if self.primary_prompt_key and self.primary_prompt_key in self.prompts:
            return self.prompts[self.primary_prompt_key]
        if self.prompts:
            return next(iter(self.prompts.values()))
        return ""


# ---------------- frontmatter ----------------
def _parse_frontmatter(text: str) -> tuple[dict[str, Any], str]:
    """解析极简 YAML frontmatter（支持 key: value、列表 [a,b]、字符串）。"""
    if not text.startswith("---"):
        return {}, text
    end = text.find("\n---", 3)
    if end < 0:
        return {}, text
    fm_block = text[3:end].strip("\n")
    body = text[end + 4:].lstrip("\n")
    fm: dict[str, Any] = {}
    for line in fm_block.split("\n"):
        line = line.rstrip()
        if not line or line.lstrip().startswith("#"):
            continue
        m = re.match(r"^([A-Za-z0-9_\-]+)\s*:\s*(.*)$", line)
        if not m:
            continue
        key, value = m.group(1).strip(), m.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        # 列表 [a, b, c]
        if value.startswith("[") and value.endswith("]"):
            inner = value[1:-1].strip()
            if inner:
                items = [
                    s.strip().strip("\"'")
                    for s in inner.split(",")
                    if s.strip()
                ]
                fm[key] = items
                continue
            fm[key] = []
            continue
        fm[key] = value
    return fm, body


def _read_text_safe(path: Path) -> str | None:
    try:
        return path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return None


_KIND_BY_KEYWORDS = (
    ("review", ("review", "评审")),
    ("testcase", ("testcase", "test_case", "test-case", "用例")),
    ("strategy", ("strategy", "策略")),
    ("analysis", ("analysis", "分析")),
    ("requirement", ("requirement", "requirements", "需求")),
)


def _detect_example_kind(filename: str) -> str:
    f = filename.lower()
    for kind, kws in _KIND_BY_KEYWORDS:
        for kw in kws:
            if kw in f:
                return kind
    return "other"


def _hash_content(parts: list[str]) -> str:
    import hashlib
    h = hashlib.sha256()
    for p in parts:
        h.update(p.encode("utf-8", errors="ignore"))
        h.update(b"\x00")
    return h.hexdigest()[:12]


# ---------------- Loader ----------------
class SkillLoader:
    """从磁盘加载 skill 资源（带缓存 + overlay 叠加）。"""

    EXAMPLE_TEXT_EXT = {".md", ".markdown", ".json", ".tsv", ".csv", ".txt"}

    def __init__(self, library_dir: Path) -> None:
        self.library_dir = library_dir
        self._cache: dict[str, SkillBundle] = {}
        self._lock = threading.Lock()

    # ---------- 公共 API ----------
    def list_available(self, *, lang: str | None = None) -> list[str]:
        if not self.library_dir.exists():
            return []
        result = []
        for p in sorted(self.library_dir.iterdir()):
            if not p.is_dir() or p.name.startswith("_"):
                continue
            if not (p / "SKILL.md").exists():
                continue
            if lang:
                bundle = self._safe_load(p.name)
                if bundle and bundle.lang and bundle.lang != lang:
                    continue
            result.append(p.name)
        return result

    def load(self, skill_id: str) -> SkillBundle:
        with self._lock:
            cached = self._cache.get(skill_id)
            if cached is not None:
                return cached

        bundle = self._load_uncached(skill_id)

        with self._lock:
            self._cache[skill_id] = bundle
        return bundle

    def reset_cache(self) -> None:
        with self._lock:
            self._cache.clear()

    def get_overlay_dirs(self) -> list[Path]:
        """返回当前激活的 overlay 目录列表（按优先级）。"""
        roots: list[Path] = []
        overlays_root = self.library_dir / "_overlays"
        if not overlays_root.exists():
            return roots
        active = (getattr(settings, "QA_SKILL_OVERLAY", "") or "").strip()
        if not active:
            return roots
        # 支持逗号分隔多个 overlay
        for name in [n.strip() for n in active.split(",") if n.strip()]:
            p = overlays_root / name
            if p.is_dir():
                roots.append(p)
        return roots

    # ---------- 内部 ----------
    def _safe_load(self, sid: str) -> SkillBundle | None:
        try:
            return self.load(sid)
        except Exception:
            return None

    def _load_uncached(self, skill_id: str) -> SkillBundle:
        skill_path = self.library_dir / skill_id
        skill_md = skill_path / "SKILL.md"
        if not skill_md.exists():
            raise SkillNotFoundError(
                f"Skill '{skill_id}' 不存在 (期望路径: {skill_md})。"
                f" 可用 skill: {self.list_available()}"
            )

        raw = _read_text_safe(skill_md) or ""
        frontmatter, body = _parse_frontmatter(raw)
        name = str(frontmatter.get("name") or skill_id)
        description = str(frontmatter.get("description") or "").strip()
        version = str(frontmatter.get("version") or "1.0.0").strip()
        lang = str(frontmatter.get("lang") or "zh").strip().lower()
        tags_raw = frontmatter.get("tags")
        if isinstance(tags_raw, list):
            tags = [str(t) for t in tags_raw]
        elif isinstance(tags_raw, str) and tags_raw:
            tags = [t.strip() for t in tags_raw.split(",") if t.strip()]
        else:
            tags = []

        requires_raw = frontmatter.get("requires")
        if isinstance(requires_raw, list):
            requires = [str(r) for r in requires_raw if r]
        elif isinstance(requires_raw, str) and requires_raw:
            requires = [r.strip() for r in requires_raw.split(",") if r.strip()]
        else:
            requires = []

        readme = _read_text_safe(skill_path / "README.md") or ""

        prompts, primary_key = self._collect_prompts(skill_path, skill_id)
        templates = self._collect_templates(skill_path)
        examples = self._collect_examples(skill_path)
        references = self._collect_references(skill_path)

        # ---- overlay 叠加 ----
        overlays_applied: list[str] = []
        for ov in self.get_overlay_dirs():
            ov_skill = ov / skill_id
            if not ov_skill.is_dir():
                continue
            overlays_applied.append(ov.name)
            ov_prompts, _ = self._collect_prompts(ov_skill, skill_id)
            for k, v in ov_prompts.items():
                # overlay prompt 用文件名前缀 z_ 排在主 prompt 后；不覆盖主 prompt
                key = f"_overlay_{ov.name}__{k}"
                prompts[key] = v
            for k, v in self._collect_templates(ov_skill).items():
                templates[f"_overlay_{ov.name}__{k}"] = v
            for ex in self._collect_examples(ov_skill):
                examples.append(SkillExample(
                    filename=f"_overlay_{ov.name}__{ex.filename}",
                    kind=ex.kind, content=ex.content, is_binary=ex.is_binary,
                ))
            for k, v in self._collect_references(ov_skill).items():
                references[f"_overlay_{ov.name}__{k}"] = v

        # ---- 指纹 ----
        content_hash = _hash_content([
            raw,
            *(prompts.values()),
            *(templates.values()),
            *(ex.content for ex in examples if not ex.is_binary),
        ])

        # 递归加载依赖（防环）
        deps: dict[str, SkillBundle] = {}
        if requires:
            visiting = getattr(self, "_visiting", set())
            for dep_id in requires:
                if dep_id == skill_id or dep_id in visiting:
                    logger.warning("[skill] {} 依赖环或自引用，跳过 {}", skill_id, dep_id)
                    continue
                self._visiting = visiting | {skill_id}
                try:
                    deps[dep_id] = self._load_uncached(dep_id)
                except SkillNotFoundError as e:
                    logger.warning("[skill] {} 依赖 {} 不存在，跳过：{}", skill_id, dep_id, e)
                finally:
                    self._visiting = visiting

        bundle = SkillBundle(
            skill_id=skill_id,
            skill_path=skill_path,
            name=name,
            description=description,
            version=version,
            lang=lang,
            tags=tags,
            requires=requires,
            frontmatter=frontmatter,
            skill_md_body=body,
            readme=readme,
            prompts=prompts,
            primary_prompt_key=primary_key,
            output_templates=templates,
            examples=examples,
            references=references,
            overlays_applied=overlays_applied,
            dependencies=deps,
            content_hash=content_hash,
        )
        logger.debug(
            "[skill] loaded id={} v{} lang={} prompts={} templates={} examples={} refs={} overlays={} hash={}",
            skill_id, version, lang,
            len(prompts), len(templates), len(examples), len(references),
            overlays_applied, content_hash,
        )
        return bundle

    def _collect_prompts(self, root: Path, skill_id: str) -> tuple[dict[str, str], str]:
        prompts: dict[str, str] = {}
        primary_key = ""
        prompts_dir = root / "prompts"
        if prompts_dir.is_dir():
            for f in sorted(prompts_dir.iterdir()):
                if f.suffix.lower() not in {".md", ".txt", ".markdown"}:
                    continue
                content = _read_text_safe(f)
                if content is None:
                    continue
                prompts[f.name] = content
                if not primary_key and f.stem == skill_id:
                    primary_key = f.name
            if not primary_key and prompts:
                primary_key = next(iter(prompts.keys()))
        return prompts, primary_key

    def _collect_templates(self, root: Path) -> dict[str, str]:
        out: dict[str, str] = {}
        d = root / "output-templates"
        if not d.is_dir():
            return out
        for f in sorted(d.iterdir()):
            if not f.is_file():
                continue
            if f.suffix.lower() in {".docx", ".xlsx", ".pdf", ".png", ".jpg"}:
                out[f.name] = f"[binary {f.stat().st_size}B]"
                continue
            content = _read_text_safe(f)
            if content is not None:
                out[f.name] = content
        return out

    def _collect_examples(self, root: Path) -> list[SkillExample]:
        out: list[SkillExample] = []
        d = root / "examples"
        if not d.is_dir():
            return out
        for f in sorted(d.iterdir()):
            if not f.is_file():
                continue
            ext = f.suffix.lower()
            kind = _detect_example_kind(f.name)
            if ext in self.EXAMPLE_TEXT_EXT:
                content = _read_text_safe(f) or ""
                out.append(SkillExample(filename=f.name, kind=kind, content=content))
            else:
                out.append(SkillExample(filename=f.name, kind=kind, content="", is_binary=True))
        return out

    def _collect_references(self, root: Path) -> dict[str, str]:
        out: dict[str, str] = {}
        d = root / "references"
        if not d.is_dir():
            return out
        for f in sorted(d.rglob("*")):
            if not f.is_file():
                continue
            if f.suffix.lower() not in {".md", ".markdown", ".txt"}:
                continue
            content = _read_text_safe(f)
            if content is not None:
                out[str(f.relative_to(d))] = content
        return out


# ---------------- 单例 ----------------
_loader: SkillLoader | None = None
_loader_lock = threading.Lock()


def _resolve_library_dir() -> Path:
    raw = (getattr(settings, "QA_SKILLS_DIR", "") or "").strip()
    if raw:
        p = Path(raw)
        if not p.is_absolute():
            p = Path(__file__).resolve().parents[3] / raw
        return p
    return Path(__file__).resolve().parent / "library"


def get_skill_loader() -> SkillLoader:
    global _loader
    if _loader is None:
        with _loader_lock:
            if _loader is None:
                _loader = SkillLoader(_resolve_library_dir())
    return _loader


def load_skill(skill_id: str) -> SkillBundle:
    return get_skill_loader().load(skill_id)
