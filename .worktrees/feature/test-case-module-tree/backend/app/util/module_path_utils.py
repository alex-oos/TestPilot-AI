"""模块路径解析与筛选工具。

作者: Zhao Wang
"""

from __future__ import annotations

import re

from sqlalchemy import or_

from app.models.test_case_model import TestCase

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def parse_module_path(module: str | None) -> list[str]:
    """将 module 字段解析为多级路径段。

    Args:
        module: 用例 module 字符串。

    Returns:
        路径段列表。
    """
    cleaned = _HTML_TAG_RE.sub("", str(module or "")).strip()
    if not cleaned:
        return []
    if " / " in cleaned:
        return [part.strip() for part in cleaned.split(" / ") if part.strip()]
    if "/" in cleaned:
        return [part.strip() for part in cleaned.split("/") if part.strip()]
    return [cleaned]


def join_module_path(segments: list[str]) -> str:
    """合并路径段为 module 存储字符串。

    Args:
        segments: 路径段列表。

    Returns:
        合并后的 module 字符串。
    """
    return " / ".join(part.strip() for part in segments if part and part.strip())


def module_prefix_filter(prefix: str):
    """生成 module 前缀匹配条件（含精确匹配）。

    Args:
        prefix: 模块路径前缀。

    Returns:
        SQLAlchemy 过滤表达式。
    """
    mod = str(prefix or "").strip()
    return or_(
        TestCase.module == mod,
        TestCase.module.like(f"{mod} / %"),
        TestCase.module.like(f"{mod}/%"),
    )
