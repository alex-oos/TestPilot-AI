"""用例生成编排器：策略解析、分批生成、覆盖补全、质量审计。

作者: Zhao Wang
"""

from __future__ import annotations

import asyncio
import json
import time
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Optional

from loguru import logger

from app.ai import quality_gate
from app.ai.coverage_planner import (
    build_coverage_matrix,
    find_coverage_gaps,
    merge_and_dedupe_cases,
    normalize_merged_cases,
    split_strategy_batches,
)
from app.ai.parsers import _fill_case_blanks, _needs_case_repair, _parse_cases_payload
from app.ai.role_config import _load_role_config, _raise_if_llm_error
from app.ai.skills import build_generation_messages, build_supplement_messages
from app.ai.strategy_schema import (
    TestStrategyV1,
    compute_expected_min_cases,
    strategy_module_names,
    try_parse_strategy,
)
from app.ai.llm import llm_client
from app.core.config import settings


ProgressCallback = Optional[Callable[[dict[str, Any]], Awaitable[None] | None]]


@dataclass
class GenerationResult:
    """生成结果。"""

    cases: list[dict[str, Any]] = field(default_factory=list)
    generation_mode: str = "legacy"
    strategy_version: str | None = None
    design_structured: dict[str, Any] | None = None
    coverage_matrix: dict[str, Any] | None = None
    batch_stats: list[dict[str, Any]] = field(default_factory=list)
    quality_audit: dict[str, Any] = field(default_factory=dict)
    expected_min_cases: int = 0
    kb_retrieval: dict[str, Any] | None = None
    filled_by_template: list[Any] = field(default_factory=list)
    pre_supplement_score: int | None = None
    post_supplement_score: int | None = None


def _structured_enabled() -> bool:
    return bool(getattr(settings, "STRUCTURED_STRATEGY_ENABLED", False))


def _fill_mode() -> str:
    return str(getattr(settings, "GENERATION_FILL_MODE", "legacy") or "legacy").lower()


def _bumped_max_tokens(role_cfg: dict[str, Any], minimum: int, *, extra: int = 0) -> int:
    raw = role_cfg.get("max_tokens")
    try:
        current = int(raw) if raw is not None else 0
    except Exception:
        current = 0
    cap = int(getattr(settings, "GENERATION_MAX_TOKENS_CAP", 16384))
    return min(max(current, minimum) + extra, cap)


async def _call_generation_llm(
    messages: list[dict[str, str]],
    role_cfg: dict[str, Any],
    *,
    max_tokens_extra: int = 0,
) -> str:
    """单次 LLM 生成调用。"""
    return await llm_client.chat(
        messages=messages,
        temperature=float(role_cfg.get("temperature", 0.1)),
        response_format={"type": "json_object"},
        model=role_cfg["model"],
        api_key=role_cfg.get("api_key"),
        base_url=role_cfg.get("base_url"),
        max_tokens=_bumped_max_tokens(role_cfg, 16384, extra=max_tokens_extra),
        top_p=role_cfg.get("top_p"),
    )


async def _parse_cases_from_llm(raw: str, role_cfg: dict[str, Any]) -> list[dict[str, Any]]:
    """解析 LLM 返回的 cases。"""
    _raise_if_llm_error(raw, "测试用例生成")
    try:
        return _parse_cases_payload(raw)
    except Exception:
        repair_messages = [
            {"role": "system", "content": "修复为合法 JSON 对象，必须含 cases 数组。只返回 JSON。"},
            {"role": "user", "content": raw},
        ]
        repaired = await _call_generation_llm(repair_messages, role_cfg)
        _raise_if_llm_error(repaired, "测试用例修复")
        return _parse_cases_payload(repaired)


def _safe_fill_blanks(cases: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[Any]]:
    """按 GENERATION_FILL_MODE 处理空白字段。"""
    mode = _fill_mode()
    filled_ids: list[Any] = []
    if mode == "strict":
        for c in cases:
            if not str(c.get("steps") or "").strip() or not str(c.get("expected_result") or "").strip():
                raise RuntimeError(f"用例 id={c.get('id')} 存在空白字段，strict 模式禁止模板填充")
        return cases, filled_ids
    if mode == "warn":
        before = {(c.get("id"), str(c.get("steps")), str(c.get("expected_result"))) for c in cases}
        filled = _fill_case_blanks(cases)
        for c in filled:
            key = (c.get("id"), str(c.get("steps")), str(c.get("expected_result")))
            if key not in before:
                filled_ids.append(c.get("id"))
        return filled, filled_ids
    return _fill_case_blanks(cases), filled_ids


async def generate_test_cases_batch(
    *,
    strategy: TestStrategyV1,
    batch: dict[str, Any],
    global_summary: str,
    historical_context: str,
    routed_skill_id: str | None,
    role_cfg: dict[str, Any],
) -> list[dict[str, Any]]:
    """单 module/sub-batch 生成。"""
    module_name = batch.get("module") or "模块"
    tps = batch.get("test_points") or []
    batch_strategy = {
        "version": strategy.version,
        "module": module_name,
        "risk_level": batch.get("risk_level"),
        "test_points": [
            {
                "id": tp.id,
                "title": tp.title,
                "case_types_required": tp.case_types_required,
                "min_cases": tp.min_cases,
                "priority_hint": tp.priority_hint,
            }
            for tp in tps
        ],
        "global_requirements": strategy.global_requirements.__dict__,
        "context_summary": global_summary[:2000],
    }
    design_text = json.dumps(batch_strategy, ensure_ascii=False, indent=2)
    per_tp = int(getattr(settings, "GENERATION_TOKENS_PER_TEST_POINT", 800))
    token_extra = per_tp * max(1, len(tps))

    br = build_generation_messages(
        design_result=design_text,
        historical_context=historical_context,
        skill_id=routed_skill_id,
        extra_business_prompt=role_cfg.get("extra_prompt") or role_cfg.get("prompt"),
    )
    raw = await _call_generation_llm(br.messages, role_cfg, max_tokens_extra=token_extra)
    cases = await _parse_cases_from_llm(raw, role_cfg)
    for c in cases:
        if not str(c.get("module") or "").strip():
            c["module"] = module_name
    return cases


async def supplement_cases_for_gaps(
    *,
    strategy: TestStrategyV1,
    cases: list[dict[str, Any]],
    gaps: dict[str, Any],
    analysis_or_design: str,
    role_cfg: dict[str, Any],
) -> list[dict[str, Any]]:
    """基于缺口定向补全。"""
    missing_scenarios: list[dict[str, Any]] = []
    for item in gaps.get("uncovered_test_points") or []:
        missing_scenarios.append({
            "module": item.get("module"),
            "test_point_id": item.get("test_point_id"),
            "title": item.get("title"),
            "reason": "uncovered_test_point",
        })
    for ct in gaps.get("missing_case_types") or []:
        missing_scenarios.append({"case_type": ct, "reason": "missing_case_type"})

    if not missing_scenarios:
        return []

    next_id = max((int(c.get("id", 0) or 0) for c in cases), default=0) + 1
    br = build_supplement_messages(
        analysis=analysis_or_design,
        existing_cases=cases,
        missing_scenarios=missing_scenarios,
        next_id=next_id,
        skill_id=role_cfg.get("skill_id"),
        extra_business_prompt=role_cfg.get("extra_prompt"),
    )
    raw = await _call_generation_llm(br.messages, role_cfg)
    try:
        return _parse_cases_payload(raw)
    except Exception as exc:
        logger.warning("缺口补全解析失败: {}", exc)
        return []


def build_quality_audit_payload(
    audit: quality_gate.CasesAudit,
    cases: list[dict[str, Any]],
    *,
    expected_modules: list[str] | None = None,
    filled_by_template: list[Any] | None = None,
    blank_ratio: float | None = None,
    pre_score: int | None = None,
    post_score: int | None = None,
) -> dict[str, Any]:
    """统一 quality_audit 结构。"""
    mod_cov = quality_gate.module_coverage_from_cases(cases, expected_modules=expected_modules)
    payload = quality_gate.audit_to_payload(
        audit,
        module_coverage=mod_cov,
        filled_by_template=filled_by_template,
        blank_ratio=blank_ratio,
        pre_supplement_score=pre_score,
        post_supplement_score=post_score,
    )
    if filled_by_template and str(getattr(settings, "GENERATION_FILL_MODE", "legacy")).lower() == "warn":
        payload["overall_score"] = min(int(payload.get("overall_score") or 0), 75)
    return payload


async def run_case_generation(
    design_result: str,
    *,
    historical_context: str = "",
    routing: dict[str, Any] | None = None,
    on_progress: ProgressCallback = None,
) -> GenerationResult:
    """统一用例生成入口（legacy / batched）。"""
    role_cfg = (await _load_role_config())["generation"]
    strategy_v1, design_raw = try_parse_strategy(design_result)
    result = GenerationResult(
        design_structured=strategy_v1.to_dict() if strategy_v1 else None,
        strategy_version=strategy_v1.version if strategy_v1 else None,
    )

    # generation skill 解析优先级：用户在 SkillsCenter 显式配置 > 智能路由 routing > 角色配置兜底
    # 此前 routing 凌驾于用户配置之上，会导致用户在角色配置里改 skill_id 时被 default 路由覆盖
    user_skill_id = (role_cfg.get("configured_skill_id") or "").strip()
    routing_skill_id = ((routing or {}).get("generation") or "").strip()
    role_skill_enabled = bool(role_cfg.get("skill_enabled", True))
    if user_skill_id and role_skill_enabled:
        routed_skill_id = user_skill_id
        skill_source = "user_config"
    elif routing_skill_id:
        routed_skill_id = routing_skill_id
        skill_source = "routing"
    else:
        routed_skill_id = (role_cfg.get("skill_id") or "").strip() or None
        skill_source = "fallback"
    logger.info(
        "[skill] generation resolve skill={} source={} routing_hit={} user_cfg={}",
        routed_skill_id, skill_source, routing_skill_id or "-", user_skill_id or "-",
    )

    if not _structured_enabled() or strategy_v1 is None:
        result.generation_mode = "legacy"
        from app.ai import ai as ai_module
        cases = await ai_module._generate_test_cases_legacy(
            design_raw,
            historical_context,
            routed_skill_id=routed_skill_id,
            routing=routing,
        )
        result.cases = cases
        audit = quality_gate.score_cases(cases)
        filled_ids: list[Any] = []
        try:
            result.cases, filled_ids = _safe_fill_blanks(result.cases)
        except RuntimeError:
            pass
        result.filled_by_template = filled_ids
        result.quality_audit = build_quality_audit_payload(
            audit, result.cases, filled_by_template=filled_ids,
        )
        return result

    result.generation_mode = "batched"
    result.expected_min_cases = compute_expected_min_cases(strategy_v1)
    batches = split_strategy_batches(
        strategy_v1,
        max_test_points_per_batch=int(getattr(settings, "GENERATION_MAX_TEST_POINTS_PER_BATCH", 15)),
        max_batches=int(getattr(settings, "GENERATION_MAX_BATCHES", 20)),
    )
    concurrency = max(1, int(getattr(settings, "GENERATION_BATCH_CONCURRENCY", 3)))
    sem = asyncio.Semaphore(concurrency)
    global_summary = design_raw[:4000]
    all_batch_cases: list[list[dict[str, Any]]] = []
    batch_stats: list[dict[str, Any]] = []

    async def _run_one(idx: int, batch: dict[str, Any]) -> None:
        async with sem:
            t0 = time.monotonic()
            err: str | None = None
            cases_batch: list[dict[str, Any]] = []
            for attempt in range(2):
                try:
                    hist = historical_context
                    if batch.get("module"):
                        try:
                            from app.rag.knowledge_base import retrieve_kb_context
                            hist = retrieve_kb_context(
                                "generation_batch",
                                f"{batch['module']} " + " ".join(tp.title for tp in batch.get("test_points") or []),
                                module_filter=str(batch["module"]),
                            ) or historical_context
                        except Exception:
                            hist = historical_context
                    cases_batch = await generate_test_cases_batch(
                        strategy=strategy_v1,
                        batch=batch,
                        global_summary=global_summary,
                        historical_context=hist,
                        routed_skill_id=routed_skill_id,
                        role_cfg=role_cfg,
                    )
                    break
                except Exception as exc:
                    err = str(exc)
                    if attempt == 0:
                        logger.warning("batch {} 失败，重试: {}", idx, exc)
                    else:
                        logger.error("batch {} 最终失败: {}", idx, exc)
            duration_ms = int((time.monotonic() - t0) * 1000)
            batch_stats.append({
                "batch_index": idx,
                "batch_total": len(batches),
                "module": batch.get("module"),
                "cases": len(cases_batch),
                "duration_ms": duration_ms,
                "error": err,
            })
            if cases_batch:
                all_batch_cases.append(cases_batch)
            if on_progress:
                maybe = on_progress({
                    "batch_index": idx,
                    "batch_total": len(batches),
                    "module_name": batch.get("module"),
                })
                if asyncio.iscoroutine(maybe):
                    await maybe

    await asyncio.gather(*[_run_one(i + 1, b) for i, b in enumerate(batches)])

    merged = merge_and_dedupe_cases(all_batch_cases) if all_batch_cases else []
    merged = normalize_merged_cases(merged, canonical_modules=strategy_module_names(strategy_v1))

    gaps = find_coverage_gaps(strategy_v1, merged)
    result.coverage_matrix = gaps.get("coverage_matrix")
    result.batch_stats = batch_stats

    pre_audit = quality_gate.score_cases(merged)
    result.pre_supplement_score = pre_audit.overall_score

    if bool(getattr(settings, "COVERAGE_SUPPLEMENT_ENABLED", True)):
        supplement_rounds = int(getattr(settings, "COVERAGE_REFINE_ROUNDS", 1))
        for _ in range(supplement_rounds):
            gaps = find_coverage_gaps(strategy_v1, merged)
            if not gaps.get("uncovered_test_points") and not gaps.get("missing_case_types"):
                break
            extra = await supplement_cases_for_gaps(
                strategy=strategy_v1,
                cases=merged,
                gaps=gaps,
                analysis_or_design=design_raw,
                role_cfg=role_cfg,
            )
            if extra:
                merged.extend(extra)
                merged = normalize_merged_cases(merged, canonical_modules=strategy_module_names(strategy_v1))

    if result.expected_min_cases and len(merged) < int(result.expected_min_cases * 0.8):
        gaps = find_coverage_gaps(strategy_v1, merged)
        extra = await supplement_cases_for_gaps(
            strategy=strategy_v1,
            cases=merged,
            gaps=gaps,
            analysis_or_design=design_raw,
            role_cfg=role_cfg,
        )
        if extra:
            merged.extend(extra)
            merged = normalize_merged_cases(merged, canonical_modules=strategy_module_names(strategy_v1))

    try:
        merged, filled_ids = _safe_fill_blanks(merged)
        result.filled_by_template = filled_ids
    except RuntimeError as exc:
        logger.error("strict fill 失败: {}", exc)
        raise

    from app.ai import ai as ai_module
    merged = await ai_module._apply_quality_gate(merged, design_result=design_raw, role_cfg=role_cfg)

    if bool(getattr(settings, "QUALITY_GATE_TYPE_SUPPLEMENT_ENABLED", True)):
        audit_mid = quality_gate.score_cases(merged)
        if audit_mid.missing_types:
            gaps = {"missing_case_types": audit_mid.missing_types, "uncovered_test_points": []}
            extra = await supplement_cases_for_gaps(
                strategy=strategy_v1,
                cases=merged,
                gaps=gaps,
                analysis_or_design=design_raw,
                role_cfg=role_cfg,
            )
            if extra:
                merged.extend(extra)
                merged = normalize_merged_cases(merged, canonical_modules=strategy_module_names(strategy_v1))
                merged = await ai_module._apply_quality_gate(merged, design_result=design_raw, role_cfg=role_cfg)

    post_audit = quality_gate.score_cases(merged)
    result.post_supplement_score = post_audit.overall_score
    result.cases = merged
    result.quality_audit = build_quality_audit_payload(
        post_audit,
        merged,
        expected_modules=strategy_module_names(strategy_v1),
        filled_by_template=result.filled_by_template,
        pre_score=result.pre_supplement_score,
        post_score=result.post_supplement_score,
    )
    result.coverage_matrix = build_coverage_matrix(strategy_v1, merged)
    return result


def should_skip_full_review(quality_audit: dict[str, Any], coverage_matrix: dict[str, Any] | None) -> str:
    """返回 review 模式: skip | light | full。"""
    if not bool(getattr(settings, "REVIEW_GATING_ENABLED", True)):
        return "full"
    score = int(quality_audit.get("overall_score") or 0)
    threshold = int(getattr(settings, "REVIEW_SKIP_THRESHOLD", 85))
    uncovered = (coverage_matrix or {}).get("uncovered") or []
    if score >= threshold and not uncovered:
        return "skip"
    if score >= 70:
        return "light"
    return "full"
