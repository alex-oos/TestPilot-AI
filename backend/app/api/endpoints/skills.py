"""QA Skills 管理 / 审计 / 智能路由相关 API。"""
from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.ai.skills import (
    DEFAULT_SKILL_FOR_ROLE,
    audit as skill_audit,
    discover as skill_discover,
    get_skill_loader,
)
from app.ai.skills.loader import SkillNotFoundError
from app.core.auth import get_current_user
from app.core.config import settings
from app.core.response import success

router = APIRouter()


def _bundle_summary(b) -> dict:
    return {
        "skill_id": b.skill_id,
        "name": b.name,
        "description": b.description,
        "version": b.version,
        "lang": b.lang,
        "tags": b.tags,
        "requires": b.requires,
        "primary_prompt_file": b.primary_prompt_key,
        "prompt_files": list(b.prompts.keys()),
        "prompt_length": len(b.primary_prompt),
        "templates": list(b.output_templates.keys()),
        "examples": [{"filename": e.filename, "kind": e.kind, "is_binary": e.is_binary} for e in b.examples],
        "references": list(b.references.keys()),
        "overlays_applied": b.overlays_applied,
        "content_hash": b.content_hash,
    }


@router.get("/ai/skills")
async def list_skills(
    request: Request,
    lang: str | None = Query(None, description="按语言过滤（zh/en），留空返回全部"),
    current_user: dict = Depends(get_current_user),
):
    """列出所有可用 QA Skill 及当前角色映射。"""
    loader = get_skill_loader()
    available = loader.list_available(lang=lang)

    skills_meta = []
    for sid in available:
        try:
            b = loader.load(sid)
            skills_meta.append(_bundle_summary(b))
        except Exception as exc:
            skills_meta.append({"skill_id": sid, "error": str(exc)})

    env_overrides = {
        "analysis": settings.QA_SKILL_ANALYSIS,
        "generation": settings.QA_SKILL_GENERATION,
        "review": settings.QA_SKILL_REVIEW,
        "supplement": settings.QA_SKILL_SUPPLEMENT,
        "discover": settings.QA_SKILL_DISCOVER,
    }
    role_mapping = {}
    for role, default_sid in DEFAULT_SKILL_FOR_ROLE.items():
        env_sid = (env_overrides.get(role) or "").strip()
        role_mapping[role] = {
            "default_skill_id": default_sid,
            "env_override": env_sid,
            "effective_skill_id": env_sid or default_sid,
        }

    return success({
        "enabled": bool(settings.USE_QA_SKILLS),
        "fewshot_enabled": bool(settings.QA_SKILL_FEWSHOT_ENABLED),
        "discover_enabled": bool(settings.QA_SKILL_DISCOVER_ENABLED),
        "ab_enabled": bool(settings.QA_SKILL_AB_ENABLED),
        "legacy_fallback_enabled": bool(settings.QA_SKILL_LEGACY_FALLBACK_ENABLED),
        "prompt_token_budget": int(settings.QA_SKILL_PROMPT_TOKEN_BUDGET),
        "library_dir": str(loader.library_dir),
        "active_overlays": [str(p) for p in loader.get_overlay_dirs()],
        "skills": skills_meta,
        "role_mapping": role_mapping,
    }, request.state.tid)


@router.get("/ai/skills/health")
async def skills_health_priority(request: Request, current_user: dict = Depends(get_current_user)):
    """运行时健康检查（路由冲突优先注册版）。"""
    from app.ai.skills.health import run_health_check
    rep = run_health_check()
    return success(rep.as_dict(), request.state.tid)


@router.get("/ai/skills/{skill_id}")
async def get_skill(skill_id: str, request: Request, current_user: dict = Depends(get_current_user)):
    """查看单个 skill 的全文内容（含全部资源）。"""
    loader = get_skill_loader()
    try:
        b = loader.load(skill_id)
    except SkillNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    summary = _bundle_summary(b)
    return success({
        **summary,
        "frontmatter": b.frontmatter,
        "skill_md_body": b.skill_md_body,
        "readme": b.readme,
        "prompts": b.prompts,
        "output_templates": b.output_templates,
        "examples_full": [
            {"filename": e.filename, "kind": e.kind, "is_binary": e.is_binary, "content": e.content}
            for e in b.examples
        ],
        "references_full": b.references,
    }, request.state.tid)


@router.post("/ai/skills/reload")
async def reload_skills(request: Request, current_user: dict = Depends(get_current_user)):
    """清空 skill 缓存并重新扫描。"""
    loader = get_skill_loader()
    loader.reset_cache()
    available = loader.list_available()
    return success({"reloaded": True, "available": available}, request.state.tid)


# ---------------- 审计 ----------------

@router.get("/ai/skills/audit/recent")
async def list_audit(
    request: Request,
    limit: int = Query(50, ge=1, le=500),
    role: str | None = Query(None),
    task_id: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """查看最近的 skill 调用审计记录。"""
    items = skill_audit.list_recent(limit=limit, role=role, task_id=task_id)
    return success({"items": items, "count": len(items)}, request.state.tid)


@router.delete("/ai/skills/audit")
async def clear_audit(request: Request, current_user: dict = Depends(get_current_user)):
    skill_audit.clear()
    return success({"cleared": True}, request.state.tid)


@router.get("/ai/skills/audit/persisted")
async def list_audit_persisted(
    request: Request,
    limit: int = Query(50, ge=1, le=1000),
    offset: int = Query(0, ge=0),
    role: str | None = Query(None),
    task_id: str | None = Query(None),
    skill_id: str | None = Query(None),
    current_user: dict = Depends(get_current_user),
):
    """从 SQLite 查询审计记录（分页、可按 role/task/skill 过滤）。"""
    res = skill_audit.query_persisted(
        limit=limit, offset=offset, role=role, task_id=task_id, skill_id=skill_id,
    )
    return success(res, request.state.tid)


@router.get("/ai/skills/audit/stats")
async def audit_token_stats(request: Request, current_user: dict = Depends(get_current_user)):
    """聚合统计：按 role / skill_id 维度统计 token 用量、few-shot 命中率。"""
    return success(skill_audit.get_token_usage_stats(), request.state.tid)


# 健康检查已在文件上方优先注册，避免与 /ai/skills/{skill_id} 路由冲突


# ---------------- 智能路由（discover） ----------------

class DiscoverIn(BaseModel):
    text: str


@router.post("/ai/skills/discover")
async def discover_for_text(
    payload: DiscoverIn,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """根据需求/分析文本预览智能路由结果（不发起 LLM 调用）。"""
    available = get_skill_loader().list_available()
    route = skill_discover.route_combined(payload.text or "", available_skills=available)
    route = skill_discover.filter_to_available(route, available)
    return success({"route": route, "available": available}, request.state.tid)
