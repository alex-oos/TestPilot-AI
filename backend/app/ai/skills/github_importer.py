"""从 GitHub 仓库一键导入 QA Skill 到本地 library/。

支持输入：
- 完整 tree URL：https://github.com/owner/repo/tree/branch/path/to/skill-id
- blob URL（指向 SKILL.md 或其父目录）
- 简写：owner/repo/branch/path/to/skill-id
- 仅 skill_id：在默认仓库 naodeng/awesome-qa-skills 的常见路径下自动探测

作者：Zhao Wang
"""

from __future__ import annotations

import base64
import re
from dataclasses import dataclass, field
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import unquote, urlparse

import httpx
from loguru import logger

from app.ai.skills.loader import SkillLoader, get_skill_loader

DEFAULT_OWNER = "naodeng"
DEFAULT_REPO = "awesome-qa-skills"
DEFAULT_BRANCH = "main"
DEFAULT_SKILL_SEARCH_PREFIXES = (
    "skills/zh/testing-types",
    "skills/zh/testing-workflows",
    "skills/en/testing-types",
    "skills/en/testing-workflows",
)

SKILL_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9._-]{0,63}$", re.I)
MAX_FILES = 500
MAX_TOTAL_BYTES = 8 * 1024 * 1024
MAX_FILE_BYTES = 2 * 1024 * 1024
HTTP_TIMEOUT = 30.0


class GitHubSkillImportError(Exception):
    """GitHub Skill 导入失败。"""


@dataclass
class GitHubSkillRef:
    """GitHub Skill 引用信息。"""

    owner: str
    repo: str
    branch: str
    skill_path: str
    skill_id: str
    resolved_from: str = ""


@dataclass
class GitHubImportPreview:
    """导入预览结果。"""

    ref: GitHubSkillRef
    exists_locally: bool
    local_path: str
    remote_file_count: int = 0
    remote_total_bytes: int = 0
    sample_files: list[str] = field(default_factory=list)


@dataclass
class GitHubImportResult:
    """导入执行结果。"""

    skill_id: str
    dest_path: str
    files_written: int
    bytes_written: int
    overwritten: bool
    ref: GitHubSkillRef
    validation_message: str = ""


def _normalize_skill_id(raw: str) -> str:
    sid = (raw or "").strip().strip("/")
    if not sid or not SKILL_ID_PATTERN.match(sid):
        raise GitHubSkillImportError(
            f"skill_id 非法：{raw!r}。仅允许字母、数字、点、下划线、连字符，且长度 ≤ 64。"
        )
    return sid


def _strip_github_noise(path: str) -> str:
    p = (path or "").strip().strip("/")
    if p.endswith("/SKILL.md"):
        p = str(PurePosixPath(p).parent)
    return p.strip("/")


def _parse_tree_or_blob_path(parts: list[str]) -> tuple[str, str]:
    """解析 /tree/branch/... 或 /blob/branch/... 路径。"""
    if len(parts) < 4:
        raise GitHubSkillImportError("GitHub URL 路径不完整，缺少 branch 或 skill 目录。")
    branch = parts[3]
    skill_path = _strip_github_noise("/".join(parts[4:]))
    if not skill_path:
        raise GitHubSkillImportError("未能从 URL 解析出 skill 目录路径。")
    skill_id = PurePosixPath(skill_path).name
    return branch, skill_path, _normalize_skill_id(skill_id)


def parse_github_skill_source(source: str, *, branch_override: str | None = None) -> GitHubSkillRef:
    """解析用户输入的 GitHub Skill 来源。

    :param source: GitHub URL、简写路径或 skill_id
    :param branch_override: 可选分支覆盖
    :return: GitHubSkillRef
    """
    raw = (source or "").strip()
    if not raw:
        raise GitHubSkillImportError("导入来源不能为空。")

    branch_override = (branch_override or "").strip() or None

    # 1) 完整 GitHub URL
    if raw.startswith("http://") or raw.startswith("https://"):
        parsed = urlparse(raw)
        host = (parsed.netloc or "").lower()
        if host not in {"github.com", "www.github.com"}:
            raise GitHubSkillImportError("仅支持 github.com 链接。")
        parts = [p for p in parsed.path.split("/") if p]
        if len(parts) < 2:
            raise GitHubSkillImportError("GitHub URL 无效。")
        owner, repo = parts[0], parts[1]
        if len(parts) >= 4 and parts[2] in {"tree", "blob"}:
            branch, skill_path, skill_id = _parse_tree_or_blob_path(parts)
            branch = branch_override or branch
            return GitHubSkillRef(
                owner=owner,
                repo=repo,
                branch=branch,
                skill_path=skill_path,
                skill_id=skill_id,
                resolved_from="github_url",
            )
        raise GitHubSkillImportError("GitHub URL 需为 /tree/... 或 /blob/... 形式。")

    # 2) owner/repo/branch/path...
    slash_parts = [p for p in raw.split("/") if p]
    if len(slash_parts) >= 4 and "." not in slash_parts[0] and slash_parts[0] != "skills":
        owner, repo, branch = slash_parts[0], slash_parts[1], slash_parts[2]
        skill_path = _strip_github_noise("/".join(slash_parts[3:]))
        if not skill_path:
            raise GitHubSkillImportError("简写路径缺少 skill 目录。")
        skill_id = _normalize_skill_id(PurePosixPath(skill_path).name)
        return GitHubSkillRef(
            owner=owner,
            repo=repo,
            branch=branch_override or branch,
            skill_path=skill_path,
            skill_id=skill_id,
            resolved_from="slash_shorthand",
        )

    # 3) skills/zh/testing-types/skill-id
    if slash_parts and slash_parts[0] == "skills":
        skill_path = _strip_github_noise("/".join(slash_parts))
        skill_id = _normalize_skill_id(PurePosixPath(skill_path).name)
        return GitHubSkillRef(
            owner=DEFAULT_OWNER,
            repo=DEFAULT_REPO,
            branch=branch_override or DEFAULT_BRANCH,
            skill_path=skill_path,
            skill_id=skill_id,
            resolved_from="default_repo_path",
        )

    # 4) 仅 skill_id — 默认仓库下自动探测
    skill_id = _normalize_skill_id(raw)
    return GitHubSkillRef(
        owner=DEFAULT_OWNER,
        repo=DEFAULT_REPO,
        branch=branch_override or DEFAULT_BRANCH,
        skill_path="",
        skill_id=skill_id,
        resolved_from="skill_id_autodetect",
    )


def validate_skill_md_text(text: str) -> tuple[bool, str]:
    """校验 SKILL.md frontmatter。"""
    if not text.startswith("---"):
        return False, "缺少 frontmatter"
    end = text.find("\n---", 3)
    if end < 0:
        return False, "frontmatter 未闭合"
    fm = text[3:end]
    if "name:" not in fm:
        return False, "frontmatter 缺少 name"
    if "description:" not in fm:
        return False, "frontmatter 缺少 description"
    return True, "ok"


class GitHubSkillImporter:
    """GitHub Skill 导入器。"""

    def __init__(self, loader: SkillLoader | None = None) -> None:
        self.loader = loader or get_skill_loader()
        self.library_dir = self.loader.library_dir

    async def resolve_ref(self, ref: GitHubSkillRef) -> GitHubSkillRef:
        """若为 skill_id 自动探测模式，解析实际 skill_path。"""
        if ref.skill_path:
            return ref
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
            for prefix in DEFAULT_SKILL_SEARCH_PREFIXES:
                candidate = f"{prefix}/{ref.skill_id}"
                if await self._path_exists(client, ref.owner, ref.repo, candidate, ref.branch):
                    resolved = GitHubSkillRef(
                        owner=ref.owner,
                        repo=ref.repo,
                        branch=ref.branch,
                        skill_path=candidate,
                        skill_id=ref.skill_id,
                        resolved_from=f"{ref.resolved_from}:{candidate}",
                    )
                    logger.info("[skill-import] autodetect {} → {}", ref.skill_id, candidate)
                    return resolved
        raise GitHubSkillImportError(
            f"在 {ref.owner}/{ref.repo} 默认路径下未找到 skill：{ref.skill_id}。"
            f"请提供完整 GitHub tree URL。"
        )

    async def preview(
        self,
        source: str,
        *,
        branch_override: str | None = None,
        skill_id_override: str | None = None,
    ) -> GitHubImportPreview:
        """预览远程 skill，不写入磁盘。"""
        ref = parse_github_skill_source(source, branch_override=branch_override)
        if skill_id_override:
            ref.skill_id = _normalize_skill_id(skill_id_override)
        ref = await self.resolve_ref(ref)

        files = await self._fetch_tree(ref)
        total_bytes = sum(len(content) for _, content in files)
        dest = self.library_dir / ref.skill_id
        return GitHubImportPreview(
            ref=ref,
            exists_locally=dest.exists(),
            local_path=str(dest),
            remote_file_count=len(files),
            remote_total_bytes=total_bytes,
            sample_files=[name for name, _ in files[:12]],
        )

    async def import_skill(
        self,
        source: str,
        *,
        branch_override: str | None = None,
        skill_id_override: str | None = None,
        overwrite: bool = False,
    ) -> GitHubImportResult:
        """从 GitHub 导入 skill 到本地 library/。"""
        preview = await self.preview(
            source,
            branch_override=branch_override,
            skill_id_override=skill_id_override,
        )
        ref = preview.ref
        dest = self.library_dir / ref.skill_id

        if dest.exists() and not overwrite:
            raise GitHubSkillImportError(
                f"本地已存在 skill `{ref.skill_id}`（{dest}）。如需覆盖请勾选 overwrite。"
            )

        files = await self._fetch_tree(ref)
        skill_md = next((content for name, content in files if name == "SKILL.md"), None)
        if skill_md is None:
            raise GitHubSkillImportError(f"远程目录 {ref.skill_path} 缺少 SKILL.md。")
        ok, msg = validate_skill_md_text(skill_md.decode("utf-8"))
        if not ok:
            raise GitHubSkillImportError(f"SKILL.md 校验失败：{msg}")

        if dest.exists() and overwrite:
            self._clear_skill_dir(dest)

        dest.mkdir(parents=True, exist_ok=True)
        written = 0
        total_bytes = 0
        for rel_name, content in files:
            target = dest / rel_name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
            written += 1
            total_bytes += len(content)

        self.loader.reset_cache()
        logger.info(
            "[skill-import] imported skill_id={} files={} bytes={} from {}/{}@{}:{}",
            ref.skill_id, written, total_bytes, ref.owner, ref.repo, ref.branch, ref.skill_path,
        )
        return GitHubImportResult(
            skill_id=ref.skill_id,
            dest_path=str(dest),
            files_written=written,
            bytes_written=total_bytes,
            overwritten=bool(preview.exists_locally and overwrite),
            ref=ref,
            validation_message=msg,
        )

    async def _path_exists(
        self,
        client: httpx.AsyncClient,
        owner: str,
        repo: str,
        path: str,
        branch: str,
    ) -> bool:
        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        resp = await client.get(url, params={"ref": branch}, headers=_github_headers())
        if resp.status_code == 404:
            return False
        if resp.status_code >= 400:
            raise GitHubSkillImportError(f"GitHub API 错误 ({resp.status_code})：{resp.text[:200]}")
        return True

    async def _fetch_tree(self, ref: GitHubSkillRef) -> list[tuple[str, bytes]]:
        async with httpx.AsyncClient(timeout=HTTP_TIMEOUT, follow_redirects=True) as client:
            collected: list[tuple[str, bytes]] = []
            await self._walk_contents(
                client,
                ref.owner,
                ref.repo,
                ref.skill_path,
                ref.branch,
                prefix="",
                collected=collected,
            )
            return collected

    async def _walk_contents(
        self,
        client: httpx.AsyncClient,
        owner: str,
        repo: str,
        path: str,
        branch: str,
        *,
        prefix: str,
        collected: list[tuple[str, bytes]],
    ) -> None:
        if len(collected) >= MAX_FILES:
            raise GitHubSkillImportError(f"远程文件数超过上限 {MAX_FILES}。")

        url = f"https://api.github.com/repos/{owner}/{repo}/contents/{path}"
        resp = await client.get(url, params={"ref": branch}, headers=_github_headers())
        if resp.status_code == 404:
            raise GitHubSkillImportError(f"GitHub 路径不存在：{owner}/{repo}/{path}@{branch}")
        if resp.status_code >= 400:
            raise GitHubSkillImportError(f"GitHub API 错误 ({resp.status_code})：{resp.text[:200]}")

        payload = resp.json()
        entries: list[dict[str, Any]]
        if isinstance(payload, dict):
            entries = [payload]
        elif isinstance(payload, list):
            entries = payload
        else:
            raise GitHubSkillImportError("GitHub API 返回格式异常。")

        total_bytes = sum(len(content) for _, content in collected)
        for entry in entries:
            entry_type = entry.get("type")
            name = unquote(str(entry.get("name") or ""))
            if not name or name in {".git", ".DS_Store"}:
                continue
            rel_name = f"{prefix}/{name}".strip("/")
            self._assert_safe_relative_path(rel_name)

            if entry_type == "dir":
                sub_path = str(entry.get("path") or f"{path}/{name}")
                await self._walk_contents(
                    client, owner, repo, sub_path, branch,
                    prefix=rel_name, collected=collected,
                )
                continue

            if entry_type != "file":
                continue

            content = await self._download_file_content(client, entry)
            total_bytes += len(content)
            if len(content) > MAX_FILE_BYTES:
                raise GitHubSkillImportError(f"单文件过大：{rel_name} ({len(content)} bytes)")
            if total_bytes > MAX_TOTAL_BYTES:
                raise GitHubSkillImportError(f"skill 总体积超过上限 {MAX_TOTAL_BYTES} bytes。")
            collected.append((rel_name, content))

    async def _download_file_content(
        self,
        client: httpx.AsyncClient,
        entry: dict[str, Any],
    ) -> bytes:
        encoded = entry.get("content")
        if isinstance(encoded, str) and encoded:
            try:
                return base64.b64decode(encoded)
            except Exception as exc:
                raise GitHubSkillImportError(f"解码 GitHub 文件失败：{entry.get('path')}") from exc

        download_url = entry.get("download_url")
        if not download_url:
            raise GitHubSkillImportError(f"无法获取文件下载地址：{entry.get('path')}")
        resp = await client.get(str(download_url), headers={"Accept": "application/octet-stream"})
        if resp.status_code >= 400:
            raise GitHubSkillImportError(f"下载文件失败 ({resp.status_code})：{download_url}")
        return resp.content

    def _assert_safe_relative_path(self, rel_name: str) -> None:
        pure = PurePosixPath(rel_name)
        if pure.is_absolute() or ".." in pure.parts:
            raise GitHubSkillImportError(f"非法文件路径：{rel_name}")

    def _clear_skill_dir(self, dest: Path) -> None:
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


def _github_headers() -> dict[str, str]:
    """构建 GitHub API 请求头（可选 GITHUB_TOKEN / GH_TOKEN）。"""
    import os

    headers = {
        "Accept": "application/vnd.github+json",
        "User-Agent": "ai-test-platform-skill-importer",
    }
    gh_token = (os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN") or "").strip()
    if gh_token:
        headers["Authorization"] = f"Bearer {gh_token}"
    return headers
