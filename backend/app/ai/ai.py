import json
from loguru import logger
from typing import List, Dict, Any

from app.ai.llm import llm_client
from app.ai.parsers import (
    _parse_cases_payload,
    _parse_review_payload,
    _normalize_cases,
    _needs_case_repair,
    _fill_case_blanks,
)
from app.ai.prompts import DEFAULT_SUPPLEMENT_PROMPT
from app.ai.role_config import _load_role_config, _raise_if_llm_error


GENERATION_MIN_TOKENS = 16384
REVIEW_MIN_TOKENS = 8192


def _bumped_max_tokens(role_cfg: Dict[str, Any], minimum: int) -> int:
    """For long-form generation, ensure we don't truncate at small caps like 4096."""
    raw = role_cfg.get("max_tokens")
    try:
        current = int(raw) if raw is not None else 0
    except Exception:
        current = 0
    return max(current, minimum)


async def _supplement_cases_from_review(
    *,
    role_cfg: Dict[str, Any],
    existing_cases: List[Dict[str, Any]],
    analysis: str,
    review: Dict[str, Any],
) -> List[Dict[str, Any]]:
    """根据评审 missing_scenarios 自动补充新增用例（只补新增，不改原有）。"""
    missing = review.get("missing_scenarios") if isinstance(review, dict) else None
    if not isinstance(missing, list) or not missing:
        return []

    next_id = max((int(c.get("id", 0) or 0) for c in existing_cases), default=0) + 1
    next_id = max(next_id, 1001)

    messages = [
        {"role": "system", "content": DEFAULT_SUPPLEMENT_PROMPT},
        {
            "role": "user",
            "content": (
                f"【需求分析】\n{analysis}\n\n"
                f"【已有用例标题清单（避免重复）】\n"
                + "\n".join(f"- [{c.get('module','')}] {c.get('title','')}" for c in existing_cases)
                + "\n\n"
                f"【评审专家指出的缺失场景】\n{json.dumps(missing, ensure_ascii=False, indent=2)}\n\n"
                f"请从 id={next_id} 开始递增编号，**只输出新增用例**。"
            ),
        },
    ]
    async def _call(extra_user_hint: str = "") -> str:
        msgs = list(messages)
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


async def analyze_requirements(text_content: str) -> str:
    """AI Module - Requirement Analysis"""
    logger.info("AI Module: Requirement Analysis via LLM")

    role_cfg = (await _load_role_config())["analysis"]
    system_prompt = role_cfg["prompt"]
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"以下是项目文档内容：\n\n{text_content}"}
    ]

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
    logger.success("Requirement Analysis completed.")
    return analysis_result


async def design_test_strategy(analysis_result: str) -> str:
    """AI Module - Test Design"""
    logger.info("AI Module: Test Design via LLM")

    role_cfg = (await _load_role_config())["analysis"]
    system_prompt = role_cfg["prompt"] + "\n\n你还需要输出一份全面测试策略，覆盖正常流程、边界值、异常处理与等价类。"
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"需求解析结果如下：\n\n{analysis_result}"}
    ]

    design_result = await llm_client.chat(
        messages=messages,
        temperature=float(role_cfg.get("temperature", 0.4)),
        model=role_cfg["model"],
        api_key=role_cfg.get("api_key"),
        base_url=role_cfg.get("base_url"),
        max_tokens=role_cfg.get("max_tokens"),
        top_p=role_cfg.get("top_p"),
    )
    _raise_if_llm_error(design_result, "测试策略")
    logger.success("Test Design completed.")
    return design_result


async def generate_test_cases(design_result: str, historical_requirements_context: str = "") -> List[Dict[str, Any]]:
    """AI Module - Generating Test Cases"""
    logger.info("AI Module: Generating Test Cases via LLM")
    history_context = str(historical_requirements_context or "").strip()

    role_cfg = (await _load_role_config())["generation"]
    system_prompt = (
        f"{role_cfg['prompt']}\n\n"
        "Output contract: always return valid json only, with key `cases` as an array. "
        "Each case must include non-empty fields: title, steps, expected_result. "
        "Do not leave steps or expected_result empty."
    )
    if history_context:
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "【历史相似用例（仅供测试设计风格参考，不得照抄）】\n"
                    f"{history_context}\n\n"
                    "【当前需求测试策略】\n"
                    f"{design_result}\n\n"
                    "**严格要求**：\n"
                    "1. 必须**只针对**【当前需求测试策略】中描述的业务功能编写用例，禁止引入历史用例中出现的"
                    "但当前需求并不存在的业务术语（如其它项目的模块名、字段名、状态名等）。\n"
                    "2. 历史用例**仅用于参考测试用例的写法/颗粒度**，不要复制其业务内容到模块/标题/步骤。\n"
                    "3. module 字段必须来自【当前需求测试策略】里的真实业务模块，禁止出现"
                    "'【复用历史经验】'、'参考历史'等前缀。\n"
                    "请直接返回合法 json 对象，包含 cases 数组字段。每条用例必须有非空 steps 和 expected_result。"
                ),
            },
        ]
    else:
        messages = [
            {"role": "system", "content": system_prompt},
            {
                "role": "user",
                "content": (
                    "【当前需求测试策略】\n"
                    f"{design_result}\n\n"
                    "当前没有历史相似需求可参考，请基于当前策略完整生成测试用例，覆盖正常、异常与边界场景。"
                    "请直接返回合法json对象，包含cases数组字段。每条用例必须有非空 steps 和 expected_result。"
                ),
            },
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

    try:
        cases = _parse_cases_payload(cases_json_str)
    except Exception as parse_error:
        logger.warning(f"Test cases JSON parse failed, trying repair once: {parse_error}")
        repair_messages = [
            {
                "role": "system",
                "content": (
                    "你是一个 JSON 修复助手。请将用户提供的内容修复为合法 JSON 对象，且必须包含 cases 数组字段。"
                    "如果用户内容是 JSON 对象，请提取其中测试用例列表字段（test_cases/cases/items/data）并放入 cases 字段。"
                    "只返回 JSON 对象，不要任何解释。"
                ),
            },
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
        try:
            cases = _parse_cases_payload(repaired)
        except Exception as repair_error:
            logger.error(
                "Failed to parse test cases JSON after repair: {} | raw={} | repaired={}",
                repair_error,
                cases_json_str,
                repaired,
            )
            raise RuntimeError("测试用例生成结果解析失败：模型未返回合法 JSON") from repair_error

    if _needs_case_repair(cases):
        logger.warning("Generated cases have too many blank fields, trying one refinement pass.")
        repair_messages = [
            {
                "role": "system",
                "content": (
                    "你是测试用例补全助手。请基于用户给出的策略与初稿用例，补全每条用例的 steps 与 expected_result。"
                    "必须返回 JSON 对象，包含 cases 数组。"
                    "cases 中每个元素都必须包含非空字段：id,module,title,precondition,steps,expected_result,priority。"
                    "禁止返回空字符串。"
                ),
            },
            {
                "role": "user",
                "content": (
                    f"【测试策略】\n{design_result}\n\n"
                    f"【初稿用例】\n{json.dumps(cases, ensure_ascii=False, indent=2)}"
                ),
            },
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

    if _needs_case_repair(cases):
        logger.warning("Cases still contain blanks after refinement, apply safe fallback text.")
        cases = _fill_case_blanks(cases)

    logger.success(f"Generated {len(cases)} test cases.")
    return cases


async def review_test_cases(cases: List[Dict[str, Any]], analysis: str) -> Dict[str, Any]:
    """AI Module - Review and optimize generated test cases"""
    logger.info("AI Module: Reviewing test cases via LLM")

    cases_summary = json.dumps(cases, ensure_ascii=False, indent=2)

    role_cfg = (await _load_role_config())["review"]
    system_prompt = (
        f"{role_cfg['prompt']}\n\n"
        "Output contract: always return valid json only."
    )

    user_content = f"""【需求分析结果】：
{analysis}

【已生成的测试用例（共{len(cases)}条）】：
{cases_summary}"""

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
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

    try:
        review = _parse_review_payload(review_str)
    except Exception as parse_error:
        logger.warning(f"Review JSON parse failed, trying repair once: {parse_error}")
        repair_messages = [
            {
                "role": "system",
                "content": (
                    "你是一个 JSON 修复助手。请将用户提供的评审内容修复为合法 JSON 对象。"
                    "必须包含 issues、suggestions、missing_scenarios、quality_score、summary 字段。"
                    "只返回 JSON 对象，不要任何解释。"
                ),
            },
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
            logger.error(
                "Failed to parse review JSON after repair: {} | raw={} | repaired={}",
                repair_error,
                review_str,
                repaired,
            )
            raise RuntimeError("AI评审解析失败：模型未返回合法 JSON") from repair_error

    # === 关键修复 ===
    # 1. 抛弃 LLM 返回的 reviewed_cases —— 它经常被 max_tokens 截断，导致用例丢失。
    # 2. 始终保留原始用例，并根据 missing_scenarios 增量补充新用例。
    original_count = len(cases)
    final_cases = list(cases)
    supplemented: List[Dict[str, Any]] = []
    try:
        supplemented = await _supplement_cases_from_review(
            role_cfg=role_cfg,
            existing_cases=cases,
            analysis=analysis,
            review=review,
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
