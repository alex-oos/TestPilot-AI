"""Skill 健康检查：启动时 lint，运行时通过 /api/ai/skills/health 查询。

策略：
- soft (默认)：只 WARN 不 raise，让进程能起来；问题列表通过 health 接口暴露
- strict：任何 skill 加载失败 / SKILL.md 缺关键字段 → 启动直接抛 RuntimeError

校验项：
- SKILL.md 存在 + frontmatter 含 name / description
- 至少 1 个 prompts/*.md
- primary_prompt 长度 ≥ 100 字
- frontmatter 中如有 version，必须形如 semver
- 角色映射的目标 skill 必须在 library 中
"""

from __future__ import annotations

import re
from dataclasses import asdict, dataclass, field
from typing import Any

from loguru import logger

from app.ai.skills import DEFAULT_SKILL_FOR_ROLE, SkillBundle, get_skill_loader
from app.ai.skills.loader import SkillNotFoundError
from app.core.config import settings

_SEMVER = re.compile(r"^\d+\.\d+\.\d+([\-\+].+)?$")


@dataclass
class SkillCheck:
    skill_id: str
    ok: bool
    issues: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    version: str = ""
    lang: str = ""
    prompts: int = 0
    primary_chars: int = 0
    requires: list[str] = field(default_factory=list)


@dataclass
class HealthReport:
    ok: bool
    library_dir: str
    total: int
    failed: int
    warning_only: int
    role_mapping_issues: list[str] = field(default_factory=list)
    checks: list[SkillCheck] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "library_dir": self.library_dir,
            "total": self.total,
            "failed": self.failed,
            "warning_only": self.warning_only,
            "role_mapping_issues": self.role_mapping_issues,
            "checks": [asdict(c) for c in self.checks],
        }


def _check_one(b: SkillBundle) -> SkillCheck:
    chk = SkillCheck(
        skill_id=b.skill_id,
        ok=True,
        version=b.version,
        lang=b.lang,
        prompts=len(b.prompts),
        primary_chars=len(b.primary_prompt),
        requires=list(b.frontmatter.get("requires") or []) if isinstance(b.frontmatter.get("requires"), list) else [],
    )
    if not b.name or b.name == b.skill_id:
        chk.warnings.append("SKILL.md frontmatter 中缺少友好的 name 字段（已用 skill_id 兜底）")
    if not b.description:
        chk.issues.append("SKILL.md frontmatter 缺少 description")
    if len(b.prompts) == 0:
        chk.issues.append("prompts/ 目录为空")
    if len(b.primary_prompt) < 100:
        chk.issues.append(f"primary_prompt 内容过短（{len(b.primary_prompt)} < 100 字）")
    if b.version and not _SEMVER.match(b.version):
        chk.warnings.append(f"version='{b.version}' 不是 semver（建议 X.Y.Z）")
    chk.ok = not chk.issues
    return chk


def run_health_check() -> HealthReport:
    loader = get_skill_loader()
    available = loader.list_available()
    checks: list[SkillCheck] = []
    failed = 0
    warning_only = 0

    for sid in available:
        try:
            b = loader.load(sid)
            chk = _check_one(b)
        except SkillNotFoundError as e:
            chk = SkillCheck(skill_id=sid, ok=False, issues=[f"loader 无法加载: {e}"])
        except Exception as e:
            chk = SkillCheck(skill_id=sid, ok=False, issues=[f"加载抛异常: {e}"])
        checks.append(chk)
        if not chk.ok:
            failed += 1
        elif chk.warnings:
            warning_only += 1

    role_issues: list[str] = []
    env_overrides = {
        "analysis": settings.QA_SKILL_ANALYSIS,
        "generation": settings.QA_SKILL_GENERATION,
        "review": settings.QA_SKILL_REVIEW,
        "supplement": settings.QA_SKILL_SUPPLEMENT,
        "discover": settings.QA_SKILL_DISCOVER,
    }
    for role, default_sid in DEFAULT_SKILL_FOR_ROLE.items():
        eff = (env_overrides.get(role) or "").strip() or default_sid
        if eff and eff not in available:
            role_issues.append(
                f"role={role} → skill_id={eff} 不在 library 中（覆盖来源={'env' if env_overrides.get(role) else 'catalog默认'}）"
            )

    report = HealthReport(
        ok=(failed == 0 and not role_issues),
        library_dir=str(loader.library_dir),
        total=len(checks),
        failed=failed,
        warning_only=warning_only,
        role_mapping_issues=role_issues,
        checks=checks,
    )
    return report


def assert_startup_health() -> HealthReport:
    """应用启动时调用。strict 模式下不通过即抛错。"""
    report = run_health_check()
    if report.ok:
        logger.info(
            "[skill] 启动健康检查通过：{} 个 skill，{} 个仅有 warning",
            report.total, report.warning_only,
        )
        return report

    for chk in report.checks:
        if not chk.ok:
            for it in chk.issues:
                logger.error("[skill] {} 失败：{}", chk.skill_id, it)
        for w in chk.warnings:
            logger.warning("[skill] {} 警告：{}", chk.skill_id, w)
    for ri in report.role_mapping_issues:
        logger.error("[skill] 角色映射问题：{}", ri)

    if bool(getattr(settings, "QA_SKILL_HEALTH_STRICT", False)):
        raise RuntimeError(
            f"QA Skill 启动健康检查失败：失败 {report.failed} 个，"
            f"映射问题 {len(report.role_mapping_issues)} 处。设置 QA_SKILL_HEALTH_STRICT=false 可降级为 warning。"
        )
    logger.warning("[skill] 健康检查未通过但 STRICT=False，已降级运行（详见 /api/ai/skills/health）")
    return report
