"""A/B 实验：generation 阶段双跑 baseline + variant，比较两份用例的关键指标。

启用：
- 在 .env 设置 QA_SKILL_AB_ENABLED=true
- 设置 QA_SKILL_AB_VARIANT_GENERATION=<另一个 skill_id>

效果：
- generate_test_cases 主流程会保留 baseline（默认 skill）的结果
- 同时异步运行 variant 拼装的 prompt，得到 variant_cases
- 把对比指标写入 audit.extra（不落库到 task_details，避免 schema 改动）
- 前端审计面板可看到指标
"""

from __future__ import annotations

from collections import Counter
from typing import Any


def _module_set(cases: list[dict]) -> set[str]:
    return {str(c.get("module", "")).strip() for c in cases if c.get("module")}


def _priority_dist(cases: list[dict]) -> dict[str, int]:
    return dict(Counter(str(c.get("priority", "")).strip() for c in cases))


def _blank_ratio(cases: list[dict], field: str) -> float:
    if not cases:
        return 0.0
    blanks = sum(1 for c in cases if not str(c.get(field, "")).strip())
    return round(blanks / len(cases), 4)


def compare(baseline: list[dict], variant: list[dict]) -> dict[str, Any]:
    """计算两份 cases 的对比指标。"""
    return {
        "baseline_count": len(baseline),
        "variant_count": len(variant),
        "module_count_baseline": len(_module_set(baseline)),
        "module_count_variant": len(_module_set(variant)),
        "module_overlap": len(_module_set(baseline) & _module_set(variant)),
        "module_only_in_variant": sorted(_module_set(variant) - _module_set(baseline))[:20],
        "priority_baseline": _priority_dist(baseline),
        "priority_variant": _priority_dist(variant),
        "blank_steps_baseline": _blank_ratio(baseline, "steps"),
        "blank_steps_variant": _blank_ratio(variant, "steps"),
        "blank_expected_baseline": _blank_ratio(baseline, "expected_result"),
        "blank_expected_variant": _blank_ratio(variant, "expected_result"),
    }
