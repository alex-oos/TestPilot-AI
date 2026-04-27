"""QA Skills 管理 / 审计 / 智能路由相关 API。"""
import json
import sqlite3
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel

from app.ai import quality_gate
from app.ai import llm_cache, llm_concurrency, llm_pricing
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


# ---------------- 用例质量门禁（Quality Gate） ----------------

class QualityScoreRequest(BaseModel):
    cases: list[dict]
    low_threshold: int | None = None


@router.post("/ai/quality/score")
async def quality_score(
    req: QualityScoreRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """对一批用例做离线质量评分。"""
    threshold = int(req.low_threshold or settings.QUALITY_GATE_LOW_THRESHOLD)
    audit = quality_gate.score_cases(req.cases or [])
    payload = quality_gate.audit_to_payload(audit, low_threshold=threshold)
    return success(payload, request.state.tid)


def _resolve_app_db_path() -> Path:
    base = Path(__file__).resolve().parents[3]  # backend/
    db = settings.SQLITE_DB_PATH
    if db.startswith("./"):
        db = db[2:]
    return (base / db).resolve()


def _load_task_generation_cases(task_id: str) -> list[dict]:
    """从 task_details.data_json 中读取 generation 阶段产出的 cases。"""
    db_path = _resolve_app_db_path()
    if not db_path.exists():
        return []
    try:
        conn = sqlite3.connect(str(db_path))
        try:
            cur = conn.execute(
                "SELECT data_json FROM task_details WHERE task_id=? AND phase_key=?",
                (task_id, "generation"),
            )
            row = cur.fetchone()
        finally:
            conn.close()
    except Exception:
        return []
    if not row or not row[0]:
        return []
    try:
        data = json.loads(row[0])
    except Exception:
        return []
    if isinstance(data, dict):
        for k in ("cases", "test_cases", "items"):
            v = data.get(k)
            if isinstance(v, list):
                return v
    if isinstance(data, list):
        return data
    return []


@router.get("/ai/quality/task/{task_id}")
async def quality_task(
    task_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """读取指定 task 的 generation 用例并实时打分。"""
    cases = _load_task_generation_cases(task_id)
    if not cases:
        raise HTTPException(status_code=404, detail=f"task {task_id} 没有可读取的 generation 用例")
    audit = quality_gate.score_cases(cases)
    payload = quality_gate.audit_to_payload(audit, low_threshold=settings.QUALITY_GATE_LOW_THRESHOLD)
    payload["task_id"] = task_id
    return success(payload, request.state.tid)


# ---------------- LLM 治理观测 ----------------

@router.get("/ai/llm/cache/stats")
async def llm_cache_stats(request: Request, current_user: dict = Depends(get_current_user)):
    return success(llm_cache.stats(), request.state.tid)


@router.post("/ai/llm/cache/purge")
async def llm_cache_purge(request: Request, current_user: dict = Depends(get_current_user)):
    n_expired = llm_cache.purge_expired()
    return success({"purged_expired": n_expired, **llm_cache.stats()}, request.state.tid)


@router.delete("/ai/llm/cache")
async def llm_cache_clear(request: Request, current_user: dict = Depends(get_current_user)):
    n = llm_cache.clear_all()
    return success({"cleared": n, **llm_cache.stats()}, request.state.tid)


@router.get("/ai/llm/concurrency/stats")
async def llm_concurrency_stats(request: Request, current_user: dict = Depends(get_current_user)):
    return success(llm_concurrency.stats(), request.state.tid)


@router.get("/ai/llm/pricing")
async def llm_pricing_endpoint(request: Request, current_user: dict = Depends(get_current_user)):
    return success(llm_pricing.list_pricing(), request.state.tid)


@router.get("/ai/llm/cost/recent")
async def llm_cost_recent(
    request: Request,
    days: int = Query(7, ge=1, le=90),
    current_user: dict = Depends(get_current_user),
):
    return success(skill_audit.get_cost_stats(days=days), request.state.tid)


@router.get("/ai/llm/task/{task_id}/calls")
async def llm_task_calls(
    task_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    return success(skill_audit.get_task_call_stats(task_id), request.state.tid)


@router.post("/ai/skills/audit/purge")
async def audit_purge(
    request: Request,
    days: int | None = Query(None, ge=1, le=365),
    current_user: dict = Depends(get_current_user),
):
    """按保留天数清理审计记录（默认使用 AUDIT_RETENTION_DAYS）。"""
    retention = int(days or settings.AUDIT_RETENTION_DAYS)
    n = skill_audit.purge_old(retention)
    return success({"purged": n, "retention_days": retention}, request.state.tid)
