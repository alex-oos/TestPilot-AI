"""结构化测试策略 Schema（TestStrategyV1）。

作者: Zhao Wang
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field
from typing import Any


CASE_TYPES_ALL = (
    "功能-正向", "功能-反向", "边界值", "异常处理",
    "权限/角色", "并发/时序", "数据校验", "兼容/UI", "性能/容量",
)


@dataclass
class TestPointV1:
    """测试点。"""

    id: str
    title: str
    case_types_required: list[str] = field(default_factory=lambda: ["功能-正向"])
    min_cases: int = 1
    priority_hint: str = "中"


@dataclass
class ModuleV1:
    """策略模块。"""

    name: str
    risk_level: str = "中"
    test_points: list[TestPointV1] = field(default_factory=list)


@dataclass
class GlobalRequirementsV1:
    """全局约束。"""

    min_total_cases: int = 10
    required_case_types: list[str] = field(default_factory=lambda: list(CASE_TYPES_ALL[:5]))


@dataclass
class TestStrategyV1:
    """TestStrategyV1 根对象。"""

    version: str = "1"
    modules: list[ModuleV1] = field(default_factory=list)
    global_requirements: GlobalRequirementsV1 = field(default_factory=GlobalRequirementsV1)

    def to_dict(self) -> dict[str, Any]:
        """转为可序列化 dict。"""
        return asdict(self)

    def to_json(self) -> str:
        """转为 JSON 字符串。"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


def _coerce_test_point(raw: dict[str, Any], idx: int) -> TestPointV1:
    """解析单个测试点。"""
    tp_id = str(raw.get("id") or f"TP-{idx:03d}").strip()
    title = str(raw.get("title") or raw.get("name") or f"测试点{idx}").strip()
    types_raw = raw.get("case_types_required") or raw.get("case_types") or ["功能-正向"]
    if isinstance(types_raw, str):
        types_raw = [types_raw]
    case_types = [str(t).strip() for t in types_raw if str(t).strip()]
    min_cases = int(raw.get("min_cases") or 1)
    priority = str(raw.get("priority_hint") or raw.get("priority") or "中").strip()
    return TestPointV1(
        id=tp_id,
        title=title,
        case_types_required=case_types or ["功能-正向"],
        min_cases=max(1, min_cases),
        priority_hint=priority,
    )


def _coerce_module(raw: dict[str, Any], idx: int) -> ModuleV1:
    """解析单个模块。"""
    name = str(raw.get("name") or raw.get("module") or f"模块{idx}").strip()
    risk = str(raw.get("risk_level") or raw.get("risk") or "中").strip()
    tps_raw = raw.get("test_points") or raw.get("points") or []
    test_points: list[TestPointV1] = []
    if isinstance(tps_raw, list):
        for i, tp in enumerate(tps_raw, start=1):
            if isinstance(tp, dict):
                test_points.append(_coerce_test_point(tp, i))
            elif isinstance(tp, str) and tp.strip():
                test_points.append(_coerce_test_point({"title": tp.strip()}, i))
    if not test_points:
        test_points.append(_coerce_test_point({"title": f"{name}核心流程"}, 1))
    return ModuleV1(name=name, risk_level=risk, test_points=test_points)


def parse_strategy_v1(data: Any) -> TestStrategyV1:
    """从 dict 或 JSON 字符串解析 TestStrategyV1。

    Args:
        data: dict 或 JSON 字符串。

    Returns:
        TestStrategyV1 实例。

    Raises:
        ValueError: 解析失败。
    """
    if isinstance(data, str):
        text = data.strip()
        if text.startswith("```"):
            text = re.sub(r"^```(?:json)?\s*", "", text)
            text = re.sub(r"\s*```$", "", text)
        try:
            data = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"策略 JSON 解析失败: {exc}") from exc
    if not isinstance(data, dict):
        raise ValueError("策略必须是 JSON 对象")

    modules_raw = data.get("modules") or []
    modules: list[ModuleV1] = []
    if isinstance(modules_raw, list):
        for i, mod in enumerate(modules_raw, start=1):
            if isinstance(mod, dict):
                modules.append(_coerce_module(mod, i))

    gr_raw = data.get("global_requirements") or data.get("global") or {}
    if not isinstance(gr_raw, dict):
        gr_raw = {}
    global_req = GlobalRequirementsV1(
        min_total_cases=int(gr_raw.get("min_total_cases") or 10),
        required_case_types=list(gr_raw.get("required_case_types") or CASE_TYPES_ALL[:5]),
    )
    if not modules:
        modules.append(ModuleV1(name="默认模块", test_points=[TestPointV1(id="TP-001", title="核心功能验证")]))

    return TestStrategyV1(
        version=str(data.get("version") or "1"),
        modules=modules,
        global_requirements=global_req,
    )


def try_parse_strategy(text: str) -> tuple[TestStrategyV1 | None, str]:
    """尝试解析策略；失败返回 (None, 原文)。"""
    raw = (text or "").strip()
    if not raw:
        return None, raw
    if raw.startswith("{") or '"modules"' in raw[:500]:
        try:
            return parse_strategy_v1(raw), raw
        except ValueError:
            pass
    try:
        return _markdown_strategy_to_v1(raw), raw
    except Exception:
        return None, raw


def _markdown_strategy_to_v1(markdown: str) -> TestStrategyV1:
    """Markdown 策略启发式转换为 V1（降级路径）。"""
    text = (markdown or "").strip()
    modules: list[ModuleV1] = []
    current_module: ModuleV1 | None = None
    tp_idx = 0

    heading_re = re.compile(r"^(#{1,4})\s+(.+)$", re.MULTILINE)
    bullet_re = re.compile(r"^[\-\*•]\s+(.+)$", re.MULTILINE)

    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        hm = re.match(r"^#{1,4}\s+(.+)$", line)
        if hm:
            title = hm.group(1).strip()
            if any(k in title for k in ("模块", "功能", "Module", "章节")) or len(modules) == 0:
                current_module = ModuleV1(name=title.replace("模块", "").strip() or title)
                modules.append(current_module)
            continue
        bm = re.match(r"^[\-\*•]\s+(.+)$", line)
        if bm and current_module is not None:
            tp_idx += 1
            current_module.test_points.append(
                TestPointV1(id=f"TP-{tp_idx:03d}", title=bm.group(1).strip()[:120])
            )

    if not modules:
        bullets = bullet_re.findall(text)
        mod = ModuleV1(name="通用模块")
        for i, b in enumerate(bullets[:20], start=1):
            mod.test_points.append(TestPointV1(id=f"TP-{i:03d}", title=b.strip()[:120]))
        if mod.test_points:
            modules.append(mod)

    if not modules:
        modules.append(ModuleV1(
            name="默认模块",
            test_points=[TestPointV1(id="TP-001", title="核心业务流程验证")],
        ))

    return TestStrategyV1(version="1", modules=modules)


def compute_expected_min_cases(strategy: TestStrategyV1) -> int:
    """根据策略计算期望最少用例数。"""
    point_sum = sum(max(1, tp.min_cases) for mod in strategy.modules for tp in mod.test_points)
    global_min = int(strategy.global_requirements.min_total_cases or 0)
    return max(point_sum, global_min)


def strategy_module_names(strategy: TestStrategyV1) -> list[str]:
    """提取模块名列表。"""
    return [m.name for m in strategy.modules if m.name]
