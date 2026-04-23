"""Golden 回归测试：固定输入 → 关键 system prompt 段必须出现 + token 区间合规。

直接 `python tests/test_skills_golden.py` 即可。

不调用 LLM，仅断言 builder 拼装结果。用于：
- skill 内容变更后的回归
- 升级 awesome-qa-skills 时的内容比对
- CI 中 fail-fast
"""

from __future__ import annotations

import os
import sys

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


def section(title: str) -> None:
    print(f"\n=== {title} ===")


from app.ai.skills.builder import (
    build_analysis_messages,
    build_generation_messages,
    build_review_messages,
    build_supplement_messages,
    GENERATION_OUTPUT_CONTRACT,
    REVIEW_OUTPUT_CONTRACT,
)
from app.ai.skills.loader import get_skill_loader


# ---- 固定 Golden 输入 ----
GOLDEN_REQUIREMENT = """\
【需求】用户登录模块改造
- 支持手机号 + 短信验证码登录
- 增加图形验证码防刷（错误 3 次后弹出）
- 60 秒短信发送频控
- 与现有 OAuth2 登录共存
"""

GOLDEN_STRATEGY = """\
## 测试策略
1. 正向：手机号格式正确 + 验证码正确 → 登录成功
2. 异常：错误验证码 / 过期 / 不存在用户
3. 边界：60 秒频控；3 次错误后图形验证码
4. 兼容：与 OAuth2 并存，互不影响
5. 安全：防止短信轰炸；图形验证码不可被脚本绕过
"""

GOLDEN_CASES = [
    {"id": 1, "module": "登录", "title": "验证手机号正确且验证码正确时登录成功",
     "precondition": "无", "steps": "1. 输入手机号\n2. 获取验证码\n3. 提交",
     "expected_result": "返回 200 且 token 有效", "priority": "高"},
    {"id": 2, "module": "登录", "title": "验证错误验证码登录失败",
     "precondition": "无", "steps": "1. 输入手机号\n2. 输入错误验证码\n3. 提交",
     "expected_result": "返回 4xx 且不下发 token", "priority": "中"},
]


# ---------------- 1. analysis ----------------
section("1. analysis builder：固定输入 → 关键段")
ar = build_analysis_messages(text_content=GOLDEN_REQUIREMENT)
sys_a = ar.messages[0]["content"]
check("system role 是 system", ar.messages[0]["role"] == "system")
check("user 段包含原始需求", GOLDEN_REQUIREMENT.strip() in ar.messages[1]["content"])
check("system 段包含【输出要求】", "【输出要求】" in sys_a)
check("system 段包含覆盖类目", "异常分支" in sys_a or "状态机" in sys_a)
check("token 估算 > 0", ar.prompt_tokens_est > 0)
check("token 估算 < 4000（轻量需求）", ar.prompt_tokens_est < 4000,
      f"实际={ar.prompt_tokens_est}")
check("skill_meta 含 detected_lang", ar.skill_meta.get("detected_lang") in ("zh", "en"))


# ---------------- 2. generation ----------------
section("2. generation builder：固定策略 → 关键段")
gr = build_generation_messages(design_result=GOLDEN_STRATEGY, historical_context="")
sys_g = gr.messages[0]["content"]
user_g = gr.messages[1]["content"]
check("system 段包含 GENERATION_OUTPUT_CONTRACT 关键字段约束", "【字段约束】" in sys_g)
check("system 段包含覆盖率硬性要求", "覆盖率硬性要求" in sys_g)
check("system 段包含 priority 三级要求", '"高"' in sys_g and '"中"' in sys_g and '"低"' in sys_g)
check("user 段包含策略全文", "测试策略" in user_g)
check("user 段提示直接返回 JSON", "JSON" in user_g or "json" in user_g)
check("token 估算合理（<10k）", gr.prompt_tokens_est < 10000,
      f"实际={gr.prompt_tokens_est}")


# ---------------- 3. review ----------------
section("3. review builder：固定用例 → 关键段")
rr = build_review_messages(cases=GOLDEN_CASES, analysis="登录模块改造")
sys_r = rr.messages[0]["content"]
user_r = rr.messages[1]["content"]
check("system 段包含 REVIEW_OUTPUT_CONTRACT", "missing_scenarios" in sys_r)
check("system 段强调禁止 reviewed_cases", "reviewed_cases" in sys_r)
check("user 段包含已生成用例数量", "共 2 条" in user_r or "(共 2 条)" in user_r or "共 2" in user_r)
check("user 段包含 case title", "手机号正确" in user_r)


# ---------------- 4. supplement ----------------
section("4. supplement builder：固定缺失场景 → 关键段")
sr = build_supplement_messages(
    analysis="登录模块改造",
    existing_cases=GOLDEN_CASES,
    missing_scenarios=[{"module": "登录", "scenario": "短信轰炸防护",
                        "test_point": "60 秒内重复请求拒绝"}],
    next_id=10,
)
sys_s = sr.messages[0]["content"]
user_s = sr.messages[1]["content"]
check("system 段含 SUPPLEMENT_OUTPUT_CONTRACT", "cases" in sys_s and "module" in sys_s)
check("user 段含 next_id 提示", "id=10" in user_s or "id=10" in user_s.replace(" ", ""))
check("user 段含已有用例标题清单", "登录" in user_s)
check("supplement few-shot 默认关闭", sr.used_fewshot is False or sr.used_fewshot is None)


# ---------------- 5. 健康检查 ----------------
section("5. health 检查：所有 skill 必须 OK")
from app.ai.skills.health import run_health_check
report = run_health_check()
check("health 报告 ok", report.ok, f"failed={report.failed} role_issues={report.role_mapping_issues}")
check("至少 4 个 skill", report.total >= 4, f"实际={report.total}")
check("零角色映射问题", len(report.role_mapping_issues) == 0,
      f"issues={report.role_mapping_issues}")


# ---------------- 6. 依赖注入 ----------------
section("6. requires 依赖：测试 _load_uncached 不会爆栈")
loader = get_skill_loader()
for sid in loader.list_available():
    try:
        b = loader.load(sid)
        check(f"{sid} 加载成功", True)
    except Exception as e:
        check(f"{sid} 加载成功", False, str(e))
        break


# ---------------- 汇总 ----------------
print(f"\n=== Golden 回归结果 ===")
print(f"通过 {PASS} / 失败 {FAIL}")
sys.exit(0 if FAIL == 0 else 1)
