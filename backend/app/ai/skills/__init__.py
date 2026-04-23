"""QA Skills 子系统：基于 awesome-qa-skills 的 SKILL 化 prompt 体系。

模块：
- loader.py    : 加载 SKILL.md + prompts/ + output-templates/ + examples/ + references/，含 overlay
- builder.py   : skill + few-shot + Output Contract + 业务自定义 拼装
- catalog.py   : 角色 → skill_id 默认映射
- discover.py  : 智能路由（关键词法）
- audit.py     : 调用审计（in-memory + task_details 持久化）
"""

from app.ai.skills import audit, discover
from app.ai.skills.builder import (
    BuildResult,
    build_analysis_messages,
    build_generation_messages,
    build_review_messages,
    build_supplement_messages,
)
from app.ai.skills.catalog import (
    DEFAULT_SKILL_FOR_ROLE,
    ROLE_ANALYSIS,
    ROLE_DISCOVER,
    ROLE_GENERATION,
    ROLE_REVIEW,
    ROLE_SUPPLEMENT,
)
from app.ai.skills.loader import (
    SkillBundle,
    SkillExample,
    SkillNotFoundError,
    get_skill_loader,
    load_skill,
)

__all__ = [
    "audit",
    "discover",
    "BuildResult",
    "build_analysis_messages",
    "build_generation_messages",
    "build_review_messages",
    "build_supplement_messages",
    "DEFAULT_SKILL_FOR_ROLE",
    "ROLE_ANALYSIS",
    "ROLE_DISCOVER",
    "ROLE_GENERATION",
    "ROLE_REVIEW",
    "ROLE_SUPPLEMENT",
    "SkillBundle",
    "SkillExample",
    "SkillNotFoundError",
    "get_skill_loader",
    "load_skill",
]
