import json
import re
import time
from loguru import logger
from typing import List, Dict, Any
from app.ai.llm import llm_client
from app.modules.persistence import config_center_store

DEFAULT_ANALYSIS_PROMPT = """
你是一个资深的软件需求分析师。
请阅读用户上传的项目文档内容，提取出关键的核心功能点、业务流程以及任何限制条件。
要求：
1. 结果以清晰的 Markdown 格式输出。
2. 将需求拆分为多个“模块”或“功能点”。
3. 突出显示任何隐藏的逻辑或者边缘情况。
"""

DEFAULT_GENERATION_PROMPT = """
你是一个资深的软件测试工程师。
基于前述分配的【测试策略】，请编写详细的系统级测试用例。
【关键要求】：
你必须直接返回一个合法的 JSON 对象，不要包裹在 markdown 代码块（如 ```json）中，不要有任何前言或后语。 
JSON 必须严格符合以下结构：
{
  "cases": [
    {
      "id": 101, // 整数，测试用例递增ID
      "module": "测试模块名称", // 字符串
      "title": "测试用例标题", // 字符串
      "precondition": "前置条件说明", // 字符串，如果没有填无
      "steps": "步骤1... \\n步骤2...", // 字符串，包含换行符的详细步骤
      "expected_result": "预期结果", // 字符串
      "priority": "高" // 字符串：高、中、低
    }
  ]
}
title：验证 xx 功能
1. 直接开始生成测试用例，不要添加任何概述、介绍、文档说明或总结
2. 第一个输出必须是测试用例，格式：## TC-001: 标题
3. 每个测试用例必须以 ## TC-XXX: 标题 格式开始
4. 必须包含 **优先级:**、**描述:**、**前置条件:** 等加粗字段
5. 测试步骤必须使用标准的Markdown表格格式，包含表头和分隔行
6. 表格必须有三列：#、步骤描述、预期结果
7. 确保测试用例覆盖需求分析中的所有功能点
8. 包含正向、负向和边界测试场景
禁止输出：
- 不要输出"基于以下需求..."等介绍性文字
- 不要输出"测试用例集"等标题
- 不要输出测试范围或覆盖说明
- 直接从第一个测试用例 ## TC-001 开始

请严格遵循格式要求，直接生成测试用例。
"""

DEFAULT_REVIEW_PROMPT = """
你是一个资深的软件质量保证（QA）专家。
请对已生成的测试用例进行评审，找出不足之处，并且将其修改正确，补充缺少的测试用例

【关键要求】：
你必须直接返回一个合法的 JSON 对象，不要包裹在 markdown 代码块中，不要有任何前言或后语。
JSON 必须严格符合以下结构：
{
  "issues": ["问题描述1", "问题描述2"],
  "suggestions": ["优化建议1", "优化建议2"],
  "missing_scenarios": [
    {
      "module": "模块名",
      "scenario": "缺失场景描述",
      "test_point": "具体测试点"
    }
  ],
  "quality_score": 85,
  "summary": "整体评审总结",
  "reviewed_cases": [
    {
      "id": 101,
      "module": "测试模块名称",
      "title": "修正后的测试用例标题",
      "precondition": "前置条件说明",
      "steps": "步骤1...\\n步骤2...",
      "expected_result": "预期结果",
      "priority": "高"
    }
  ]
}
- issues: 发现的问题列表（如：缺少并发测试、未覆盖边界值等）
- suggestions: 优化建议列表
- missing_scenarios: 建议补充的测试场景列表
- quality_score: 用例质量评分（0-100）
- summary: 整体评审总结（中文，100字以内）
- reviewed_cases: 基于评审意见自动修正后的完整测试用例列表（必须返回）
"""


def _strip_code_fence(text: str) -> str:
    value = (text or "").strip()
    value = re.sub(r"^```json\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^```\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s*```$", "", value)
    return value.strip()


def _extract_json_array_text(text: str) -> str:
    value = _strip_code_fence(text)
    if value.startswith("[") and value.endswith("]"):
        return value

    start = value.find("[")
    if start < 0:
        raise ValueError("未找到 JSON 数组起始符 '['")

    depth = 0
    end = -1
    for i in range(start, len(value)):
        ch = value[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = i
                break

    if end < 0:
        raise ValueError("未找到 JSON 数组结束符 ']'")
    return value[start:end + 1]


def _extract_first_json_value_text(text: str) -> str:
    value = _strip_code_fence(text)
    decoder = json.JSONDecoder()
    for i, ch in enumerate(value):
        if ch not in "[{":
            continue
        try:
            _, end = decoder.raw_decode(value[i:])
            return value[i:i + end]
        except Exception:
            continue
    raise ValueError("未找到可解析的 JSON 内容")


def _extract_cases_payload(data: Any) -> Any:
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        for key in ("test_cases", "cases", "items", "data", "result"):
            value = data.get(key)
            if isinstance(value, list):
                return value
    return data


def _parse_cases_payload(text: str) -> List[Dict[str, Any]]:
    # 1) 直接按数组解析（最快）
    try:
        return _normalize_cases(json.loads(_extract_json_array_text(text)))
    except Exception:
        pass

    # 2) 解析首个 JSON 值（可能是对象包裹数组）
    payload = json.loads(_extract_first_json_value_text(text))
    return _normalize_cases(_extract_cases_payload(payload))


def _extract_review_payload(data: Any) -> Any:
    if isinstance(data, dict):
        if any(key in data for key in ("issues", "suggestions", "missing_scenarios", "quality_score", "summary")):
            return data
        for key in ("review", "result", "data", "payload"):
            value = data.get(key)
            if isinstance(value, dict):
                return value
    return data


def _normalize_review_payload(review: Any) -> Dict[str, Any]:
    if not isinstance(review, dict):
        raise ValueError("评审结果不是对象")

    issues_raw = review.get("issues") or []
    suggestions_raw = review.get("suggestions") or []
    missing_raw = review.get("missing_scenarios") or []

    if not isinstance(issues_raw, list):
        issues_raw = [issues_raw] if issues_raw else []
    if not isinstance(suggestions_raw, list):
        suggestions_raw = [suggestions_raw] if suggestions_raw else []
    if not isinstance(missing_raw, list):
        missing_raw = [missing_raw] if missing_raw else []

    issues = [str(x).strip() for x in issues_raw if str(x).strip()]
    suggestions = [str(x).strip() for x in suggestions_raw if str(x).strip()]
    missing_scenarios: List[Dict[str, str]] = []
    for item in missing_raw:
        if isinstance(item, dict):
            missing_scenarios.append(
                {
                    "module": str(item.get("module") or "").strip(),
                    "scenario": str(item.get("scenario") or "").strip(),
                    "test_point": str(item.get("test_point") or "").strip(),
                }
            )
        else:
            text = str(item).strip()
            if text:
                missing_scenarios.append({"module": "", "scenario": text, "test_point": ""})

    try:
        quality_score = int(float(review.get("quality_score", 0)))
    except Exception:
        quality_score = 0
    quality_score = max(0, min(100, quality_score))

    summary = str(review.get("summary") or "").strip()
    if not summary:
        summary = "评审已完成。"

    reviewed_cases: List[Dict[str, Any]] = []
    raw_reviewed_cases = review.get("reviewed_cases")
    if isinstance(raw_reviewed_cases, list):
        try:
            reviewed_cases = _normalize_cases(raw_reviewed_cases)
        except Exception:
            reviewed_cases = []

    normalized_review = {
        "issues": issues,
        "suggestions": suggestions,
        "missing_scenarios": missing_scenarios,
        "quality_score": quality_score,
        "summary": summary,
    }
    if reviewed_cases:
        normalized_review["reviewed_cases"] = reviewed_cases
    return normalized_review


def _parse_review_payload(text: str) -> Dict[str, Any]:
    payload = json.loads(_extract_first_json_value_text(text))
    return _normalize_review_payload(_extract_review_payload(payload))


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


def _normalize_cases(cases: Any) -> List[Dict[str, Any]]:
    if not isinstance(cases, list):
        raise ValueError("LLM 返回内容不是数组")

    normalized: List[Dict[str, Any]] = []
    for idx, item in enumerate(cases, start=1):
        if not isinstance(item, dict):
            continue
        raw_id = item.get("id")
        try:
            case_id = int(raw_id)
        except Exception:
            case_id = idx
        normalized.append(
            {
                "id": case_id,
                "module": str(item.get("module") or "通用"),
                "title": str(item.get("title") or f"测试用例{idx}"),
                "precondition": str(item.get("precondition") or "无"),
                "steps": str(item.get("steps") or ""),
                "expected_result": str(item.get("expected_result") or ""),
                "priority": str(item.get("priority") or "中"),
            }
        )

    if not normalized:
        raise ValueError("LLM 返回数组为空或字段无效")
    return normalized


def _normalize_role(role: str) -> str:
    value = (role or "").strip().lower()
    if value in {"analysis", "需求分析", "需求分析角色"}:
        return "analysis"
    if value in {"generation", "用例编写", "用例编写角色", "测试用例编写"}:
        return "generation"
    if value in {"review", "用例评审", "用例评审角色"}:
        return "review"
    return value


def _is_llm_error_text(text: str) -> bool:
    if not isinstance(text, str):
        return True
    return text.strip().lower().startswith("error:")


def _raise_if_llm_error(text: str, stage: str) -> None:
    if _is_llm_error_text(text):
        detail = (text or "").strip()
        raise RuntimeError(f"{stage}模型调用失败：{detail}")


def _pick_role_model_options(cfg: Dict[str, Any], role: str) -> Dict[str, Any]:
    normalized_role = _normalize_role(role)
    role_target_model = str((cfg.get("role_configs") or cfg.get("ai_models") or {}).get(normalized_role) or "").strip()
    fallback: Dict[str, Any] = {}
    for item in cfg.get("ai_model_configs", []):
        if not isinstance(item, dict):
            continue
        if not item.get("enabled", True):
            continue
        if not fallback:
            fallback = {
                "model": item.get("model_name") or llm_client.model,
                "api_key": item.get("api_key") or None,
                "base_url": item.get("api_base_url") or None,
                "temperature": item.get("temperature"),
                "max_tokens": item.get("max_tokens"),
                "top_p": item.get("top_p"),
            }
        if role_target_model and str(item.get("model_name") or "").strip() == role_target_model:
            return {
                "model": item.get("model_name") or llm_client.model,
                "api_key": item.get("api_key") or None,
                "base_url": item.get("api_base_url") or None,
                "temperature": item.get("temperature"),
                "max_tokens": item.get("max_tokens"),
                "top_p": item.get("top_p"),
            }
    return fallback


def _pick_role_prompt(cfg: Dict[str, Any], role: str, fallback: str) -> str:
    normalized_role = _normalize_role(role)
    for item in cfg.get("prompt_configs", []):
        if not isinstance(item, dict):
            continue
        if not item.get("enabled", True):
            continue
        prompt_role = _normalize_role(str(item.get("role") or item.get("prompt_type") or ""))
        if prompt_role == normalized_role:
            content = str(item.get("content") or "").strip()
            if content:
                return content
    prompts = cfg.get("prompts", {})
    prompt = str((prompts or {}).get(normalized_role) or "").strip()
    return prompt or fallback


async def _load_role_config() -> Dict[str, Dict[str, Any]]:
    cfg = await config_center_store.get_config_center()
    role_configs = cfg.get("role_configs", {}) or cfg.get("ai_models", {})
    analysis_options = _pick_role_model_options(cfg, "analysis")
    generation_options = _pick_role_model_options(cfg, "generation")
    review_options = _pick_role_model_options(cfg, "review")
    return {
        "analysis": {
            **analysis_options,
            "model": analysis_options.get("model") or role_configs.get("analysis") or llm_client.model,
            "prompt": _pick_role_prompt(cfg, "analysis", DEFAULT_ANALYSIS_PROMPT),
        },
        "generation": {
            **generation_options,
            "model": generation_options.get("model") or role_configs.get("generation") or llm_client.model,
            "prompt": _pick_role_prompt(cfg, "generation", DEFAULT_GENERATION_PROMPT),
        },
        "review": {
            **review_options,
            "model": review_options.get("model") or role_configs.get("review") or llm_client.model,
            "prompt": _pick_role_prompt(cfg, "review", DEFAULT_REVIEW_PROMPT),
        },
    }

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


async def generate_test_cases(design_result: str) -> List[Dict[str, Any]]:
    """AI Module - Generating Test Cases"""
    logger.info("AI Module: Generating Test Cases via LLM")
    
    role_cfg = (await _load_role_config())["generation"]
    system_prompt = role_cfg["prompt"]
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"测试策略如下：\n\n{design_result}"}
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

    logger.success(f"Generated {len(cases)} test cases.")
    return cases


async def review_test_cases(cases: List[Dict[str, Any]], analysis: str) -> Dict[str, Any]:
    """AI Module - Review and optimize generated test cases"""
    logger.info("AI Module: Reviewing test cases via LLM")
    
    cases_summary = json.dumps(cases, ensure_ascii=False, indent=2)
    
    role_cfg = (await _load_role_config())["review"]
    system_prompt = role_cfg["prompt"]
    
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
