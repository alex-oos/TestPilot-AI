"""需求驱动的测试用例同步上下文解析。

作者: Zhao Wang
"""

import re

from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.requirement_model import Requirement

_HTML_TAG_RE = re.compile(r"<[^>]+>")


def strip_html_tags(text: str | None) -> str:
    """去除 module 等字段中残留的 HTML 标签。

    Args:
        text: 原始文本。

    Returns:
        去除标签并 trim 后的纯文本。
    """
    return _HTML_TAG_RE.sub("", str(text or "")).strip()


def coerce_optional_int(value: object | None) -> int | None:
    """将 upload meta / JSON 中的 ID 安全转为 int。

    Args:
        value: 原始 ID 值，可能为 int、str 或 None。

    Returns:
        解析后的整数 ID；无法解析时返回 None。
    """
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_ai_module(ai_module: str | None) -> str:
    """规范化 AI 生成的子模块名。

    Args:
        ai_module: AI 用例中的 module 字段。

    Returns:
        非空模块名，空值时返回「默认模块」。
    """
    mod = strip_html_tags(ai_module)
    return mod if mod else "默认模块"


async def resolve_case_sync_context(
    db: AsyncSession,
    *,
    requirement_id: int | str | None,
    project_id: int | str | None,
    ai_module: str | None,
) -> tuple[str, int | None, int | None]:
    """解析同步到用例库时的 module、project_id、requirement_id。

    有关联需求时 module 仅存 AI 子模块名；需求标题作为 UI 根节点，通过 requirement_id 关联。

    Args:
        db: 异步数据库会话。
        requirement_id: 需求 ID（可为字符串）。
        project_id: 项目 ID（可为字符串）。
        ai_module: AI 生成的子模块名。

    Returns:
        (module, project_id, requirement_id) 三元组。
    """
    req_id = coerce_optional_int(requirement_id)
    proj_id = coerce_optional_int(project_id)
    sub_module = normalize_ai_module(ai_module)

    if req_id is None:
        return sub_module, proj_id, None

    req = await db.get(Requirement, req_id)
    if not req:
        logger.warning(
            "resolve_case_sync_context: requirement {} not found, fallback to ai module {}",
            req_id,
            sub_module,
        )
        return sub_module, proj_id, req_id

    resolved_project_id = proj_id if proj_id is not None else req.project_id
    return sub_module, resolved_project_id, req_id
