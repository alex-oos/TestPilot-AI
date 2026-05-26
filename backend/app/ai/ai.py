"""核心 AI 调用：需求分析 / 测试策略 / 用例生成 / 用例评审 / 评审补全。

prompt 拼装策略（按优先级）：
1. SkillPromptBuilder（默认开启，USE_QA_SKILLS=true）
2. 若 skill 加载失败：仅用 Output Contract + 业务自定义
3. 若 contract 也禁用 / 失败：回退到旧硬编码 prompts.py（QA_SKILL_LEGACY_FALLBACK_ENABLED=true）
"""

import json
from typing import Any, Dict, List

from loguru import logger

from app.ai.llm import get_last_call_meta, get_last_usage, llm_client
from app.ai.parsers import (
    _fill_case_blanks,
    _needs_case_repair,
    _parse_cases_payload,
    _parse_review_payload,
)
from app.ai.prompts import (
    DEFAULT_ANALYSIS_PROMPT,
    DEFAULT_GENERATION_PROMPT,
    DEFAULT_REVIEW_PROMPT,
    DEFAULT_SUPPLEMENT_PROMPT,
)
from app.ai.role_config import _load_role_config, _raise_if_llm_error
from app.ai.skills import (
    audit as skill_audit,
    build_analysis_messages,
    build_generation_messages,
    build_review_messages,
    build_strategy_messages,
    build_supplement_messages,
)
from app.ai.context_compressor import compress_text_for_llm
from app.ai.generation_orchestrator import GenerationResult, should_skip_full_review
from app.ai.strategy_schema import try_parse_strategy
from app.ai.skills import ab as skill_ab
from app.ai.skills import discover as skill_discover
from app.ai.skills.loader import get_skill_loader
from app.ai import quality_gate
from app.core.config import QA_SKILL_DISCOVER_ENABLED, settings


GENERATION_MIN_TOKENS = 16384
REVIEW_MIN_TOKENS = 8192


# 当前 task_id 的轻量 thread-local 上下文，用于在 ai 模块给 audit 自动带上 task_id
import contextvars
_current_task_ctx: contextvars.ContextVar[str | None] = contextvars.ContextVar("ai_task_id", default=None)


def set_current_task_id(task_id: str | None) -> None:
    _current_task_ctx.set(task_id)


def _current_task_id() -> str | None:
    return _current_task_ctx.get()


def _use_skills() -> bool:
    return bool(getattr(settings, "USE_QA_SKILLS", True))


def _role_use_skills(role_cfg: Dict[str, Any]) -> bool:
    """全局与角色级 Skill 开关均开启时才走 Skill builder。"""
    if not _use_skills():
        return False
    if not role_cfg.get("qa_skills_enabled", True):
        return False
    return bool(role_cfg.get("skill_enabled", True))


def _legacy_fallback_enabled() -> bool:
    return bool(getattr(settings, "QA_SKILL_LEGACY_FALLBACK_ENABLED", True))


def _bumped_max_tokens(role_cfg: Dict[str, Any], minimum: int) -> int:
    raw = role_cfg.get("max_tokens")
    try:
        current = int(raw) if raw is not None else 0
    except Exception:
        current = 0
    return max(current, minimum)


def _audit(role: str, meta: dict, *, extra_prompt_present: bool = False, extra: dict | None = None) -> None:
    try:
        skill_audit.from_meta(
            role=role,
            meta=meta or {},
            task_id=_current_task_id(),
            extra_prompt_present=extra_prompt_present,
            extra=extra or {},
        )
    except Exception as exc:  # noqa
        logger.warning("[skill] audit 失败: {}", exc)


def _backfill_actual_tokens(role: str) -> None:
    """LLM 调用后调用：把真实 usage、成本、cache/retries/error_code 写回最近一条审计记录。"""
    try:
        usage = get_last_usage()
        meta = get_last_call_meta() or {}
        if not usage and not meta:
            return
        skill_audit.update_actual_tokens(
            {"role": role, "task_id": _current_task_id()},
            usage or {},
            meta=meta,
        )
    except Exception as exc:  # noqa
        logger.debug("[skill] 回填 actual_tokens 失败: {}", exc)


# ---------------- quality gate ----------------

async def _apply_quality_gate(
    cases: List[Dict[str, Any]],
    *,
    design_result: str,
    role_cfg: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """生成阶段质量门禁：打分 + 审计 + 低分用例 LLM 自动细化重生成。"""
    if not cases:
        return cases
    audit = quality_gate.score_cases(cases)
    threshold = int(getattr(settings, "QUALITY_GATE_LOW_THRESHOLD", 60))
    low_ids = quality_gate.find_low_quality_ids(audit, threshold=threshold)

    # 审计写一条
    try:
        skill_audit.from_meta(
            role="quality_gate",
            meta={
                "skill_id": "quality_gate", "version": "1.0.0", "lang": "zh",
                "content_hash": "", "overlays_applied": [], "used_fewshot": False,
                "detected_lang": "", "prompt_tokens_est": 0, "over_budget": False,
            },
            task_id=_current_task_id(),
            extra={
                "overall_score": audit.overall_score,
                "average_case_score": audit.average_case_score,
                "sub_scores": audit.sub_scores,
                "low_count": len(low_ids),
                "missing_types": audit.missing_types,
                "weak_areas": audit.weak_areas,
                "threshold": threshold,
            },
        )
    except Exception as exc:  # noqa
        logger.debug("[quality-gate] 审计写入失败: {}", exc)

    logger.info(
        "[quality-gate] total={} overall={} avg={:.1f} low={} weak={} missing={}",
        audit.total, audit.overall_score, audit.average_case_score,
        len(low_ids), audit.weak_areas, audit.missing_types,
    )

    if not bool(getattr(settings, "QUALITY_GATE_REFINE_ENABLED", True)):
        return cases
    if not low_ids:
        return cases

    refine_max = int(getattr(settings, "QUALITY_GATE_REFINE_MAX", 30))
    target_ids = low_ids[:refine_max]
    targets = [c for c in cases if c.get("id") in target_ids]
    target_issues = {cs.case_id: cs.issues for cs in audit.cases if cs.case_id in target_ids}
    if not targets:
        return cases

    refine_user = (
        "下列测试用例被质量门禁判定为不合格，需要你**逐条**重写为高质量版本。\n"
        "重写时严格遵守输出契约：title ≥12 字符并以'验证'开头；steps ≥3 步、≥80 字符且必须采用 [操作]/[数据]/[校验] 三段式；"
        "expected_result ≥40 字符且包含可观测断言；test_data 必须给出字段=值；case_type 必须从 9 类中选；priority 合理分布。\n\n"
        f"【测试策略上下文】\n{design_result[:3000]}\n\n"
        f"【需要重写的用例（共 {len(targets)} 条）】\n{json.dumps(targets, ensure_ascii=False, indent=2)}\n\n"
        f"【每条用例的具体扣分原因】\n{json.dumps(target_issues, ensure_ascii=False, indent=2)}\n\n"
        "请直接返回 JSON 对象 {\"cases\": [...]}，cases 数组中**每条**都必须保留与原用例相同的 id 字段，"
        "其它字段按要求改写。除 JSON 外不要任何文字。"
    )
    refine_messages = [
        {"role": "system", "content": (
            "你是资深 QA 用例重写专家。任务：把不合格的用例改写为高质量版本，"
            "保留 id 不变，按字段约束逐条改写。只返回 JSON 对象。"
        )},
        {"role": "user", "content": refine_user},
    ]
    try:
        refined_raw = await llm_client.chat(
            messages=refine_messages,
            temperature=float(role_cfg.get("temperature", 0.1)),
            response_format={"type": "json_object"},
            model=role_cfg["model"],
            api_key=role_cfg.get("api_key"),
            base_url=role_cfg.get("base_url"),
            max_tokens=_bumped_max_tokens(role_cfg, GENERATION_MIN_TOKENS),
            top_p=role_cfg.get("top_p"),
        )
        if not isinstance(refined_raw, str) or refined_raw.lower().startswith("error:"):
            logger.warning("[quality-gate] 细化重写失败，跳过")
            return cases
        _backfill_actual_tokens("quality_gate")
        refined_cases = _parse_cases_payload(refined_raw)
    except Exception as exc:
        logger.warning("[quality-gate] 细化重写解析失败: {}", exc)
        return cases

    refined_cases = _fill_case_blanks(refined_cases)
    by_id = {c.get("id"): c for c in refined_cases if c.get("id") in target_ids}
    if not by_id:
        return cases

    # 用重写结果覆盖原用例
    merged: List[Dict[str, Any]] = []
    for c in cases:
        cid = c.get("id")
        if cid in by_id:
            new_case = dict(c)
            new_case.update(by_id[cid])
            new_case["id"] = cid
            merged.append(new_case)
        else:
            merged.append(c)
    logger.success(
        "[quality-gate] 已细化重写 {}/{} 条低分用例",
        len(by_id), len(target_ids),
    )
    return merged


# ---------------- discover routing ----------------

def _resolve_dynamic_routes(text_for_routing: str) -> dict:
    """根据需求/分析文本路由到具体 skill_id；返回 {generation, review, category, decided_by}。"""
    if not QA_SKILL_DISCOVER_ENABLED:
        return {}
    available = get_skill_loader().list_available()
    route = skill_discover.route_combined(text_for_routing or "", available_skills=available)
    route = skill_discover.filter_to_available(route, available)
    _audit("discover", {
        "skill_id": "discover-testing",
        "version": "1.0.0",
        "lang": "zh",
        "content_hash": "",
        "overlays_applied": [],
        "used_fewshot": False,
        "detected_lang": "",
        "prompt_tokens_est": 0,
        "over_budget": False,
    }, extra={"route": route})
    return route


def resolve_generation_routing(text_for_routing: str) -> dict:
    """对外暴露的智能路由结果。"""
    return _resolve_dynamic_routes(text_for_routing)


# ---------------- analyze_requirements ----------------

async def analyze_requirements(text_content: str) -> str:
    logger.info("AI Module: Requirement Analysis via LLM")
    role_cfg = (await _load_role_config())["analysis"]

    compressed, _compress_meta = compress_text_for_llm(
        text_content,
        max_chars=int(settings.LLM_MAX_SOURCE_CHARS or 32000),
        mode_hint="analysis",
    )
    kb_context = ""
    try:
        from app.rag.knowledge_base import retrieve_kb_context
        kb_context, _ = retrieve_kb_context("analysis", compressed)
    except Exception as exc:
        logger.debug("analysis KB 检索跳过: {}", exc)

    use_skills = _role_use_skills(role_cfg)
    skill_meta: dict = {}
    extra_present = bool((role_cfg.get("extra_prompt") or "").strip())

    user_body = compressed
    if kb_context:
        user_body = f"{kb_context}\n\n以下是项目文档内容：\n\n{compressed}"

    if use_skills:
        try:
            br = build_analysis_messages(
                text_content=user_body,
                skill_id=role_cfg.get("skill_id"),
                extra_business_prompt=role_cfg.get("extra_prompt") or role_cfg.get("prompt"),
                include_strategy_extension=False,
            )
            messages, skill_meta = br.messages, br.skill_meta
            _audit("analysis", skill_meta, extra_prompt_present=extra_present)
            logger.info(
                "[skill] analysis skill={} v{} fewshot={} tokens≈{}",
                skill_meta.get("skill_id"), skill_meta.get("version"),
                skill_meta.get("used_fewshot"), skill_meta.get("prompt_tokens_est"),
            )
        except Exception as exc:
            logger.warning("[skill] analysis 拼装失败 ({})，触发降级", exc)
            messages = None
    else:
        messages = None

    if messages is None:
        if _legacy_fallback_enabled():
            logger.info("[skill] analysis 使用 legacy prompt 降级")
            messages = [
                {"role": "system", "content": role_cfg["prompt"] or DEFAULT_ANALYSIS_PROMPT},
                {"role": "user", "content": user_body if kb_context else f"以下是项目文档内容：\n\n{compressed}"},
            ]
        else:
            raise RuntimeError("Skill 拼装失败且 legacy fallback 已禁用")

    analysis_result = await llm_client.chat(
        messages=messages,
        temperature=float(role_cfg.get("temperature", 0.3)),
        model=role_cfg["model"],
        api_key=role_cfg.get("api_key"),
        base_url=role_cfg.get("base_url"),
        max_tokens=role_cfg.get("max_tokens"),
        top_p=role_cfg.get("top_p"),
    )
    _raise_if_llm_error(analysis_result, "需求分析")
    _backfill_actual_tokens("analysis")
    logger.success("Requirement Analysis completed.")
    return analysis_result


async def design_test_strategy(
    analysis_result: str,
    *,
    routing: dict | None = None,
) -> str:
    logger.info("AI Module: Test Design via LLM")
    role_cfg = (await _load_role_config())["analysis"]
    strategy_skill = (
        getattr(settings, "QA_SKILL_STRATEGY", "") or role_cfg.get("skill_id")
    )

    compressed, _ = compress_text_for_llm(
        analysis_result,
        max_chars=int(settings.LLM_MAX_ANALYSIS_CHARS_FOR_STRATEGY or 12000),
        mode_hint="strategy",
    )
    kb_context = ""
    try:
        from app.rag.knowledge_base import retrieve_kb_context
        kb_context, _ = retrieve_kb_context("strategy", compressed)
    except Exception as exc:
        logger.debug("strategy KB 检索跳过: {}", exc)

    analysis_for_llm = compressed
    if kb_context:
        analysis_for_llm = f"{kb_context}\n\n需求解析结果如下：\n\n{compressed}"

    structured = bool(getattr(settings, "STRUCTURED_STRATEGY_ENABLED", False))
    extra_present = bool((role_cfg.get("extra_prompt") or "").strip())
    use_skills = _role_use_skills(role_cfg)
    messages = None

    if structured and use_skills:
        try:
            br = build_strategy_messages(
                analysis_result=analysis_for_llm,
                skill_id=strategy_skill,
                extra_business_prompt=role_cfg.get("extra_prompt") or role_cfg.get("prompt"),
                routing_category=(routing or {}).get("category"),
            )
            messages = br.messages
            _audit("strategy", br.skill_meta, extra_prompt_present=extra_present, extra={"structured": True})
        except Exception as exc:
            logger.warning("[skill] structured strategy 拼装失败 ({})，fallback legacy", exc)

    if messages is None and use_skills:
        try:
            br = build_analysis_messages(
                text_content=f"需求解析结果如下：\n\n{analysis_for_llm}",
                skill_id=role_cfg.get("skill_id"),
                extra_business_prompt=role_cfg.get("extra_prompt") or role_cfg.get("prompt"),
                include_strategy_extension=True,
            )
            messages = br.messages
            _audit("strategy", br.skill_meta, extra_prompt_present=extra_present)
        except Exception as exc:
            logger.warning("[skill] strategy 拼装失败 ({})，触发降级", exc)

    if messages is None:
        if _legacy_fallback_enabled():
            sys_p = (role_cfg["prompt"] or DEFAULT_ANALYSIS_PROMPT) + (
                "\n\n你还需要输出一份全面测试策略，覆盖正常流程、边界值、异常处理与等价类。"
            )
            messages = [
                {"role": "system", "content": sys_p},
                {"role": "user", "content": f"需求解析结果如下：\n\n{analysis_for_llm}"},
            ]
        else:
            raise RuntimeError("Skill 拼装失败且 legacy fallback 已禁用")

    design_result = await llm_client.chat(
        messages=messages,
        temperature=float(role_cfg.get("temperature", 0.4)),
        response_format={"type": "json_object"} if structured else None,
        model=role_cfg["model"],
        api_key=role_cfg.get("api_key"),
        base_url=role_cfg.get("base_url"),
        max_tokens=role_cfg.get("max_tokens"),
        top_p=role_cfg.get("top_p"),
    )
    _raise_if_llm_error(design_result, "测试策略")
    _backfill_actual_tokens("strategy")

    if structured:
        strategy_v1, _ = try_parse_strategy(design_result)
        if strategy_v1:
            design_result = strategy_v1.to_json()
        else:
            logger.warning("structured strategy 解析失败，保留原始 LLM 输出供 markdown 降级")

    logger.success("Test Design completed.")
    return design_result


# ---------------- generate / review / supplement ----------------

async def _generate_test_cases_legacy(
    design_result: str,
    historical_requirements_context: str = "",
    *,
    routed_skill_id: str | None = None,
    routing: dict | None = None,
) -> List[Dict[str, Any]]:
    """Legacy 单次全量生成路径。"""
    history_context = str(historical_requirements_context or "").strip()
    role_cfg = (await _load_role_config())["generation"]

    if not routed_skill_id:
        routed = routing or _resolve_dynamic_routes(design_result)
        # 与 generation_orchestrator 对齐：用户配置优先，routing 仅在用户未配置时兜底
        user_skill_id = (role_cfg.get("configured_skill_id") or "").strip()
        routing_skill_id = ((routed.get("generation") if routed else None) or "").strip()
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
            "[skill] generation(legacy) resolve skill={} source={} routing_hit={} user_cfg={}",
            routed_skill_id, skill_source, routing_skill_id or "-", user_skill_id or "-",
        )
    else:
        routed = routing or {}

    extra_present = bool((role_cfg.get("extra_prompt") or "").strip())
    use_skills = _role_use_skills(role_cfg)
    messages = None
    if use_skills:
        try:
            br = build_generation_messages(
                design_result=design_result,
                historical_context=history_context,
                skill_id=routed_skill_id,
                extra_business_prompt=role_cfg.get("extra_prompt") or role_cfg.get("prompt"),
            )
            messages = br.messages
            br.skill_meta["routing"] = routed
            _audit("generation", br.skill_meta, extra_prompt_present=extra_present, extra={"routing": routed})
        except Exception as exc:
            logger.warning("[skill] generation 拼装失败 ({})，触发降级", exc)

    if messages is None:
        if not _legacy_fallback_enabled():
            raise RuntimeError("Skill 拼装失败且 legacy fallback 已禁用")
        sys_p = (
            f"{role_cfg['prompt'] or DEFAULT_GENERATION_PROMPT}\n\n"
            "Output contract: always return valid json only, with key `cases` as an array. "
            "Each case must include non-empty fields: title, steps, expected_result. "
            "Do not leave steps or expected_result empty."
        )
        if history_context:
            messages = [
                {"role": "system", "content": sys_p},
                {"role": "user", "content": (
                    f"【历史相似用例（仅供风格参考，不得照抄）】\n{history_context}\n\n"
                    f"【当前需求测试策略】\n{design_result}\n\n"
                    "请直接返回合法 JSON 对象，包含 cases 数组字段。"
                )},
            ]
        else:
            messages = [
                {"role": "system", "content": sys_p},
                {"role": "user", "content": (
                    f"【当前需求测试策略】\n{design_result}\n\n"
                    "请直接返回合法 JSON 对象，包含 cases 数组字段。"
                )},
            ]

    cases_json_str = await llm_client.chat(
        messages=messages,
        temperature=float(role_cfg.get("temperature", 0.1)),
        response_format={"type": "json_object"},
        model=role_cfg["model"],
        api_key=role_cfg.get("api_key"),
        base_url=role_cfg.get("base_url"),
        max_tokens=_bumped_max_tokens(role_cfg, GENERATION_MIN_TOKENS),
        top_p=role_cfg.get("top_p"),
    )
    _raise_if_llm_error(cases_json_str, "测试用例生成")
    _backfill_actual_tokens("generation")

    try:
        cases = _parse_cases_payload(cases_json_str)
    except Exception as parse_error:
        logger.warning(f"Test cases JSON parse failed, trying repair once: {parse_error}")
        repair_messages = [
            {"role": "system", "content": (
                "你是一个 JSON 修复助手。请将用户提供的内容修复为合法 JSON 对象，且必须包含 cases 数组字段。"
                "如果用户内容是 JSON 对象，请提取其中测试用例列表字段（test_cases/cases/items/data）并放入 cases 字段。"
                "只返回 JSON 对象，不要任何解释。"
            )},
            {"role": "user", "content": cases_json_str},
        ]
        repaired = await llm_client.chat(
            messages=repair_messages,
            temperature=0,
            response_format={"type": "json_object"},
            model=role_cfg["model"],
            api_key=role_cfg.get("api_key"),
            base_url=role_cfg.get("base_url"),
            max_tokens=_bumped_max_tokens(role_cfg, GENERATION_MIN_TOKENS),
            top_p=role_cfg.get("top_p"),
        )
        _raise_if_llm_error(repaired, "测试用例修复")
        cases = _parse_cases_payload(repaired)

    if _needs_case_repair(cases):
        logger.warning("Generated cases have too many blank fields, trying one refinement pass.")
        repair_messages = [
            {"role": "system", "content": (
                "你是测试用例补全助手。请基于用户给出的策略与初稿用例，补全每条用例的 steps 与 expected_result。"
                "必须返回 JSON 对象，包含 cases 数组。"
                "cases 中每个元素都必须包含非空字段：id,module,title,precondition,steps,expected_result,priority。"
                "禁止返回空字符串。"
            )},
            {"role": "user", "content": (
                f"【测试策略】\n{design_result}\n\n"
                f"【初稿用例】\n{json.dumps(cases, ensure_ascii=False, indent=2)}"
            )},
        ]
        repaired_cases_raw = await llm_client.chat(
            messages=repair_messages,
            temperature=0.1,
            response_format={"type": "json_object"},
            model=role_cfg["model"],
            api_key=role_cfg.get("api_key"),
            base_url=role_cfg.get("base_url"),
            max_tokens=_bumped_max_tokens(role_cfg, GENERATION_MIN_TOKENS),
            top_p=role_cfg.get("top_p"),
        )
        _raise_if_llm_error(repaired_cases_raw, "测试用例补全")
        try:
            cases = _parse_cases_payload(repaired_cases_raw)
        except Exception as repair_parse_error:
            logger.warning("Refined cases parse failed, keep original: {}", repair_parse_error)

    fill_mode = str(getattr(settings, "GENERATION_FILL_MODE", "legacy") or "legacy").lower()
    if _needs_case_repair(cases):
        if fill_mode == "strict":
            raise RuntimeError("用例存在空白字段，strict 模式禁止模板填充")
        logger.warning("Cases still contain blanks after refinement, apply safe fallback text.")
        cases = _fill_case_blanks(cases)

    try:
        cases = await _apply_quality_gate(cases, design_result=design_result, role_cfg=role_cfg)
    except Exception as qg_exc:  # noqa
        logger.warning("[quality-gate] 异常，跳过细化: {}", qg_exc)

    return cases


async def run_test_case_generation(
    design_result: str,
    historical_requirements_context: str = "",
    *,
    routing: dict | None = None,
    on_progress=None,
) -> GenerationResult:
    """统一用例生成（含分批、覆盖、质量审计）。"""
    from app.ai.generation_orchestrator import run_case_generation
    return await run_case_generation(
        design_result,
        historical_context=historical_requirements_context,
        routing=routing,
        on_progress=on_progress,
    )


async def generate_test_cases(
    design_result: str,
    historical_requirements_context: str = "",
    *,
    routing: dict | None = None,
) -> List[Dict[str, Any]]:
    logger.info("AI Module: Generating Test Cases via LLM")
    if routing is None:
        routing = _resolve_dynamic_routes(design_result)
    result = await run_test_case_generation(
        design_result,
        historical_requirements_context,
        routing=routing,
    )
    cases = result.cases

    role_cfg = (await _load_role_config())["generation"]
    use_skills = _role_use_skills(role_cfg)
    if (
        bool(getattr(settings, "QA_SKILL_AB_ENABLED", False))
        and use_skills
        and getattr(settings, "QA_SKILL_AB_VARIANT_GENERATION", "")
    ):
        try:
            variant_skill = settings.QA_SKILL_AB_VARIANT_GENERATION
            br_v = build_generation_messages(
                design_result=design_result,
                historical_context=historical_requirements_context,
                skill_id=variant_skill,
                extra_business_prompt=role_cfg.get("extra_prompt") or role_cfg.get("prompt"),
            )
            variant_raw = await llm_client.chat(
                messages=br_v.messages,
                temperature=float(role_cfg.get("temperature", 0.1)),
                response_format={"type": "json_object"},
                model=role_cfg["model"],
                api_key=role_cfg.get("api_key"),
                base_url=role_cfg.get("base_url"),
                max_tokens=_bumped_max_tokens(role_cfg, GENERATION_MIN_TOKENS),
                top_p=role_cfg.get("top_p"),
            )
            if isinstance(variant_raw, str) and not variant_raw.lower().startswith("error:"):
                variant_cases = _parse_cases_payload(variant_raw)
                metrics = skill_ab.compare(cases, variant_cases)
                _audit("generation", br_v.skill_meta, extra={
                    "ab_variant": variant_skill,
                    "ab_metrics": metrics,
                    "ab_role": "variant",
                })
        except Exception as ab_exc:  # noqa
            logger.warning("[ab] variant 跑失败，忽略: {}", ab_exc)

    logger.success(f"Generated {len(cases)} test cases.")
    return cases


async def review_test_cases(cases: List[Dict[str, Any]], analysis: str) -> Dict[str, Any]:
    logger.info("AI Module: Reviewing test cases via LLM")
    role_cfg = (await _load_role_config())["review"]

    extra_present = bool((role_cfg.get("extra_prompt") or "").strip())
    use_skills = _role_use_skills(role_cfg)
    messages = None
    if use_skills:
        try:
            br = build_review_messages(
                cases=cases,
                analysis=analysis,
                skill_id=role_cfg.get("skill_id"),
                extra_business_prompt=role_cfg.get("extra_prompt") or role_cfg.get("prompt"),
            )
            messages = br.messages
            _audit("review", br.skill_meta, extra_prompt_present=extra_present)
            logger.info(
                "[skill] review skill={} v{} fewshot={} tokens≈{}",
                br.skill_meta.get("skill_id"), br.skill_meta.get("version"),
                br.skill_meta.get("used_fewshot"), br.skill_meta.get("prompt_tokens_est"),
            )
        except Exception as exc:
            logger.warning("[skill] review 拼装失败 ({})，触发降级", exc)

    if messages is None:
        if not _legacy_fallback_enabled():
            raise RuntimeError("Skill 拼装失败且 legacy fallback 已禁用")
        cases_summary = json.dumps(cases, ensure_ascii=False, indent=2)
        sys_p = f"{role_cfg['prompt'] or DEFAULT_REVIEW_PROMPT}\n\nOutput contract: always return valid json only."
        messages = [
            {"role": "system", "content": sys_p},
            {"role": "user", "content": (
                f"【需求分析结果】：\n{analysis}\n\n【已生成的测试用例（共{len(cases)}条）】：\n{cases_summary}"
            )},
        ]

    review_str = await llm_client.chat(
        messages=messages,
        temperature=float(role_cfg.get("temperature", 0.3)),
        response_format={"type": "json_object"},
        model=role_cfg["model"],
        api_key=role_cfg.get("api_key"),
        base_url=role_cfg.get("base_url"),
        max_tokens=_bumped_max_tokens(role_cfg, REVIEW_MIN_TOKENS),
        top_p=role_cfg.get("top_p"),
    )
    _raise_if_llm_error(review_str, "测试用例评审")
    _backfill_actual_tokens("review")

    try:
        review = _parse_review_payload(review_str)
    except Exception as parse_error:
        logger.warning(f"Review JSON parse failed, trying repair once: {parse_error}")
        repair_messages = [
            {"role": "system", "content": (
                "你是一个 JSON 修复助手。请将用户提供的评审内容修复为合法 JSON 对象。"
                "必须包含 issues、suggestions、missing_scenarios、quality_score、summary 字段。"
                "只返回 JSON 对象，不要任何解释。"
            )},
            {"role": "user", "content": review_str},
        ]
        repaired = await llm_client.chat(
            messages=repair_messages,
            temperature=0,
            response_format={"type": "json_object"},
            model=role_cfg["model"],
            api_key=role_cfg.get("api_key"),
            base_url=role_cfg.get("base_url"),
            max_tokens=_bumped_max_tokens(role_cfg, REVIEW_MIN_TOKENS),
            top_p=role_cfg.get("top_p"),
        )
        _raise_if_llm_error(repaired, "测试用例评审修复")
        try:
            review = _parse_review_payload(repaired)
        except Exception as repair_error:
            logger.error("Failed to parse review JSON after repair: {}", repair_error)
            raise RuntimeError("AI评审解析失败：模型未返回合法 JSON") from repair_error

    original_count = len(cases)
    final_cases = list(cases)
    supplemented: List[Dict[str, Any]] = []
    try:
        supplemented = await _supplement_cases_from_review(
            role_cfg=role_cfg, existing_cases=cases, analysis=analysis, review=review,
        )
    except Exception as supplement_error:
        logger.warning(f"补充用例失败，将仅保留原用例：{supplement_error}")
        supplemented = []

    if supplemented:
        final_cases.extend(supplemented)
        logger.info(
            f"评审完成：原用例 {original_count} 条，补充 {len(supplemented)} 条，合计 {len(final_cases)} 条。"
        )
    else:
        logger.info(f"评审完成：原用例 {original_count} 条，未发现需补充的场景。")

    review["reviewed_cases"] = final_cases
    review["original_case_count"] = original_count
    review["supplemented_case_count"] = len(supplemented)

    logger.success(f"Test case review completed. Quality score: {review.get('quality_score', 'N/A')}")
    return review


async def _supplement_cases_from_review(
    *,
    role_cfg: Dict[str, Any],
    existing_cases: List[Dict[str, Any]],
    analysis: str,
    review: Dict[str, Any],
) -> List[Dict[str, Any]]:
    missing = review.get("missing_scenarios") if isinstance(review, dict) else None
    if not isinstance(missing, list) or not missing:
        return []

    next_id = max((int(c.get("id", 0) or 0) for c in existing_cases), default=0) + 1
    next_id = max(next_id, 1001)

    use_skills = _role_use_skills(role_cfg)
    base_messages = None
    if use_skills:
        try:
            br = build_supplement_messages(
                analysis=analysis,
                existing_cases=existing_cases,
                missing_scenarios=missing,
                next_id=next_id,
                skill_id=role_cfg.get("skill_id"),
                extra_business_prompt=role_cfg.get("extra_prompt"),
            )
            base_messages = br.messages
            _audit("supplement", br.skill_meta,
                   extra_prompt_present=bool((role_cfg.get("extra_prompt") or "").strip()))
        except Exception as exc:
            logger.warning("[skill] supplement 拼装失败 ({})，触发降级", exc)

    if base_messages is None:
        if not _legacy_fallback_enabled():
            return []
        base_messages = [
            {"role": "system", "content": DEFAULT_SUPPLEMENT_PROMPT},
            {"role": "user", "content": (
                f"【需求分析】\n{analysis}\n\n"
                "【已有用例标题清单（避免重复）】\n"
                + "\n".join(f"- [{c.get('module','')}] {c.get('title','')}" for c in existing_cases)
                + "\n\n"
                f"【评审专家指出的缺失场景】\n{json.dumps(missing, ensure_ascii=False, indent=2)}\n\n"
                f"请从 id={next_id} 开始递增编号，**只输出新增用例**。"
            )},
        ]

    async def _call(extra_user_hint: str = "") -> str:
        msgs = list(base_messages)
        if extra_user_hint:
            msgs.append({"role": "user", "content": extra_user_hint})
        return await llm_client.chat(
            messages=msgs,
            temperature=0.3,
            response_format={"type": "json_object"},
            model=role_cfg["model"],
            api_key=role_cfg.get("api_key"),
            base_url=role_cfg.get("base_url"),
            max_tokens=_bumped_max_tokens(role_cfg, GENERATION_MIN_TOKENS),
            top_p=role_cfg.get("top_p"),
        )

    raw = await _call()
    _backfill_actual_tokens("supplement")
    if isinstance(raw, str) and raw.strip().lower().startswith("error:"):
        logger.warning(f"补充用例 LLM 调用失败，跳过: {raw}")
        return []
    try:
        parsed = _parse_cases_payload(raw)
        if parsed:
            return parsed
        raise ValueError("返回的 cases 数组为空")
    except Exception as exc:
        logger.warning(f"补充用例首次解析失败，重试一次: {exc}")
        retry_hint = (
            f"上一次响应未生成有效用例。请严格按要求，为每个 missing_scenario 至少生成一条用例，"
            f"必须返回非空 cases 数组（至少 {len(missing)} 条）。直接输出 JSON。"
        )
        try:
            retry_raw = await _call(retry_hint)
            if isinstance(retry_raw, str) and retry_raw.strip().lower().startswith("error:"):
                logger.warning(f"补充用例重试 LLM 失败: {retry_raw}")
                return []
            return _parse_cases_payload(retry_raw)
        except Exception as retry_exc:
            logger.warning(f"补充用例重试仍失败，跳过: {retry_exc}")
            return []


# ---------------- fix_cases_by_review ----------------

async def fix_cases_by_review(
    cases: List[Dict[str, Any]],
    review: Dict[str, Any],
    analysis: str,
    design: str = "",
) -> List[Dict[str, Any]]:
    """评审完成后，根据评审意见使用 generation skill 对不合格用例进行修复重写。

    Args:
        cases: 当前全量测试用例列表
        review: 评审结果（包含 issues / suggestions / quality_score）
        analysis: 需求分析文本
        design: 测试策略/设计文本（可选）

    Returns:
        修复后的全量用例列表（未被改动的用例原样保留）
    """
    issues: List[str] = review.get("issues") or [] if isinstance(review, dict) else []
    suggestions: List[str] = review.get("suggestions") or [] if isinstance(review, dict) else []
    quality_score: int = int(review.get("quality_score", 100)) if isinstance(review, dict) else 100

    if not issues and not suggestions:
        logger.info("[fix_cases] 评审未发现问题，无需修复")
        return cases

    logger.info(
        "[fix_cases] 开始修复：quality_score={}, issues={}, suggestions={}",
        quality_score, len(issues), len(suggestions),
    )

    role_cfg = (await _load_role_config())["generation"]
    issues_text = "\n".join(f"- {i}" for i in issues)
    suggestions_text = "\n".join(f"- {s}" for s in suggestions)

    fix_review_context = (
        f"【评审质量分】: {quality_score}/100\n\n"
        f"【评审发现的问题】:\n{issues_text}\n\n"
        f"【改进建议】:\n{suggestions_text}"
    )

    use_skills = _role_use_skills(role_cfg)
    messages = None
    skill_meta: dict = {}
    extra_prompt_present = True

    if use_skills:
        try:
            extra_business_prompt = (
                f"根据以下评审反馈，对有问题的用例进行修复和改写。"
                f"未被评审指出问题的用例原样保留，保持 id 不变。\n\n"
                f"{fix_review_context}\n\n"
                f"【当前全量用例】:\n{json.dumps(cases, ensure_ascii=False, indent=2)}"
            )
            br = build_generation_messages(
                design_text=design or analysis,
                history_context=fix_review_context,
                routing={},
                skill_id=role_cfg.get("skill_id"),
                extra_business_prompt=extra_business_prompt,
            )
            messages, skill_meta = br.messages, br.skill_meta
            _audit("generation", skill_meta, extra_prompt_present=extra_prompt_present,
                   extra={"phase": "auto_fix", "quality_score": quality_score})
            logger.info(
                "[skill] fix_cases skill={} v{} fewshot={} tokens≈{}",
                skill_meta.get("skill_id"), skill_meta.get("version"),
                skill_meta.get("used_fewshot"), skill_meta.get("prompt_tokens_est"),
            )
        except Exception as exc:
            logger.warning("[skill] fix_cases 拼装失败 ({})，使用内置 prompt", exc)

    if messages is None:
        fix_system = (
            "你是资深 QA 用例改写专家。根据评审意见，对有问题的测试用例进行修复改写。"
            "未被评审指出问题的用例原样保留，保持 id 不变。"
            "只返回 JSON 对象 {\"cases\": [...]}，包含全部用例（已修复的+未改动的），除 JSON 外不要任何文字。"
        )
        fix_user = (
            f"【需求分析背景】\n{analysis[:2000]}\n\n"
            f"{fix_review_context}\n\n"
            f"【当前全量测试用例（共 {len(cases)} 条）】:\n"
            f"{json.dumps(cases, ensure_ascii=False, indent=2)}\n\n"
            "请修复上述问题，返回包含全部用例的 JSON。"
        )
        messages = [
            {"role": "system", "content": fix_system},
            {"role": "user", "content": fix_user},
        ]

    fixed_raw = await llm_client.chat(
        messages=messages,
        temperature=float(role_cfg.get("temperature", 0.1)),
        response_format={"type": "json_object"},
        model=role_cfg["model"],
        api_key=role_cfg.get("api_key"),
        base_url=role_cfg.get("base_url"),
        max_tokens=_bumped_max_tokens(role_cfg, GENERATION_MIN_TOKENS),
        top_p=role_cfg.get("top_p"),
    )
    _raise_if_llm_error(fixed_raw, "评审后用例修复")
    _backfill_actual_tokens("generation")

    try:
        fixed_cases = _parse_cases_payload(fixed_raw)
    except Exception as exc:
        logger.warning("[fix_cases] 解析失败，保留原用例: {}", exc)
        return cases

    fixed_cases = _fill_case_blanks(fixed_cases)
    if not fixed_cases:
        logger.warning("[fix_cases] 修复结果为空，保留原用例")
        return cases

    # 按 id 合并：LLM 返回的修复版本覆盖原用例，原用例中未被返回的保留
    by_fixed_id = {c.get("id"): c for c in fixed_cases if c.get("id") is not None}
    result: List[Dict[str, Any]] = []
    for c in cases:
        cid = c.get("id")
        result.append(by_fixed_id.get(cid, c))

    # 若 LLM 补充了新用例（新 id），追加
    orig_ids = {c.get("id") for c in cases}
    for c in fixed_cases:
        if c.get("id") not in orig_ids:
            result.append(c)

    logger.success(
        "[fix_cases] 修复完成：原 {} 条 → 修复后 {} 条",
        len(cases), len(result),
    )
    return result
