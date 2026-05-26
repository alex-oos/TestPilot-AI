"""覆盖矩阵与缺口检测单测。"""

from app.ai.coverage_planner import (
    build_coverage_matrix,
    find_coverage_gaps,
    merge_and_dedupe_cases,
    normalize_merged_cases,
)
from app.ai.strategy_schema import ModuleV1, TestPointV1, TestStrategyV1, GlobalRequirementsV1


def _sample_strategy() -> TestStrategyV1:
    return TestStrategyV1(
        modules=[
            ModuleV1(
                name="登录",
                test_points=[
                    TestPointV1(id="TP-1", title="正确账号登录", min_cases=1),
                    TestPointV1(id="TP-2", title="密码错误", min_cases=1),
                ],
            )
        ],
        global_requirements=GlobalRequirementsV1(required_case_types=["功能-正向", "功能-反向"]),
    )


def test_coverage_matrix_uncovered():
    strategy = _sample_strategy()
    cases = [{"id": 1, "module": "登录", "title": "验证正确账号登录", "case_type": "功能-正向"}]
    matrix = build_coverage_matrix(strategy, cases)
    assert matrix["total_test_points"] == 2
    assert len(matrix["uncovered"]) >= 1


def test_merge_dedupe_by_title():
    a = [{"id": 1, "title": "验证A", "steps": "1. x", "module": "M"}]
    b = [{"id": 2, "title": "验证A", "steps": "1. x", "module": "M"}]
    merged = merge_and_dedupe_cases([a, b])
    assert len(merged) == 1


def test_normalize_merged_cases_reindex():
    cases = [
        {"id": 5, "module": "login", "title": "验证登录"},
        {"id": 9, "module": "login", "title": "验证登出"},
    ]
    out = normalize_merged_cases(cases, canonical_modules=["登录"])
    assert out[0]["id"] == 1
    assert out[0]["module"] == "登录"


def test_find_coverage_gaps_missing_type():
    strategy = _sample_strategy()
    cases = [{"id": 1, "module": "登录", "title": "验证正确账号登录", "case_type": "功能-正向"}]
    gaps = find_coverage_gaps(strategy, cases)
    assert "功能-反向" in gaps.get("missing_case_types", [])
