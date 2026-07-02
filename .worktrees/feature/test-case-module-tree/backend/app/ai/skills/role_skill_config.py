"""Skill 角色配置解析与 API 视图构建。

作者：Zhao Wang
"""

from __future__ import annotations

from typing import Any

from app.ai.skills import DEFAULT_SKILL_FOR_ROLE, get_skill_loader
from app.core.config import settings
from app.modules.persistence import config_center_store

PIPELINE_ROLES = ("analysis", "generation", "review")


def normalize_role(role: str) -> str:
    """将角色别名归一化为 pipeline 角色标识。"""
    value = (role or "").strip().lower()
    if value in {"analysis", "需求分析", "需求分析角色"}:
        return "analysis"
    if value in {"generation", "用例编写", "用例编写角色", "测试用例编写"}:
        return "generation"
    if value in {"review", "用例评审", "用例评审角色"}:
        return "review"
    return value


def _env_skill_override(role: str) -> str:
    """读取 .env 中角色 Skill 覆盖。"""
    env_map = {
        "analysis": settings.QA_SKILL_ANALYSIS,
        "generation": settings.QA_SKILL_GENERATION,
        "review": settings.QA_SKILL_REVIEW,
    }
    return str(env_map.get(role, "") or "").strip()


def _find_skill_config_entry(cfg: dict[str, Any], role: str) -> dict[str, Any] | None:
    """从配置中心 skill_configs 查找角色条目。"""
    normalized = normalize_role(role)
    for item in cfg.get("skill_configs") or []:
        if not isinstance(item, dict):
            continue
        if normalize_role(str(item.get("role") or "")) == normalized:
            return item
    return None


def pick_role_skill_enabled(cfg: dict[str, Any], role: str) -> bool:
    """角色是否启用 Skill builder。"""
    entry = _find_skill_config_entry(cfg, role)
    if entry is not None:
        return bool(entry.get("enabled", True))
    return True


def pick_configured_skill_id(cfg: dict[str, Any], role: str) -> str:
    """读取 skill_configs 中配置的 skill_id（不受 enabled 影响）。"""
    entry = _find_skill_config_entry(cfg, role)
    if entry:
        sid = str(entry.get("skill_id") or "").strip()
        if sid:
            return sid
    skills_map = cfg.get("skills", {}) or {}
    sid = str(skills_map.get(normalize_role(role)) or "").strip()
    if sid:
        return sid
    return ""


def resolve_effective_skill_id(cfg: dict[str, Any], role: str) -> tuple[str, str]:
    """解析生效 skill_id 与来源。

    Returns:
        (effective_skill_id, source) source 为 config|skills_map|env|catalog_default
    """
    entry = _find_skill_config_entry(cfg, role)
    if entry:
        sid = str(entry.get("skill_id") or "").strip()
        if sid and entry.get("enabled", True):
            return sid, "config"
        if sid and not entry.get("enabled", True):
            env_sid = _env_skill_override(role)
            if env_sid:
                return env_sid, "env"
            return DEFAULT_SKILL_FOR_ROLE.get(role, sid), "catalog_default"

    skills_map = cfg.get("skills", {}) or {}
    sid = str(skills_map.get(normalize_role(role)) or "").strip()
    if sid:
        return sid, "skills_map"

    env_sid = _env_skill_override(role)
    if env_sid:
        return env_sid, "env"

    return DEFAULT_SKILL_FOR_ROLE.get(role, ""), "catalog_default"


def pick_qa_skills_enabled(cfg: dict[str, Any]) -> bool:
    """全局 QA Skill 开关（配置中心优先于 env）。"""
    if "qa_skills_enabled" in cfg and cfg.get("qa_skills_enabled") is not None:
        return bool(cfg.get("qa_skills_enabled"))
    return bool(settings.USE_QA_SKILLS)


def list_skill_references(cfg: dict[str, Any], skill_id: str) -> list[dict[str, str]]:
    """列出引用指定 skill_id 且 enabled 的角色配置。"""
    sid = (skill_id or "").strip()
    refs: list[dict[str, str]] = []
    for item in cfg.get("skill_configs") or []:
        if not isinstance(item, dict):
            continue
        if not item.get("enabled", True):
            continue
        if str(item.get("skill_id") or "").strip() == sid:
            refs.append({
                "role": normalize_role(str(item.get("role") or "")),
                "config_id": str(item.get("id") or item.get("config_id") or ""),
            })
    return refs


async def build_role_config_view() -> dict[str, Any]:
    """构建 GET /ai/skill-role-config 响应。"""
    cfg = await config_center_store.get_config_center()
    loader = get_skill_loader()
    available = set(loader.list_available())
    qa_enabled = pick_qa_skills_enabled(cfg)
    roles: list[dict[str, Any]] = []
    for role in PIPELINE_ROLES:
        entry = _find_skill_config_entry(cfg, role)
        configured = pick_configured_skill_id(cfg, role) or DEFAULT_SKILL_FOR_ROLE.get(role, "")
        effective, source = resolve_effective_skill_id(cfg, role)
        skill_enabled = pick_role_skill_enabled(cfg, role)
        roles.append({
            "role": role,
            "config_id": str((entry or {}).get("id") or (entry or {}).get("config_id") or f"default-{role}-skill"),
            "skill_id": configured,
            "enabled": skill_enabled,
            "effective_skill_id": effective if qa_enabled and skill_enabled else "",
            "source": source if qa_enabled and skill_enabled else "legacy",
            "skill_exists": effective in available if effective else True,
            "default_skill_id": DEFAULT_SKILL_FOR_ROLE.get(role, ""),
            "env_override": _env_skill_override(role),
        })
    return {
        "qa_skills_enabled": qa_enabled,
        "env_qa_skills_enabled": bool(settings.USE_QA_SKILLS),
        "roles": roles,
    }


async def apply_role_config_update(payload: dict[str, Any]) -> dict[str, Any]:
    """应用 PUT /ai/skill-role-config 更新。"""
    from app.modules.domain import config_center_domain

    update_body: dict[str, Any] = {}
    if payload.get("qa_skills_enabled") is not None:
        update_body["qa_skills_enabled"] = bool(payload["qa_skills_enabled"])
    if payload.get("skill_configs") is not None:
        update_body["skill_configs"] = payload["skill_configs"]
    await config_center_domain.update_skill_configs_section(update_body)
    return await build_role_config_view()
