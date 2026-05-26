"""长文档智能压缩（优先于硬截断）。

作者: Zhao Wang
"""

from __future__ import annotations

import re
from typing import Any


_PRIORITY_KEYWORDS = (
    "功能", "流程", "接口", "API", "权限", "角色", "异常", "边界",
    "状态", "规则", "需求", "业务", "模块", "用例", "测试",
)


def _is_priority_section(title: str, body: str) -> bool:
    """判断是否策略相关章节。"""
    combined = f"{title} {body[:200]}"
    return any(kw in combined for kw in _PRIORITY_KEYWORDS)


def compress_text_for_llm(
    text: str,
    *,
    max_chars: int,
    mode_hint: str = "general",
) -> tuple[str, dict[str, Any]]:
    """压缩文本以适配 LLM 上下文。

    Args:
        text: 原始文本。
        max_chars: 最大字符数。
        mode_hint: 用途提示（general/analysis/strategy）。

    Returns:
        (压缩后文本, meta) meta 含 compression_mode。
    """
    source = (text or "").strip()
    if not source or len(source) <= max_chars:
        return source, {"compression_mode": "none", "original_chars": len(source), "final_chars": len(source)}

    heading_pattern = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)
    if heading_pattern.search(source):
        compressed = _compress_by_headings(source, max_chars=max_chars)
        if len(compressed) <= max_chars:
            return compressed, {
                "compression_mode": "heading",
                "original_chars": len(source),
                "final_chars": len(compressed),
            }

    if mode_hint == "strategy":
        compressed = _compress_paragraph_summary(source, max_chars=max_chars)
        if len(compressed) <= max_chars:
            return compressed, {
                "compression_mode": "summary",
                "original_chars": len(source),
                "final_chars": len(compressed),
            }

    truncated = source[:max_chars]
    return truncated, {
        "compression_mode": "hard_truncate",
        "original_chars": len(source),
        "final_chars": len(truncated),
        "truncated": True,
    }


def _compress_by_headings(text: str, *, max_chars: int) -> str:
    """按 Markdown 标题保留优先章节。"""
    sections: list[tuple[str, str]] = []
    current_title = "前言"
    current_lines: list[str] = []

    for line in text.splitlines():
        m = re.match(r"^(#{1,4})\s+(.+)$", line.strip())
        if m:
            if current_lines:
                sections.append((current_title, "\n".join(current_lines).strip()))
            current_title = m.group(2).strip()
            current_lines = []
        else:
            current_lines.append(line)
    if current_lines:
        sections.append((current_title, "\n".join(current_lines).strip()))

    priority = [s for s in sections if _is_priority_section(s[0], s[1])]
    others = [s for s in sections if s not in priority]
    ordered = priority + others

    parts: list[str] = []
    total = 0
    for title, body in ordered:
        chunk = f"## {title}\n{body}".strip()
        if total + len(chunk) + 2 > max_chars:
            remain = max_chars - total - 2
            if remain > 200:
                parts.append(chunk[:remain] + "\n...(已截断)")
            break
        parts.append(chunk)
        total += len(chunk) + 2
    return "\n\n".join(parts)


def _compress_paragraph_summary(text: str, *, max_chars: int) -> str:
    """段落级摘要：保留每段首句。"""
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", text) if p.strip()]
    lines: list[str] = []
    total = 0
    for para in paragraphs:
        first_line = para.split("\n", 1)[0].strip()
        if len(first_line) < 20:
            snippet = para[: min(300, len(para))]
        else:
            snippet = first_line
        if total + len(snippet) + 1 > max_chars:
            break
        lines.append(snippet)
        total += len(snippet) + 1
    return "\n".join(lines)
