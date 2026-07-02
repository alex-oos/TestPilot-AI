import json
import re
from typing import List, Dict, Any


def _strip_code_fence(text: str) -> str:
    value = (text or "").strip()
    value = re.sub(r"^```json\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"^```\s*", "", value, flags=re.IGNORECASE)
    value = re.sub(r"\s*```$", "", value)
    return value.strip()


def _extract_json_array_text(text: str) -> str:
    value = _strip_code_fence(text)
    if value.startswith("[") and value.endswith("]"):
        return value

    start = value.find("[")
    if start < 0:
        raise ValueError("未找到 JSON 数组起始符 '['")

    depth = 0
    end = -1
    for i in range(start, len(value)):
        ch = value[i]
        if ch == "[":
            depth += 1
        elif ch == "]":
            depth -= 1
            if depth == 0:
                end = i
                break

    if end < 0:
        raise ValueError("未找到 JSON 数组结束符 ']'")
    return value[start:end + 1]


def _extract_first_json_value_text(text: str) -> str:
    value = _strip_code_fence(text)
    decoder = json.JSONDecoder()
    for i, ch in enumerate(value):
        if ch not in "[{":
            continue
        try:
            _, end = decoder.raw_decode(value[i:])
            return value[i:i + end]
        except Exception:
            continue
    raise ValueError("未找到可解析的 JSON 内容")


def _looks_like_case_obj(item: Any) -> bool:
    if not isinstance(item, dict):
        return False
    keys = set(item.keys())
    expected = {"id", "module", "title", "precondition", "steps", "test_steps", "expected_result", "priority"}
    return bool(keys & expected)


def _find_case_list_deep(data: Any) -> Any:
    if isinstance(data, list):
        if data and any(_looks_like_case_obj(item) for item in data):
            return data
        for item in data:
            found = _find_case_list_deep(item)
            if isinstance(found, list):
                return found
        return data
    if isinstance(data, dict):
        for key in ("test_cases", "cases", "items", "data", "result", "payload", "output"):
            value = data.get(key)
            found = _find_case_list_deep(value)
            if isinstance(found, list):
                return found
        for value in data.values():
            found = _find_case_list_deep(value)
            if isinstance(found, list):
                return found
    return data


def _extract_cases_payload(data: Any) -> Any:
    return _find_case_list_deep(data)


def _parse_cases_payload(text: str) -> List[Dict[str, Any]]:
    try:
        return _normalize_cases(json.loads(_extract_json_array_text(text)))
    except Exception:
        pass

    payload = json.loads(_extract_first_json_value_text(text))
    return _normalize_cases(_extract_cases_payload(payload))


def _extract_review_payload(data: Any) -> Any:
    if isinstance(data, dict):
        if any(key in data for key in ("issues", "suggestions", "missing_scenarios", "quality_score", "summary")):
            return data
        for key in ("review", "result", "data", "payload"):
            value = data.get(key)
            if isinstance(value, dict):
                return value
    return data


def _normalize_review_payload(review: Any) -> Dict[str, Any]:
    if not isinstance(review, dict):
        raise ValueError("评审结果不是对象")

    issues_raw = review.get("issues") or []
    suggestions_raw = review.get("suggestions") or []
    missing_raw = review.get("missing_scenarios") or []

    if not isinstance(issues_raw, list):
        issues_raw = [issues_raw] if issues_raw else []
    if not isinstance(suggestions_raw, list):
        suggestions_raw = [suggestions_raw] if suggestions_raw else []
    if not isinstance(missing_raw, list):
        missing_raw = [missing_raw] if missing_raw else []

    issues = [str(x).strip() for x in issues_raw if str(x).strip()]
    suggestions = [str(x).strip() for x in suggestions_raw if str(x).strip()]
    missing_scenarios: List[Dict[str, str]] = []
    for item in missing_raw:
        if isinstance(item, dict):
            missing_scenarios.append(
                {
                    "module": str(item.get("module") or "").strip(),
                    "scenario": str(item.get("scenario") or "").strip(),
                    "test_point": str(item.get("test_point") or "").strip(),
                }
            )
        else:
            text = str(item).strip()
            if text:
                missing_scenarios.append({"module": "", "scenario": text, "test_point": ""})

    try:
        quality_score = int(float(review.get("quality_score", 0)))
    except Exception:
        quality_score = 0
    quality_score = max(0, min(100, quality_score))

    summary = str(review.get("summary") or "").strip()
    if not summary:
        summary = "评审已完成。"

    reviewed_cases: List[Dict[str, Any]] = []
    raw_reviewed_cases = review.get("reviewed_cases")
    if isinstance(raw_reviewed_cases, list):
        try:
            reviewed_cases = _normalize_cases(raw_reviewed_cases)
        except Exception:
            reviewed_cases = []

    sub_scores_raw = review.get("sub_scores") or {}
    sub_scores: Dict[str, int] = {}
    if isinstance(sub_scores_raw, dict):
        for k in ("coverage", "completeness", "executability", "boundary", "data_accuracy", "priority_balance"):
            try:
                sub_scores[k] = max(0, min(100, int(float(sub_scores_raw.get(k, 0)))))
            except Exception:
                sub_scores[k] = 0

    type_distribution_raw = review.get("type_distribution") or {}
    type_distribution: Dict[str, int] = {}
    if isinstance(type_distribution_raw, dict):
        for k, v in type_distribution_raw.items():
            try:
                type_distribution[str(k)] = int(v)
            except Exception:
                continue

    normalized_review = {
        "issues": issues,
        "suggestions": suggestions,
        "missing_scenarios": missing_scenarios,
        "quality_score": quality_score,
        "sub_scores": sub_scores,
        "type_distribution": type_distribution,
        "summary": summary,
    }
    if reviewed_cases:
        normalized_review["reviewed_cases"] = reviewed_cases
    return normalized_review


def _parse_review_payload(text: str) -> Dict[str, Any]:
    payload = json.loads(_extract_first_json_value_text(text))
    return _normalize_review_payload(_extract_review_payload(payload))


def _normalize_cases(cases: Any) -> List[Dict[str, Any]]:
    if not isinstance(cases, list):
        raise ValueError("LLM 返回内容不是数组")

    def _normalize_title(raw_title: str, idx: int) -> str:
        title = str(raw_title or "").strip()
        if not title:
            title = f"验证功能点{idx}"
        if not title.startswith("验证"):
            title = re.sub(r"^[：:：\-—_\s]+", "", title)
            title = f"验证{title}"
        return title

    def _derive_module(raw_module: str, title: str, steps: str, idx: int) -> str:
        module = str(raw_module or "").strip()
        if module and module not in {"通用", "默认", "general", "General", "默认模块", "未分类"}:
            return module

        clean_title = re.sub(r"^验证[：:\s]*", "", str(title or "").strip())
        for sep in ["-", "—", "–", "－", "_"]:
            if sep in clean_title:
                head = clean_title.split(sep, 1)[0].strip()
                if 2 <= len(head) <= 30:
                    return head
        for sep in ["在", "时", "下", "前", "后", "中", "对", "进行"]:
            pos = clean_title.find(sep)
            if 2 <= pos <= 30:
                head = clean_title[:pos].strip()
                if head:
                    return head

        text = f"{title}\n{steps}"
        mapping = [
            ("灰度", "灰度控制"),
            ("白名单", "灰度白名单"),
            ("广告策略", "广告策略模板"),
            ("展示位", "展示位配置"),
            ("广告单元", "广告单元配置"),
            ("漏斗", "漏斗分析"),
            ("收益", "收益分析"),
            ("用户分析", "用户分析"),
            ("ab", "AB Test"),
            ("看板", "数据看板"),
            ("导出", "导出能力"),
            ("权限", "权限与角色"),
        ]
        lower = text.lower()
        for keyword, module_name in mapping:
            if keyword in lower:
                return module_name
        if 2 <= len(clean_title) <= 20:
            return clean_title
        return "默认模块"

    normalized: List[Dict[str, Any]] = []
    for idx, item in enumerate(cases, start=1):
        if not isinstance(item, dict):
            continue
        raw_steps = item.get("steps")
        if not raw_steps:
            raw_steps = item.get("test_steps")
        if isinstance(raw_steps, list):
            raw_steps = "\n".join([str(s).strip() for s in raw_steps if str(s).strip()])
        elif raw_steps is None:
            raw_steps = ""
        raw_expected = (
            item.get("expected_result")
            or item.get("expected")
            or item.get("expectedResult")
            or item.get("expected_results")
            or item.get("result")
            or item.get("assertion")
        )
        if isinstance(raw_expected, list):
            raw_expected = "\n".join([str(s).strip() for s in raw_expected if str(s).strip()])
        elif raw_expected is None:
            raw_expected = ""
        raw_id = item.get("id")
        try:
            case_id = int(raw_id)
        except Exception:
            case_id = idx
        title = _normalize_title(str(item.get("title") or ""), idx)
        steps = str(raw_steps or "")
        module = _derive_module(str(item.get("module") or ""), title, steps, idx)
        normalized.append(
            {
                "id": case_id,
                "module": module,
                "title": title,
                "precondition": str(item.get("precondition") or "无"),
                "steps": steps,
                "expected_result": str(raw_expected or ""),
                "priority": str(item.get("priority") or "中"),
                "case_type": str(item.get("case_type") or "").strip(),
                "test_data": str(item.get("test_data") or "").strip(),
            }
        )

    if not normalized:
        raise ValueError("LLM 返回数组为空或字段无效")
    return normalized


def _count_blank_case_fields(cases: List[Dict[str, Any]]) -> Dict[str, int]:
    blank_steps = sum(1 for c in cases if not str(c.get("steps") or "").strip())
    blank_expected = sum(1 for c in cases if not str(c.get("expected_result") or "").strip())
    short_steps = sum(1 for c in cases if len(str(c.get("steps") or "").strip()) < 60)
    return {
        "total": len(cases),
        "blank_steps": blank_steps,
        "blank_expected": blank_expected,
        "short_steps": short_steps,
    }


def _needs_case_repair(cases: List[Dict[str, Any]]) -> bool:
    stats = _count_blank_case_fields(cases)
    total = max(1, stats["total"])
    if (stats["blank_steps"] / total) > 0.4:
        return True
    if (stats["blank_expected"] / total) > 0.4:
        return True
    # 步骤过粗：>30% 用例 steps 过短
    if (stats["short_steps"] / total) > 0.3:
        return True
    return False


_TYPE_INFER_RULES = (
    # 顺序：从特定到一般。title 命中优先于 expected/steps。
    ("并发/时序", ("并发", "竞态", "重复提交", "幂等", "时序")),
    ("性能/容量", ("性能", "qps", "tps", "压测", "稳定性")),
    ("权限/角色", ("权限", "角色", "未登录", "越权", "鉴权")),
    ("兼容/UI",  ("兼容", "浏览器", "分辨率", "样式", "国际化")),
    ("数据校验", ("校验", "格式", "正则", "非法字符")),
    ("边界值",   ("最大", "最小", "上限", "下限", "极值", "边界")),
    ("功能-反向", ("失败", "错误", "拒绝", "无效", "不存在", "缺少")),
    ("异常处理", ("超时", "断网", "中断", "宕机", "崩溃")),  # 不含'异常'，避免默认 expected 误命中
)


def _infer_case_type(title: str, expected: str, steps: str = "") -> str:
    title_l = (title or "").lower()
    full_l = f"{title} {expected} {steps}".lower()
    # title 命中优先（避免默认填充文本污染）
    for ct, kws in _TYPE_INFER_RULES:
        if any(kw.lower() in title_l for kw in kws):
            return ct
    for ct, kws in _TYPE_INFER_RULES:
        if any(kw.lower() in full_l for kw in kws):
            return ct
    return "功能-正向"


def _fill_case_blanks(cases: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    patched: List[Dict[str, Any]] = []
    for case in cases:
        item = dict(case)
        if not str(item.get("steps") or "").strip():
            item["steps"] = (
                "1. [操作] 进入对应功能页面/接口；[数据] 使用前置条件中的账号与数据；[校验] 页面/接口正常加载。\n"
                "2. [操作] 执行该用例对应的核心动作；[数据] 输入主要业务字段；[校验] 系统返回符合预期。\n"
                "3. [操作] 检查关联数据/状态；[数据] 关注影响范围内的字段；[校验] 状态机/数据库变化符合需求。"
            )
        if not str(item.get("expected_result") or "").strip():
            item["expected_result"] = (
                "系统返回成功状态，对应业务字段更新到数据库；前端 UI 显示对应结果文案，不出现异常报错与白屏。"
            )
        if len(str(item.get("precondition") or "").strip()) < 5:
            item["precondition"] = "测试账号已登录且具有对应业务权限；前置数据按需求文档准备完毕。"
        if not str(item.get("case_type") or "").strip():
            item["case_type"] = _infer_case_type(
                str(item.get("title") or ""),
                str(item.get("expected_result") or ""),
                str(item.get("steps") or ""),
            )
        if not str(item.get("test_data") or "").strip():
            item["test_data"] = "无"
        patched.append(item)
    return patched
