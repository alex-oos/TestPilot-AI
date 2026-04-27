"""quality_gate 评分模块单元测试。

直接 `python tests/test_quality_gate.py` 即可。
26+ 断言覆盖：
- 单条用例打分（合格 / 不合格）
- 整体评分（sub_scores / overall_score / type_distribution）
- 优先级平衡评分
- 缺失类型识别
- parsers._fill_case_blanks 集成
"""

from __future__ import annotations

import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


PASS = 0
FAIL = 0


def check(name: str, cond: bool, detail: str = "") -> None:
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✓ {name}")
    else:
        FAIL += 1
        print(f"  ✗ {name}  -- {detail}")


def section(t: str) -> None:
    print(f"\n=== {t} ===")


from app.ai import quality_gate as qg
from app.ai.parsers import _fill_case_blanks, _needs_case_repair


GOOD_CASE = {
    "id": 101,
    "module": "用户登录",
    "title": "验证手机号正确且短信验证码正确时登录成功并返回 token",
    "precondition": "测试账号 13800000001 已注册；图形验证码服务可用；当前 60s 内未发送过短信",
    "steps": (
        "1. [操作] 在登录页输入手机号；[数据] phone=13800000001；[校验] 页面接收输入并启用'获取验证码'按钮\n"
        "2. [操作] 点击'获取验证码'；[数据] 接口 POST /sms/send；[校验] 响应 200 且数据库 sms_codes 表有记录\n"
        "3. [操作] 输入收到的验证码并提交；[数据] code=数据库最新值；[校验] 返回 200，body.token 非空\n"
        "4. [操作] 用 token 调用 /me；[数据] header Authorization=Bearer <token>；[校验] 返回当前用户信息"
    ),
    "expected_result": "登录接口返回 HTTP 200 且 body.token 非空；后续 /me 接口能用 token 解析出用户 id；登录日志表新增一条 status=success 记录。",
    "priority": "高",
    "case_type": "功能-正向",
    "test_data": "phone=13800000001; code=<动态获取>",
}

BAD_CASE = {
    "id": 9999,
    "module": "通用",
    "title": "登录测试",
    "precondition": "无",
    "steps": "点击登录",
    "expected_result": "正常",
    "priority": "中",
}


# ---------------- 1. 单条评分 ----------------
section("1. 单条评分")
sg = qg.score_case(GOOD_CASE)
sb = qg.score_case(BAD_CASE)
check("good case 评分 ≥85", sg.score >= 85, f"实际={sg.score} issues={sg.issues}")
check("good case issues 几乎为空", len(sg.issues) <= 1, str(sg.issues))
check("bad case 评分 <50", sb.score < 50, f"实际={sb.score}")
check("bad case 命中 title 过短", any("title" in i for i in sb.issues))
check("bad case 命中 module 占位", any("module" in i for i in sb.issues))
check("bad case 命中 steps 过短", any("steps 过短" in i for i in sb.issues))
check("bad case 命中 expected 模糊", any("expected" in i for i in sb.issues))
check("bad case 命中 case_type 缺失", any("case_type" in i for i in sb.issues))


# ---------------- 2. 整体审计 ----------------
section("2. 整体审计 score_cases")
batch = [GOOD_CASE]
# 多复制几个变体，凑出 9 类
for ct in ("功能-反向", "边界值", "异常处理", "权限/角色", "并发/时序", "数据校验", "兼容/UI", "性能/容量"):
    c = dict(GOOD_CASE)
    c["id"] = c["id"] + len(batch)
    c["case_type"] = ct
    c["priority"] = "中" if ct not in ("功能-反向",) else "高"
    batch.append(c)
batch.append(BAD_CASE)

audit = qg.score_cases(batch)
check("total 等于输入条数", audit.total == len(batch), str(audit.total))
check("overall_score 为整数", isinstance(audit.overall_score, int))
check("overall_score 0~100", 0 <= audit.overall_score <= 100, str(audit.overall_score))
check("sub_scores 6 维全在", set(audit.sub_scores.keys()) == {
    "coverage", "completeness", "executability", "boundary", "data_accuracy", "priority_balance"
})
check("coverage = 100（已含 9 类）", audit.sub_scores["coverage"] == 100)
check("type_distribution 包含全部 9 类 key",
      all(t in audit.type_distribution for t in qg.CASE_TYPES))
check("priority_distribution 高/中/低 key 齐",
      set(audit.priority_distribution.keys()) == {"高", "中", "低"})
check("low_quality_ids 默认空（由调用方算）", audit.low_quality_ids == [])

low_ids = qg.find_low_quality_ids(audit, threshold=60)
check("低分用例包含 BAD_CASE id", BAD_CASE["id"] in low_ids, str(low_ids))


# ---------------- 3. priority_balance 函数 ----------------
section("3. priority_balance 评分")
balanced = Counter({"高": 3, "中": 5, "低": 2})  # 30/50/20 完美
unbalanced = Counter({"高": 0, "中": 10, "低": 0})  # 全中
score_balanced = qg._priority_balance_score(balanced, sum(balanced.values()))
score_unbalanced = qg._priority_balance_score(unbalanced, sum(unbalanced.values()))
check("balanced 得分 ≥90", score_balanced >= 90, str(score_balanced))
check("unbalanced 得分 ≤60", score_unbalanced <= 60, str(score_unbalanced))


# ---------------- 4. 缺失类型识别 ----------------
section("4. find_missing_types")
types_partial = Counter({"功能-正向": 5, "边界值": 1})
miss = qg.find_missing_types(types_partial)
check("缺失 '功能-反向'", "功能-反向" in miss)
check("缺失 '异常处理'", "异常处理" in miss)
check("不缺失 '功能-正向'", "功能-正向" not in miss)


# ---------------- 5. parsers._fill_case_blanks 集成 ----------------
section("5. _fill_case_blanks 自动填补 case_type/test_data")
filled = _fill_case_blanks([
    {"id": 1, "title": "验证错误密码登录失败", "module": "登录"},
    {"id": 2, "title": "验证最大长度边界", "module": "用户名"},
    {"id": 3, "title": "验证并发提交订单", "module": "订单"},
])
check("空 case 也能被填补 steps", all(len(c.get("steps") or "") >= 80 for c in filled))
check("空 case 也能被填补 expected", all(len(c.get("expected_result") or "") >= 40 for c in filled))
check("test_data 默认填'无'", all(c.get("test_data") for c in filled))
check("case_type 自动推断: '失败' → 功能-反向",
      filled[0]["case_type"] == "功能-反向", filled[0]["case_type"])
check("case_type 自动推断: '最大' → 边界值",
      filled[1]["case_type"] == "边界值", filled[1]["case_type"])
check("case_type 自动推断: '并发' → 并发/时序",
      filled[2]["case_type"] == "并发/时序", filled[2]["case_type"])


# ---------------- 6. _needs_case_repair 阈值 ----------------
section("6. _needs_case_repair 三种触发条件")
short_steps = [{"id": i, "title": "x", "steps": "1. click", "expected_result": "ok"} for i in range(10)]
check("步骤过粗触发 repair", _needs_case_repair(short_steps) is True)
empty_expected = [{"id": i, "title": "x", "steps": "1. " + "a" * 100, "expected_result": ""} for i in range(10)]
check("expected 大量为空触发 repair", _needs_case_repair(empty_expected) is True)
ok_cases = [
    {"id": i, "title": "验证 x", "steps": "1. " + "a" * 60 + "\n2. " + "b" * 60,
     "expected_result": "abc " * 20} for i in range(10)
]
check("正常用例不触发 repair", _needs_case_repair(ok_cases) is False)


# ---------------- 7. audit_to_payload ----------------
section("7. audit_to_payload 输出契约")
payload = qg.audit_to_payload(audit, low_threshold=60)
check("payload 含 overall_score", "overall_score" in payload)
check("payload 含 sub_scores", "sub_scores" in payload and len(payload["sub_scores"]) == 6)
check("payload 含 low_quality_cases 列表", isinstance(payload["low_quality_cases"], list))
check("payload 含 missing_types", "missing_types" in payload)


if __name__ == "__main__":
    print(f"\n=== quality_gate 测试结果 ===")
    print(f"通过 {PASS} / 失败 {FAIL}")
    sys.exit(0 if FAIL == 0 else 1)
else:
    def test_quality_gate_all() -> None:
        assert FAIL == 0, f"quality_gate 测试失败 {FAIL} 项"
