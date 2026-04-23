"""业务角色 ↔ Skill 的默认映射表。"""

from __future__ import annotations

ROLE_ANALYSIS = "analysis"
ROLE_GENERATION = "generation"
ROLE_REVIEW = "review"
ROLE_SUPPLEMENT = "supplement"
ROLE_DISCOVER = "discover"


DEFAULT_SKILL_FOR_ROLE: dict[str, str] = {
    ROLE_ANALYSIS: "requirements-analysis-plus",
    ROLE_GENERATION: "testcase-writer-plus",
    ROLE_REVIEW: "test-case-reviewer-plus",
    ROLE_SUPPLEMENT: "testcase-writer-plus",
    ROLE_DISCOVER: "discover-testing",
}
