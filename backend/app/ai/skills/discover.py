"""智能路由：根据需求文档关键词推断最适合的 generation / review skill。

策略：
1. 关键词命中（轻量、零 LLM 成本，<10ms） —— 默认开启，足够覆盖常见情况。
2. Skill tags 加权：library 中所有 skill 的 tags 也参与评分，命中越多权重越高。
3. 中英文双语关键词支持。
4. 可选：调用 discover-testing skill 让 LLM 决策（重，需要 .env 开启）。
"""

from __future__ import annotations

import re
from typing import Any

from loguru import logger

# 关键词 → 推荐 skill 映射（按优先级匹配，先命中先用，中英双语）
_KEYWORD_RULES: list[tuple[re.Pattern[str], dict[str, str]]] = [
    (
        re.compile(r"(api|REST|GraphQL|gRPC|HTTP|接口|swagger|OpenAPI|postman|bruno|webhook|endpoint)", re.I),
        {"generation": "api-test-pytest", "review": "test-case-reviewer-plus", "category": "api"},
    ),
    (
        re.compile(r"(Android|iOS|移动端|App\b|H5|微信小程序|小程序|手机|Flutter|React Native|mobile|tablet)", re.I),
        {"generation": "mobile-testing", "review": "test-case-reviewer-plus", "category": "mobile"},
    ),
    (
        re.compile(r"(性能|压测|TPS|QPS|并发|响应时间|稳定性|吞吐|压力|spike|loadtest|k6|Gatling|JMeter|throughput|latency|benchmark|stress)", re.I),
        {"generation": "performance-testing", "review": "test-case-reviewer-plus", "category": "performance"},
    ),
    (
        re.compile(r"(安全|XSS|SQL\s*注入|CSRF|越权|渗透|OWASP|SSRF|RCE|信息泄露|加密|security|vulnerability|pentest|injection|auth bypass)", re.I),
        {"generation": "security-testing", "review": "test-case-reviewer-plus", "category": "security"},
    ),
    (
        re.compile(r"(可访问性|无障碍|accessibility|WCAG|屏幕朗读|残障|a11y|aria-label|screen reader)", re.I),
        {"generation": "accessibility-testing", "review": "test-case-reviewer-plus", "category": "accessibility"},
    ),
    (
        re.compile(r"(自动化|UI 自动化|端到端|E2E|Playwright|Cypress|Selenium|WebDriver|automation|headless)", re.I),
        {"generation": "automation-testing", "review": "test-case-reviewer-plus", "category": "automation"},
    ),
]

DEFAULT_ROUTE = {
    "generation": "testcase-writer-plus",
    "review": "test-case-reviewer-plus",
    "category": "functional",
}


def route_by_keywords(text: str) -> dict[str, Any]:
    """关键词路由。返回 {generation, review, category, matched_pattern}。"""
    if not text:
        return {**DEFAULT_ROUTE, "matched_pattern": None, "decided_by": "default"}

    text_head = text[:6000]  # 只看前 6k 避免过慢
    for pattern, route in _KEYWORD_RULES:
        m = pattern.search(text_head)
        if m:
            picked = {**route, "matched_pattern": m.group(0), "decided_by": "keyword"}
            logger.info(
                "[discover] 关键词命中 '{}' → category={} generation={}",
                m.group(0), route["category"], route["generation"],
            )
            return picked

    return {**DEFAULT_ROUTE, "matched_pattern": None, "decided_by": "default"}


def filter_to_available(route: dict[str, Any], available_skills: list[str]) -> dict[str, Any]:
    """如果路由结果指向了 library 里不存在的 skill，自动降级到默认。"""
    out = dict(route)
    for k in ("generation", "review"):
        sid = out.get(k)
        if sid and sid not in available_skills:
            logger.warning(
                "[discover] 路由 skill '{}' 不在 library 中，降级到默认 '{}'",
                sid, DEFAULT_ROUTE[k],
            )
            out[k] = DEFAULT_ROUTE[k]
            out["decided_by"] = "fallback"
    return out


def route_by_skill_tags(text: str, max_candidates: int = 3) -> dict[str, Any]:
    """基于 library 中所有 skill 的 tags 评分，给出 generation 候选。

    - 每个 tag 命中文本一次 +1
    - skill_id 命中文本 +2
    - 仅在 generation 角色用 skill 上评分（启发：tags 含 'generation'/'testcase'/'api' 等）
    返回最高分 skill 或 None。
    """
    if not text:
        return {}
    try:
        from app.ai.skills.loader import get_skill_loader
    except Exception:
        return {}
    loader = get_skill_loader()
    text_lower = text[:8000].lower()
    scores: list[tuple[str, int, list[str]]] = []
    for sid in loader.list_available():
        try:
            b = loader.load(sid)
        except Exception:
            continue
        score = 0
        hits: list[str] = []
        sid_low = sid.lower()
        if sid_low in text_lower:
            score += 2
            hits.append(sid_low)
        for tag in (b.tags or []):
            tl = str(tag).lower().strip()
            if tl and tl in text_lower:
                score += 1
                hits.append(tl)
        if score > 0:
            scores.append((sid, score, hits))
    scores.sort(key=lambda x: x[1], reverse=True)
    top = scores[:max_candidates]
    if not top:
        return {}
    best_sid, best_score, best_hits = top[0]
    return {
        "skill_id": best_sid,
        "score": best_score,
        "hits": best_hits,
        "candidates": [{"skill_id": s, "score": sc, "hits": h} for (s, sc, h) in top],
    }


def route_combined(text: str, available_skills: list[str] | None = None) -> dict[str, Any]:
    """关键词 + tags 联合路由：先按规则；规则未命中再用 tags 评分。"""
    base = route_by_keywords(text)
    if base.get("decided_by") != "default":
        return base
    tag_route = route_by_skill_tags(text)
    if tag_route and tag_route.get("skill_id"):
        sid = tag_route["skill_id"]
        if available_skills and sid not in available_skills:
            return base
        return {
            **DEFAULT_ROUTE,
            "generation": sid,
            "matched_pattern": ",".join(tag_route.get("hits", [])[:5]),
            "decided_by": "skill_tags",
            "tag_candidates": tag_route.get("candidates", []),
        }
    return base
