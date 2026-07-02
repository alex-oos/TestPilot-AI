"""离线测试用例质量门禁。

完全基于规则评分（无 LLM 依赖），用于：
1. 生成阶段后立即评分，找到低分用例触发"自动细化重生成"；
2. 给前端"用例质量"tab 提供快速诊断；
3. 给 review 提供基线，避免 LLM 自评打高分。

评分维度（与 review sub_scores 对齐）：
- coverage          —— 是否覆盖 9 种 case_type；
- completeness      —— 字段是否齐全（precondition/test_data/steps/expected）；
- executability     —— 步骤是否结构化（三段式 / 编号 / 长度）；
- boundary          —— 是否包含边界值/异常/极值用例；
- data_accuracy     —— test_data 是否含具体字段值；
- priority_balance  —— 高/中/低 是否分布合理。

调用：
    audit = score_cases(cases)
    audit.overall_score, audit.average_case_score
    find_low_quality_ids(audit, threshold=60)
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import asdict, dataclass, field
from typing import Any


CASE_TYPES = (
    "功能-正向", "功能-反向", "边界值", "异常处理",
    "权限/角色", "并发/时序", "数据校验", "兼容/UI", "性能/容量",
)

PRIORITY_TARGET = {"高": 0.30, "中": 0.50, "低": 0.20}

# 关键词触发推断（用于 _fill_case_blanks 和 case_type 检测）
TYPE_KEYWORDS: dict[str, tuple[str, ...]] = {
    "功能-反向":   ("失败", "错误", "拒绝", "无效", "不存在", "缺少"),
    "边界值":     ("最大", "最小", "上限", "下限", "极值", "0", "1", "边界"),
    "异常处理":   ("超时", "断网", "中断", "宕机", "异常", "崩溃", "回滚"),
    "权限/角色":  ("权限", "角色", "未登录", "越权", "鉴权", "管理员", "普通用户"),
    "并发/时序":  ("并发", "竞态", "重复提交", "幂等", "重试", "时序"),
    "数据校验":   ("校验", "格式", "空字符", "非法字符", "正则", "长度", "类型"),
    "兼容/UI":    ("兼容", "浏览器", "分辨率", "样式", "刷新", "国际化", "i18n"),
    "性能/容量":  ("性能", "并发量", "qps", "rps", "tps", "压测", "稳定性"),
}

NEGATIVE_RESULT_KEYWORDS = ("正常", "成功", "符合预期")  # 模糊词，命中扣分


@dataclass
class CaseScore:
    case_id: Any
    score: int
    issues: list[str] = field(default_factory=list)
    field_lengths: dict[str, int] = field(default_factory=dict)


@dataclass
class CasesAudit:
    total: int
    overall_score: int
    average_case_score: float
    sub_scores: dict[str, int]
    type_distribution: dict[str, int]
    priority_distribution: dict[str, int]
    low_quality_ids: list[Any]
    missing_types: list[str]
    weak_areas: list[str]
    cases: list[CaseScore]


# ---------------- 单条用例评分 ----------------

_STEP_TRIPLE_RE = re.compile(r"\[操作\]|\[数据\]|\[校验\]")
_STEP_NUMBER_RE = re.compile(r"^\s*\d+[\.\)、]")


def _len_field(case: dict[str, Any], key: str) -> int:
    val = case.get(key)
    return len(str(val).strip()) if val is not None else 0


def _step_count(steps: str) -> int:
    if not steps:
        return 0
    lines = [ln for ln in steps.splitlines() if ln.strip()]
    numbered = [ln for ln in lines if _STEP_NUMBER_RE.match(ln)]
    return max(len(numbered), len(lines))


def _has_triple_format(steps: str) -> bool:
    if not steps:
        return False
    return len(set(_STEP_TRIPLE_RE.findall(steps))) >= 2  # 至少出现 2 个 segment


_DATA_TAG_RE = re.compile(r"\[数据\]\s*([^\[]+)")
_KEY_VALUE_RE = re.compile(r"[\w\u4e00-\u9fa5]+\s*[=：:]\s*\S+")


def _infer_case_type(case: dict[str, Any]) -> str:
    """若 case_type 为空，根据 title / steps / expected_result 关键词推断。"""
    text = " ".join([
        str(case.get("title") or ""),
        str(case.get("steps") or ""),
        str(case.get("expected_result") or ""),
    ]).lower()
    for ct, keywords in TYPE_KEYWORDS.items():
        if any(kw in text for kw in keywords):
            return ct
    # 默认推断为功能-正向
    return "功能-正向"


def _extract_test_data_from_steps(steps: str) -> str:
    """从 [数据] 标签中提取 test_data。如 '[数据] 用户名=abc，密码=Pwd@1' → 'abc'。"""
    matches = _DATA_TAG_RE.findall(steps)
    return "；".join(m.strip() for m in matches if m.strip())


def score_case(case: dict[str, Any]) -> CaseScore:
    """对单条用例打分（0-100），并给出问题列表。"""
    issues: list[str] = []
    score = 100

    title = str(case.get("title") or "").strip()
    precondition = str(case.get("precondition") or "").strip()
    steps = str(case.get("steps") or "").strip()
    expected = str(case.get("expected_result") or "").strip()
    priority = str(case.get("priority") or "").strip()
    module = str(case.get("module") or "").strip()

    # case_type：原始值为空时，从内容推断
    case_type_raw = str(case.get("case_type") or "").strip()
    case_type = case_type_raw if case_type_raw else _infer_case_type(case)

    # test_data：原始值为空时，尝试从 steps [数据] 标签提取
    test_data_raw = str(case.get("test_data") or "").strip()
    test_data = test_data_raw if test_data_raw else _extract_test_data_from_steps(steps)

    # 从 steps [数据] 标签中提取的内嵌测试数据（用于补足缺失的 test_data 字段）
    steps_data_extracted = _extract_test_data_from_steps(steps)

    field_lengths = {
        "title": len(title), "precondition": len(precondition),
        "steps": len(steps), "expected_result": len(expected),
        "test_data": len(test_data),
        # 记录从 steps 中提取到的数据长度，供 completeness/data_accuracy 评分使用
        "steps_data_extracted": len(steps_data_extracted),
    }

    # title
    if not title:
        score -= 20; issues.append("title 为空")
    elif len(title) < 12:
        score -= 8; issues.append("title 过短(<12)")
    if title and not title.startswith(("验证", "Verify", "verify")):
        score -= 4; issues.append("title 未以'验证'开头")

    # module
    if not module or module in ("通用", "默认", "功能模块1", "功能模块"):
        score -= 8; issues.append("module 为空或占位词")

    # precondition
    if len(precondition) < 20:
        score -= 6; issues.append("precondition 过短(<20)")

    # steps
    sc = _step_count(steps)
    if len(steps) < 80:
        score -= 12; issues.append("steps 过短(<80)")
    if sc < 3:
        score -= 10; issues.append(f"steps 不足 3 步(当前{sc})")
    if not _has_triple_format(steps):
        score -= 10; issues.append("steps 未采用 [操作]/[数据]/[校验] 三段式")

    # expected
    if len(expected) < 40:
        score -= 12; issues.append("expected_result 过短(<40)")
    if expected and any(k in expected for k in NEGATIVE_RESULT_KEYWORDS) and len(expected) < 60:
        score -= 4; issues.append("expected_result 含模糊词('正常/成功')")

    # priority
    if priority not in ("高", "中", "低", "P0", "P1", "P2", "P3"):
        score -= 4; issues.append("priority 非合法值")

    # case_type：原始值为空时用推断值不扣分（仅轻微扣分提示补全）
    if not case_type_raw:
        score -= 3; issues.append(f"case_type 未显式声明（推断为 {case_type}）")
    elif case_type_raw not in CASE_TYPES:
        score -= 4; issues.append(f"case_type 非标准值({case_type_raw})")

    # test_data：优先使用独立字段，若没有但 steps 中有 [数据] 内嵌，视为合格
    effective_test_data = test_data_raw or steps_data_extracted
    if not effective_test_data:
        score -= 8; issues.append("test_data 缺失（steps 中也未找到 [数据] 内嵌值）")
    elif effective_test_data in ("无", "略", "自定义", "参考需求"):
        if case_type in ("数据校验", "边界值", "功能-反向"):
            score -= 6; issues.append("数据相关用例 test_data 不应为'无'")
    elif ("=" not in effective_test_data
          and "：" not in effective_test_data
          and ":" not in effective_test_data):
        score -= 4; issues.append("test_data 未包含字段=值结构")

    score = max(0, min(100, score))
    return CaseScore(
        case_id=case.get("id", ""),
        score=score,
        issues=issues,
        field_lengths=field_lengths,
    )


# ---------------- 整体审计 ----------------

def _coverage_score(types: Counter) -> int:
    covered = sum(1 for t in CASE_TYPES if types.get(t, 0) > 0)
    return int(round(covered / len(CASE_TYPES) * 100))


def _completeness_score(case_scores: list[CaseScore]) -> int:
    if not case_scores:
        return 0
    # test_data 可能在 steps [数据] 中，只要 steps 包含 [数据] 即视为完整
    full = sum(
        1 for cs in case_scores
        if (cs.field_lengths.get("test_data", 0) > 0
            or cs.field_lengths.get("steps_data_extracted", 0) > 0)
        and cs.field_lengths.get("precondition", 0) >= 20
    )
    return int(round(full / len(case_scores) * 100))


def _executability_score(case_scores: list[CaseScore]) -> int:
    if not case_scores:
        return 0
    ok = sum(
        1 for cs in case_scores
        if cs.field_lengths.get("steps", 0) >= 80
        and not any("三段式" in i or "不足 3 步" in i for i in cs.issues)
    )
    return int(round(ok / len(case_scores) * 100))


def _boundary_score(types: Counter, total: int) -> int:
    if total == 0:
        return 0
    boundary = types.get("边界值", 0) + types.get("异常处理", 0) + types.get("数据校验", 0)
    ratio = boundary / total
    # 期望 ≥30%
    return int(round(min(1.0, ratio / 0.30) * 100))


def _data_accuracy_score(case_scores: list[CaseScore]) -> int:
    if not case_scores:
        return 0
    # 若 steps_data_extracted > 0 说明 [数据] 已有具体字段值，视为数据准确
    ok = sum(
        1 for cs in case_scores
        if cs.field_lengths.get("steps_data_extracted", 0) > 0
        or (cs.field_lengths.get("test_data", 0) > 0
            and not any("test_data" in i for i in cs.issues))
    )
    return int(round(ok / len(case_scores) * 100))


def _priority_balance_score(prios: Counter, total: int) -> int:
    if total == 0:
        return 0
    # 容忍 ±15% 偏差
    score = 100
    for level, target in PRIORITY_TARGET.items():
        actual = prios.get(level, 0) / total
        diff = abs(actual - target)
        if diff > 0.15:
            score -= int((diff - 0.15) * 200)
        if actual == 0 and total >= 5:
            score -= 8
    return max(0, min(100, score))


def score_cases(cases: list[dict[str, Any]]) -> CasesAudit:
    case_scores = [score_case(c) for c in cases]
    # case_type：原始值为空时使用推断值，以便正确统计分布
    types = Counter(
        (str(c.get("case_type") or "").strip() or _infer_case_type(c))
        for c in cases
    )
    prios = Counter(str(c.get("priority") or "").strip() for c in cases)
    total = len(cases)

    sub = {
        "coverage": _coverage_score(types),
        "completeness": _completeness_score(case_scores),
        "executability": _executability_score(case_scores),
        "boundary": _boundary_score(types, total),
        "data_accuracy": _data_accuracy_score(case_scores),
        "priority_balance": _priority_balance_score(prios, total),
    }
    weights = {
        "coverage": 0.25, "completeness": 0.20, "executability": 0.20,
        "boundary": 0.15, "data_accuracy": 0.10, "priority_balance": 0.10,
    }
    overall = int(round(sum(sub[k] * w for k, w in weights.items())))

    avg_case_score = round(sum(cs.score for cs in case_scores) / total, 2) if total else 0.0
    weak = [k for k, v in sub.items() if v < 70]
    missing = find_missing_types(types)

    return CasesAudit(
        total=total,
        overall_score=overall,
        average_case_score=avg_case_score,
        sub_scores=sub,
        type_distribution={t: types.get(t, 0) for t in CASE_TYPES},
        priority_distribution={p: prios.get(p, 0) for p in ("高", "中", "低")},
        low_quality_ids=[],  # 由调用方按 threshold 算
        missing_types=missing,
        weak_areas=weak,
        cases=case_scores,
    )


def find_low_quality_ids(audit: CasesAudit, threshold: int = 60) -> list[Any]:
    return [cs.case_id for cs in audit.cases if cs.score < threshold]


def find_missing_types(types: Counter) -> list[str]:
    """缺失的关键 case_type（仅前 5 类视为关键）。"""
    critical = ("功能-正向", "功能-反向", "边界值", "异常处理", "数据校验")
    return [t for t in critical if types.get(t, 0) == 0]


def module_coverage_from_cases(
    cases: list[dict[str, Any]],
    *,
    expected_modules: list[str] | None = None,
) -> dict[str, Any]:
    """按 module 统计覆盖，返回零覆盖模块列表。"""
    modules_in_cases = {
        str(c.get("module") or "").strip()
        for c in cases
        if str(c.get("module") or "").strip()
    }
    zero_coverage: list[str] = []
    if expected_modules:
        for mod in expected_modules:
            mod = str(mod or "").strip()
            if not mod:
                continue
            if not any(mod in cm or cm in mod for cm in modules_in_cases):
                zero_coverage.append(mod)
    return {
        "modules_with_cases": sorted(modules_in_cases),
        "zero_coverage_modules": zero_coverage,
    }


def audit_to_payload(
    audit: CasesAudit,
    *,
    low_threshold: int = 60,
    module_coverage: dict[str, Any] | None = None,
    filled_by_template: list[Any] | None = None,
    blank_ratio: float | None = None,
    pre_supplement_score: int | None = None,
    post_supplement_score: int | None = None,
) -> dict[str, Any]:
    """转成给 API/前端的 dict。"""
    low_ids = find_low_quality_ids(audit, threshold=low_threshold)
    payload = {
        "total": audit.total,
        "overall_score": audit.overall_score,
        "average_case_score": audit.average_case_score,
        "sub_scores": audit.sub_scores,
        "type_distribution": audit.type_distribution,
        "priority_distribution": audit.priority_distribution,
        "missing_types": audit.missing_types,
        "weak_areas": audit.weak_areas,
        "low_threshold": low_threshold,
        "low_quality_ids": low_ids,
        "low_quality_cases": [
            asdict(cs) for cs in audit.cases if cs.case_id in low_ids
        ][:50],
    }
    if module_coverage is not None:
        payload["module_coverage"] = module_coverage
    if filled_by_template:
        payload["filled_by_template"] = filled_by_template
    if blank_ratio is not None:
        payload["expected_result_blank_ratio"] = blank_ratio
    if pre_supplement_score is not None:
        payload["pre_supplement_score"] = pre_supplement_score
    if post_supplement_score is not None:
        payload["post_supplement_score"] = post_supplement_score
    return payload
