"""QA Skills 管理 / 审计 / 智能路由相关 API。"""
import json
import shutil
from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai import quality_gate
from app.ai import llm_cache, llm_concurrency, llm_pricing
from app.ai.skills import (
    audit as skill_audit,
    discover as skill_discover,
    get_skill_loader,
)
from app.ai.skills.loader import SkillNotFoundError
from app.ai.skills.protected import is_protected_skill
from app.ai.skills.role_skill_config import (
    build_role_config_view,
    list_skill_references,
    pick_qa_skills_enabled,
)
from app.ai.skills.zip_exporter import ZipSkillExporter
from app.core.auth import get_current_user
from app.core.config import QA_SKILL_DISCOVER_ENABLED, settings
from app.core.database import get_db
from app.core.response import success
from app.modules.persistence import config_center_store

router = APIRouter()


class GitHubSkillImportRequest(BaseModel):
    """GitHub Skill 导入请求体。"""

    source: str
    branch: str | None = None
    skill_id: str | None = None
    overwrite: bool = False


async def _skill_usage_flags(cfg: dict, skill_id: str) -> dict:
    """计算 Skill 是否受保护、是否被角色引用。"""
    refs = list_skill_references(cfg, skill_id)
    return {
        "protected": is_protected_skill(skill_id),
        "referenced_by_roles": [r["role"] for r in refs],
        "deletable": not is_protected_skill(skill_id) and not refs,
    }


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
    """列出所有可用 QA Skill。"""
    loader = get_skill_loader()
    available = loader.list_available(lang=lang)
    cfg = await config_center_store.get_config_center()
    qa_enabled = pick_qa_skills_enabled(cfg)

    skills_meta = []
    for sid in available:
        flags = await _skill_usage_flags(cfg, sid)
        try:
            b = loader.load(sid)
            skills_meta.append({**_bundle_summary(b), **flags})
        except Exception as exc:
            skills_meta.append({"skill_id": sid, "error": str(exc), **flags})

    return success({
        "enabled": qa_enabled,
        "env_enabled": bool(settings.USE_QA_SKILLS),
        "fewshot_enabled": bool(settings.QA_SKILL_FEWSHOT_ENABLED),
        "discover_enabled": QA_SKILL_DISCOVER_ENABLED,
        "ab_enabled": bool(settings.QA_SKILL_AB_ENABLED),
        "legacy_fallback_enabled": bool(settings.QA_SKILL_LEGACY_FALLBACK_ENABLED),
        "prompt_token_budget": int(settings.QA_SKILL_PROMPT_TOKEN_BUDGET),
        "library_dir": str(loader.library_dir),
        "active_overlays": [str(p) for p in loader.get_overlay_dirs()],
        "skills": skills_meta,
    }, request.state.tid)


@router.get("/ai/skills/health")
async def skills_health_priority(request: Request, current_user: dict = Depends(get_current_user)):
    """运行时健康检查（路由冲突优先注册版）。"""
    from app.ai.skills.health import run_health_check

    role_view = await build_role_config_view()
    rep = run_health_check(role_config_view=role_view)
    return success(rep.as_dict(), request.state.tid)


@router.post("/ai/skills/import/github/preview")
async def preview_github_skill_import(
    payload: GitHubSkillImportRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """预览 GitHub Skill 导入（不写入磁盘）。"""
    from app.ai.skills.github_importer import GitHubSkillImportError, GitHubSkillImporter

    try:
        preview = await GitHubSkillImporter().preview(
            payload.source,
            branch_override=payload.branch,
            skill_id_override=payload.skill_id,
        )
    except GitHubSkillImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    ref = preview.ref
    return success({
        "ref": {
            "owner": ref.owner,
            "repo": ref.repo,
            "branch": ref.branch,
            "skill_path": ref.skill_path,
            "skill_id": ref.skill_id,
            "resolved_from": ref.resolved_from,
            "github_tree_url": (
                f"https://github.com/{ref.owner}/{ref.repo}/tree/{ref.branch}/{ref.skill_path}"
            ),
        },
        "exists_locally": preview.exists_locally,
        "local_path": preview.local_path,
        "remote_file_count": preview.remote_file_count,
        "remote_total_bytes": preview.remote_total_bytes,
        "sample_files": preview.sample_files,
    }, request.state.tid)


@router.post("/ai/skills/import/github")
async def import_github_skill(
    payload: GitHubSkillImportRequest,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """从 GitHub 一键导入 Skill 到本地 library/ 并重载缓存。"""
    from app.ai.skills.github_importer import GitHubSkillImportError, GitHubSkillImporter

    try:
        result = await GitHubSkillImporter().import_skill(
            payload.source,
            branch_override=payload.branch,
            skill_id_override=payload.skill_id,
            overwrite=bool(payload.overwrite),
        )
        loader = get_skill_loader()
        bundle_summary = None
        try:
            b = loader.load(result.skill_id)
            bundle_summary = _bundle_summary(b)
        except Exception as exc:
            bundle_summary = {"skill_id": result.skill_id, "error": str(exc)}

        ref = result.ref
        return success({
            "imported": True,
            "skill_id": result.skill_id,
            "dest_path": result.dest_path,
            "files_written": result.files_written,
            "bytes_written": result.bytes_written,
            "overwritten": result.overwritten,
            "validation_message": result.validation_message,
            "ref": {
                "owner": ref.owner,
                "repo": ref.repo,
                "branch": ref.branch,
                "skill_path": ref.skill_path,
                "resolved_from": ref.resolved_from,
                "github_tree_url": (
                    f"https://github.com/{ref.owner}/{ref.repo}/tree/{ref.branch}/{ref.skill_path}"
                ),
            },
            "skill": bundle_summary,
            "available": loader.list_available(),
        }, request.state.tid)
    except GitHubSkillImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


def _zip_analysis_payload(analysis) -> dict:
    """将 ZIP 解析结果转为 API 响应字段。"""
    return {
        "skill_id": analysis.skill_id,
        "skill_root": analysis.skill_root,
        "detected_from": analysis.detected_from,
        "archive_name": analysis.archive_name,
        "file_count": analysis.file_count,
        "total_bytes": analysis.total_bytes,
        "sample_files": analysis.sample_files,
        "skill_md_preview": analysis.skill_md_preview,
        "ambiguous_candidates": analysis.ambiguous_candidates,
    }


@router.post("/ai/skills/import/zip/preview")
async def preview_zip_skill_import(
    request: Request,
    file: UploadFile = File(..., description="Skill ZIP 压缩包"),
    skill_id: str | None = Form(None, description="可选，覆盖导入后的 skill 目录名"),
    current_user: dict = Depends(get_current_user),
):
    """预览 ZIP Skill 导入（自动解析结构，不写入磁盘）。"""
    from app.ai.skills.zip_importer import ZipSkillImportError, ZipSkillImporter

    raw = await file.read()
    try:
        preview = ZipSkillImporter().preview(
            raw,
            archive_name=file.filename or "",
            skill_id_override=skill_id,
        )
    except ZipSkillImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return success({
        "analysis": _zip_analysis_payload(preview.analysis),
        "exists_locally": preview.exists_locally,
        "local_path": preview.local_path,
    }, request.state.tid)


@router.post("/ai/skills/import/zip")
async def import_zip_skill(
    request: Request,
    file: UploadFile = File(..., description="Skill ZIP 压缩包"),
    skill_id: str | None = Form(None, description="可选，覆盖导入后的 skill 目录名"),
    overwrite: bool = Form(False, description="是否覆盖已存在的同名 Skill"),
    current_user: dict = Depends(get_current_user),
):
    """从 ZIP 包导入 Skill 到本地 library/ 并重载缓存。"""
    from app.ai.skills.zip_importer import ZipSkillImportError, ZipSkillImporter

    raw = await file.read()
    try:
        result = ZipSkillImporter().import_skill(
            raw,
            archive_name=file.filename or "",
            skill_id_override=skill_id,
            overwrite=bool(overwrite),
        )
        loader = get_skill_loader()
        bundle_summary = None
        try:
            b = loader.load(result.skill_id)
            bundle_summary = _bundle_summary(b)
        except Exception as exc:
            bundle_summary = {"skill_id": result.skill_id, "error": str(exc)}

        return success({
            "imported": True,
            "skill_id": result.skill_id,
            "dest_path": result.dest_path,
            "files_written": result.files_written,
            "bytes_written": result.bytes_written,
            "overwritten": result.overwritten,
            "validation_message": result.validation_message,
            "detected_from": result.detected_from,
            "skill": bundle_summary,
            "available": loader.list_available(),
        }, request.state.tid)
    except ZipSkillImportError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/ai/skills/{skill_id}/export")
async def export_skill_zip(
    skill_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """导出 Skill 目录为 ZIP。"""
    try:
        data, filename = ZipSkillExporter().export_bytes(skill_id)
    except SkillNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return Response(
        content=data,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.delete("/ai/skills/{skill_id}")
async def delete_skill(
    skill_id: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
):
    """删除非受保护且未被角色引用的 Skill 目录。"""
    sid = (skill_id or "").strip()
    if is_protected_skill(sid):
        raise HTTPException(status_code=403, detail=f"Skill '{sid}' 为内置受保护 Skill，不可删除")

    cfg = await config_center_store.get_config_center()
    refs = list_skill_references(cfg, sid)
    if refs:
        raise HTTPException(
            status_code=409,
            detail={
                "message": f"Skill '{sid}' 仍被角色配置引用，请先修改绑定",
                "references": refs,
            },
        )

    loader = get_skill_loader()
    skill_dir = loader.library_dir / sid
    if not skill_dir.is_dir():
        raise HTTPException(status_code=404, detail=f"Skill 不存在: {sid}")

    shutil.rmtree(skill_dir)
    loader.reset_cache()
    return success({"deleted": True, "skill_id": sid}, request.state.tid)


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


async def _load_task_generation_cases(task_id: str, db: AsyncSession) -> list[dict]:
    """从 task_details.data_json 中异步读取 generation 阶段产出的 cases。"""
    try:
        result = await db.execute(
            text("SELECT data_json FROM task_details WHERE task_id=:tid AND phase_key=:pk"),
            {"tid": task_id, "pk": "generation"},
        )
        row = result.first()
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
    db: AsyncSession = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """读取指定 task 的 generation 用例并实时打分。"""
    cases = await _load_task_generation_cases(task_id, db)
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
