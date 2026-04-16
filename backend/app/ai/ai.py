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
from app.ai.role_config import _load_role_config, _raise_if_llm_error


async def _revise_cases_from_review(
    *,
    role_cfg: Dict[str, Any],
    original_cases: List[Dict[str, Any]],
    analysis: str,
    review: Dict[str, Any],
) -> List[Dict[str, Any]]:
    revise_prompt = (
        "你是测试用例修正助手。请依据需求分析与评审结果，输出修正后的完整测试用例列表。"
        "必须只返回 JSON 数组，不要 markdown，不要解释。字段严格为："
        "id,module,title,precondition,steps,expected_result,priority。"
    )
    revise_messages = [
        {"role": "system", "content": revise_prompt},
        {
            "role": "user",
            "content": (
                f"【需求分析】\n{analysis}\n\n"
                f"【原始用例】\n{json.dumps(original_cases, ensure_ascii=False, indent=2)}\n\n"
                f"【评审结果】\n{json.dumps(review, ensure_ascii=False, indent=2)}\n"
            ),
        },
    ]
    revised_raw = await llm_client.chat(
        messages=revise_messages,
        temperature=0,
        model=role_cfg["model"],
        api_key=role_cfg.get("api_key"),
        base_url=role_cfg.get("base_url"),
        max_tokens=role_cfg.get("max_tokens"),
        top_p=role_cfg.get("top_p"),
    )
    _raise_if_llm_error(revised_raw, "测试用例评审后修正")
    return _parse_cases_payload(revised_raw)


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
                    "【历史相似需求（优先参考）】\n"
                    f"{history_context}\n\n"
                    "【当前需求测试策略】\n"
                    f"{design_result}\n\n"
                    "要求：生成的测试用例需体现对历史相似需求的复用与补充。"
                    "请直接返回合法json对象，包含cases数组字段。每条用例必须有非空 steps 和 expected_result。"
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
        max_tokens=role_cfg.get("max_tokens"),
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
            max_tokens=role_cfg.get("max_tokens"),
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
            max_tokens=role_cfg.get("max_tokens"),
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
        max_tokens=role_cfg.get("max_tokens"),
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
            max_tokens=role_cfg.get("max_tokens"),
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

    if not isinstance(review.get("reviewed_cases"), list) or not review.get("reviewed_cases"):
        try:
            review["reviewed_cases"] = await _revise_cases_from_review(
                role_cfg=role_cfg,
                original_cases=cases,
                analysis=analysis,
                review=review,
            )
        except Exception as revise_error:
            logger.warning(f"Review cases auto-revise failed, fallback to original cases: {revise_error}")
            review["reviewed_cases"] = cases

    logger.success(f"Test case review completed. Quality score: {review.get('quality_score', 'N/A')}")
    return review
