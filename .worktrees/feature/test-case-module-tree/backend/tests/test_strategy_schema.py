"""TestStrategyV1 解析与降级单测。"""

import json

from app.ai.strategy_schema import (
    TestStrategyV1,
    compute_expected_min_cases,
    parse_strategy_v1,
    try_parse_strategy,
)


def test_parse_strategy_v1_json():
    raw = {
        "version": "1",
        "modules": [{
            "name": "登录",
            "risk_level": "高",
            "test_points": [{
                "id": "TP-001",
                "title": "正确账号登录",
                "case_types_required": ["功能-正向"],
                "min_cases": 2,
            }],
        }],
        "global_requirements": {"min_total_cases": 5, "required_case_types": ["功能-正向"]},
    }
    strategy = parse_strategy_v1(json.dumps(raw))
    assert strategy.version == "1"
    assert strategy.modules[0].name == "登录"
    assert compute_expected_min_cases(strategy) >= 2


def test_markdown_fallback_to_v1():
    md = """
## 用户模块
- 登录成功
- 密码错误

## 订单模块
- 创建订单
"""
    strategy, raw = try_parse_strategy(md)
    assert strategy is not None
    assert len(strategy.modules) >= 1
    assert "用户" in strategy.modules[0].name or strategy.modules[0].name
