import json
import re
import time
from loguru import logger
from typing import List, Dict, Any
from app.ai.llm import llm_client

async def analyze_requirements(text_content: str) -> str:
    """AI Module - Requirement Analysis"""
    logger.info("AI Module: Requirement Analysis via LLM")
    
    system_prompt = """
你是一个资深的软件需求分析师。
请阅读用户上传的项目文档内容，提取出关键的核心功能点、业务流程以及任何限制条件。
要求：
1. 结果以清晰的 Markdown 格式输出。
2. 将需求拆分为多个“模块”或“功能点”。
3. 突出显示任何隐藏的逻辑或者边缘情况。
"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"以下是项目文档内容：\n\n{text_content}"}
    ]
    
    analysis_result = await llm_client.chat(messages=messages, temperature=0.3)
    logger.success("Requirement Analysis completed.")
    return analysis_result


async def design_test_strategy(analysis_result: str) -> str:
    """AI Module - Test Design"""
    logger.info("AI Module: Test Design via LLM")
    
    system_prompt = """
你是一个资深的测试架构师。
基于前一步提取的【需求解析结果】，请设计一份全面的测试策略（Test Strategy）。
要求：
1. 必须覆盖：正常核心流程、边界值分析、异常处理测试（如格式错误、网络断开等）。
2. 提供等价类划分建议。
3. 结果使用清晰、排版的 Markdown 格式输出。
"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"需求解析结果如下：\n\n{analysis_result}"}
    ]

    design_result = await llm_client.chat(messages=messages, temperature=0.4)
    logger.success("Test Design completed.")
    return design_result


async def generate_test_cases(design_result: str) -> List[Dict[str, Any]]:
    """AI Module - Generating Test Cases"""
    logger.info("AI Module: Generating Test Cases via LLM")
    
    system_prompt = """
你是一个资深的软件测试工程师。
基于前述分配的【测试策略】，请编写详细的系统级测试用例。
【关键要求】：
你必须直接返回一个合法的 JSON 数组结构（List of Objects），并且不要包裹在 markdown 代码块（如 ```json）中。不要有任何前言或后语。
JSON 中的每一个对象代表一个测试用例，必须严格符合以下字段定义：
[
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
"""
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"测试策略如下：\n\n{design_result}"}
    ]

    cases_json_str = await llm_client.chat(messages=messages, temperature=0.1)
    
    # Simple cleanup just in case LLM wraps the response in ```json ... ```
    cases_json_str = cases_json_str.strip()
    if cases_json_str.startswith("```json"):
        cases_json_str = cases_json_str[7:]
    if cases_json_str.startswith("```"):
        cases_json_str = cases_json_str[3:]
    if cases_json_str.endswith("```"):
        cases_json_str = cases_json_str[:-3]
    cases_json_str = cases_json_str.strip()
    
    try:
        cases = json.loads(cases_json_str)
        if not isinstance(cases, list):
            raise ValueError("LLM did not return a list")
    except Exception as e:
        logger.error(f"Failed to parse test cases JSON from LLM: {str(e)}\nRaw Output: {cases_json_str}")
        # Fallback to empty or mocked behavior if parsing strictly fails
        cases = [
            {
                "id": 1,
                "module": "Error",
                "title": "LLM Test Generation failed to parse",
                "precondition": "N/A",
                "steps": "Check LLM logs.",
                "expected_result": "JSON should be perfectly valid.",
                "priority": "高"
            }
        ]

    logger.success(f"Generated {len(cases)} test cases.")
    return cases


async def review_test_cases(cases: List[Dict[str, Any]], analysis: str) -> Dict[str, Any]:
    """AI Module - Review and optimize generated test cases"""
    logger.info("AI Module: Reviewing test cases via LLM")
    
    cases_summary = json.dumps(cases, ensure_ascii=False, indent=2)
    
    system_prompt = """
你是一个资深的软件质量保证（QA）专家。
请对已生成的测试用例进行评审，找出不足之处并提出优化建议。

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
  "summary": "整体评审总结"
}
- issues: 发现的问题列表（如：缺少并发测试、未覆盖边界值等）
- suggestions: 优化建议列表
- missing_scenarios: 建议补充的测试场景列表
- quality_score: 用例质量评分（0-100）
- summary: 整体评审总结（中文，100字以内）
"""
    
    user_content = f"""【需求分析结果】：
{analysis}

【已生成的测试用例（共{len(cases)}条）】：
{cases_summary}"""
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_content}
    ]
    
    review_str = await llm_client.chat(messages=messages, temperature=0.3)
    
    # Clean up potential markdown wrapping
    review_str = review_str.strip()
    review_str = re.sub(r'^```json\s*', '', review_str)
    review_str = re.sub(r'^```\s*', '', review_str)
    review_str = re.sub(r'\s*```$', '', review_str)
    review_str = review_str.strip()
    
    try:
        review = json.loads(review_str)
        if not isinstance(review, dict):
            raise ValueError("LLM did not return a dict")
    except Exception as e:
        logger.error(f"Failed to parse review JSON from LLM: {str(e)}\nRaw: {review_str}")
        review = {
            "issues": ["AI评审解析失败，请检查LLM输出格式"],
            "suggestions": ["建议手动检查生成的测试用例完整性"],
            "missing_scenarios": [],
            "quality_score": 0,
            "summary": "AI评审模块返回内容格式有误，已降级处理。"
        }
    
    logger.success(f"Test case review completed. Quality score: {review.get('quality_score', 'N/A')}")
    return review
