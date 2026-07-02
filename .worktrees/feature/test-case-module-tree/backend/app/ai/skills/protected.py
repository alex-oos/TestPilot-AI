"""内置受保护 Skill 标识。

作者：Zhao Wang
"""

from __future__ import annotations

from app.ai.skills.catalog import DEFAULT_SKILL_FOR_ROLE

# 仓库内置 library Skill，禁止通过 API 删除
PROTECTED_SKILL_IDS: frozenset[str] = frozenset(
    set(DEFAULT_SKILL_FOR_ROLE.values())
    | {
        "requirements-analysis-plus",
        "testcase-writer-plus",
        "test-case-reviewer-plus",
        "test-strategy-plus",
        "discover-testing",
        "api-test-pytest",
        "automation-testing",
        "functional-testing",
    }
)


def is_protected_skill(skill_id: str) -> bool:
    """判断 Skill 是否受保护不可删除。"""
    return (skill_id or "").strip() in PROTECTED_SKILL_IDS
