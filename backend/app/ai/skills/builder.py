"""SkillPromptBuilder：把 skill 的方法论 + Output Contract + 业务上下文 拼装成 LLM 消息。

设计原则：
- Skill 提供「思考框架 / 角色定位 / 最低覆盖清单」 → system prompt 主体
- 项目内置 Output Contract（JSON Schema / 字段约束 / 禁止行为）
- 业务自定义补充（配置中心 extra_prompt_configs / 项目 overlay）
- 防污染补丁（不要照抄历史用例）→ user-side
- 可选 few-shot 风格示例（带字段映射，防止 LLM 照抄结构）
- Token 预估 + 高阈值告警
- 多语言：根据需求文档语言或显式 lang 参数选择对应语种 skill
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import Any

from loguru import logger

from app.ai.skills.catalog import (
    DEFAULT_SKILL_FOR_ROLE,
    ROLE_ANALYSIS,
    ROLE_GENERATION,
    ROLE_REVIEW,
    ROLE_SUPPLEMENT,
)
from app.ai.skills.loader import SkillBundle, SkillNotFoundError, get_skill_loader, load_skill
from app.core.config import settings


# ---------------------- Output Contracts ----------------------

GENERATION_OUTPUT_CONTRACT = """
【输出契约（必须严格遵守）】
你必须直接返回一个合法的 JSON 对象，**不要**包裹在 markdown 代码块（如 ```json）中，**不要**前言或后语。
JSON 必须严格符合以下结构：
{
  "cases": [
    {
      "id": 101,
      "module": "测试模块名称",
      "title": "验证XX功能在YY条件下的ZZ结果",
      "precondition": "前置条件说明，如无填'无'",
      "steps": "1. 步骤一\\n2. 步骤二\\n3. 步骤三",
      "expected_result": "明确、可校验的预期结果",
      "priority": "高"
    }
  ]
}

【字段约束】
- id：递增整数，从 1 起。
- module：**必填且不能为空**。必须从需求分析的真实业务模块中复用一个具体名称（如"素材工单生成"、"投放分剧配置"），**禁止**"通用"、"默认"、"功能模块1"等占位词。同一业务模块的所有用例必须使用完全相同的 module 字符串。
- title：以"验证"开头，描述具体场景，禁止泛化。
- steps：分行编号步骤，至少 2 步，必须可操作。
- expected_result：必须可观测、可断言，禁止"正常"、"成功"等模糊词。
- priority：**必须按场景重要性区分**：
    * 正向主流程、核心业务路径 → "高"
    * 常见异常分支、字段校验、边界值 → "中"
    * 极端边界、罕见组合、UI 细节 → "低"
  禁止把所有用例都标"中"，合理分布约 30% 高 / 50% 中 / 20% 低。

【覆盖率硬性要求】
- 必须覆盖测试策略中提到的**每一个**功能点 / 子功能 / 异常分支。
- 每个功能点至少包含 **3 条**用例：1 条正向主流程、1 条异常 / 反向、1 条边界 / 数据校验。
- 总用例数应与需求复杂度匹配，**通常不少于 20 条**；复杂需求 50~100 条也属正常。

【禁止行为】
- 不要返回介绍 / 总结 / 统计文字。
- 不要在 JSON 外有任何字符。
- 不要使用 ```json 代码块包裹。
- 不要把多个场景塞进同一条用例。
""".strip()


REVIEW_OUTPUT_CONTRACT = """
【输出契约（必须严格遵守）】
直接返回合法的 JSON 对象，**不要**包裹在 markdown 代码块中，**不要**前言或后语。
**禁止返回 reviewed_cases 字段**——你的职责只是评审，不重写整个用例列表。

JSON 必须严格符合以下结构：
{
  "issues": ["问题描述1", "问题描述2"],
  "suggestions": ["优化建议1", "优化建议2"],
  "missing_scenarios": [
    {
      "module": "模块名（必须与原有模块对应或新增）",
      "scenario": "缺失场景的简短描述",
      "test_point": "具体测试点（一句话）"
    }
  ],
  "quality_score": 85,
  "summary": "整体评审总结（中文，100字以内）"
}

【字段说明】
- issues：发现的问题列表（如缺少并发测试、未覆盖某状态迁移、步骤过粗等）。
- suggestions：改进建议（如何提升用例质量）。
- missing_scenarios：建议补充的具体测试场景，**越完整越好**——会被用于自动补充用例。
- quality_score：0~100。
- summary：整体评价（100字以内）。

【其他】
- 已有用例覆盖充分时 issues / missing_scenarios 可为空数组，但 quality_score 与 summary 必填。
- 不要重复列出已存在的场景。
- 必须用中文。
""".strip()


SUPPLEMENT_OUTPUT_CONTRACT = """
【输出契约（必须严格遵守）】
直接返回合法 JSON 对象，**不要**任何前言、后语或 markdown 包裹：
{
  "cases": [
    {
      "id": 1001,
      "module": "具体业务模块名",
      "title": "验证XX在YY条件下的ZZ结果",
      "precondition": "前置条件，如无填'无'",
      "steps": "1. 步骤一\\n2. 步骤二",
      "expected_result": "可断言的预期结果",
      "priority": "高/中/低"
    }
  ]
}

【硬性要求】
- 评审给的每一个 missing_scenario，**必须**至少生成 1 条用例（理想 1~3 条覆盖正/反/边界）。
- 即使 missing_scenario 与某条已有用例相似，仍要生成更细化的新用例。
- **禁止返回空 cases 数组**。完全没有补充必要时，也至少要生成 1 条用例覆盖第一个 missing_scenario。
- 用例 module 必须填具体业务模块名，不能为空或"通用"。
- 用例 id 从指定起始值递增。
- priority 按场景重要性区分（高/中/低），不要全部"中"。
- 不要总结、不要解释、不要 markdown，只输出 JSON。
""".strip()


CONTAMINATION_GUARD = """
【严格防污染】
1. 必须**只针对**【当前需求测试策略】中描述的业务功能编写用例，禁止引入历史用例中存在但当前需求并不存在的业务术语（如其它项目的模块名、字段名、状态名等）。
2. 历史用例**仅用于参考测试用例的写法 / 颗粒度**，不要复制其业务内容到模块 / 标题 / 步骤。
3. module 字段必须来自【当前需求测试策略】中的真实业务模块，禁止出现"【复用历史经验】"、"参考历史"等前缀。
""".strip()


# ---------------------- 工具函数 ----------------------

def _approx_token_count(text: str) -> int:
    """粗略 token 估算：中文 1 字 ≈ 1 token，英文 ≈ 1/4 字符。"""
    if not text:
        return 0
    cn = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    others = len(text) - cn
    return cn + max(1, others // 4)


def _sanitize_extra_prompt(text: str | None) -> str:
    """对用户/配置中心来源的自定义 prompt 做简单注入防御。"""
    if not text:
        return ""
    s = str(text)
    # 截断超长内容（防止填充上下文）
    max_chars = int(getattr(settings, "QA_SKILL_EXTRA_PROMPT_MAX_CHARS", 4000))
    if len(s) > max_chars:
        s = s[:max_chars] + "...[truncated]"
    # 简单去除明显的 system prompt 注入尝试
    bad = (
        "ignore previous instructions",
        "ignore the above",
        "你之前的指令作废",
        "忽略以上所有",
        "现在你是另一个角色",
    )
    lowered = s.lower()
    if any(b.lower() in lowered for b in bad):
        logger.warning("[skill] extra_prompt 触发注入防御过滤")
        return ""
    return s.strip()


def _detect_lang(text: str | None) -> str:
    """非常粗的语言检测：含中文比例 > 5% → zh，否则 en。"""
    if not text:
        return "zh"
    cn = sum(1 for c in text if "\u4e00" <= c <= "\u9fff")
    return "zh" if cn > max(20, len(text) * 0.05) else "en"


def _resolve_skill_id(role: str, override_skill_id: str | None) -> str:
    if override_skill_id and str(override_skill_id).strip():
        return str(override_skill_id).strip()
    return DEFAULT_SKILL_FOR_ROLE.get(role, "")


# ---------------------- Few-shot 示例提取 ----------------------

# 字段映射：把 awesome-qa-skills 模板字段名翻译到我们的 schema
SCHEMA_FIELD_MAPPING = {
    "test_case_title": "title",
    "preconditions": "precondition",
    "test_steps": "steps",
    "expected_results": "expected_result",
    "P0": "高", "P1": "高", "P2": "中", "P3": "低",
}

FEW_SHOT_GUARD_NOTE = (
    "【风格示例字段映射规则（关键）】\n"
    "- 示例中字段 test_case_title → 我们用 title\n"
    "- 示例中字段 preconditions(数组) → 我们用 precondition(字符串)\n"
    "- 示例中字段 test_steps → 我们用 steps（带编号文本）\n"
    "- 示例中字段 expected_results → 我们用 expected_result\n"
    "- 示例中 priority='P0/P1' → 我们用 priority='高/中/低'\n"
    "**示例只用于学习步骤颗粒度 / 标题命名风格 / 业务建模思路，禁止照搬字段名，禁止把示例里的业务术语带入当前需求！**"
)


def _truncate(text: str, n: int) -> str:
    text = text.strip()
    return text if len(text) <= n else text[:n] + "...[truncated]"


def _pick_example_for_role(
    bundle: SkillBundle,
    role: str,
    *,
    max_chars: int = 1200,
    hint_text: str = "",
) -> str:
    """从 skill examples 里选一个对当前角色最有价值的示例摘要。

    选择策略（优先级从高到低）：
    1. kind 与角色匹配
    2. 与 hint_text 的关键词重合度高（粗略 token 重合）
    3. 长度更接近 max_chars 的 60%（避免太长被截断 / 太短无信息量）
    """
    if not bundle.examples:
        return ""
    role_kind = {
        ROLE_ANALYSIS: "analysis",
        ROLE_GENERATION: "testcase",
        ROLE_REVIEW: "review",
        ROLE_SUPPLEMENT: "testcase",
    }.get(role, "")
    candidates = [ex for ex in bundle.examples if not ex.is_binary and ex.filename.endswith(".md")]
    if not candidates:
        return ""

    hint_tokens: set[str] = set()
    if hint_text:
        for token in hint_text.lower().split():
            t = token.strip("，。、？！?,.!:;\"'()[]{}<>")
            if 2 <= len(t) <= 20:
                hint_tokens.add(t)

    target_len = int(max_chars * 0.6)

    def _score(ex) -> tuple[int, int, int]:
        kind_match = 1 if (role_kind and ex.kind == role_kind) else 0
        overlap = 0
        if hint_tokens:
            content_lower = ex.content.lower()
            overlap = sum(1 for t in hint_tokens if t and t in content_lower)
        length_penalty = -abs(len(ex.content) - target_len)
        return (kind_match, overlap, length_penalty)

    candidates.sort(key=_score, reverse=True)
    chosen = candidates[0]
    return _truncate(chosen.content, max_chars)


# ---------------------- 拼装结果 ----------------------

@dataclass
class BuildResult:
    """builder 输出的完整元信息（替代之前的 (messages, meta) 元组）。"""
    messages: list[dict[str, str]]
    skill_meta: dict[str, Any] = field(default_factory=dict)
    used_fewshot: bool = False
    prompt_tokens_est: int = 0
    over_budget: bool = False

    # 兼容旧调用：result[0] -> messages, result[1] -> skill_meta
    def __iter__(self):
        yield self.messages
        yield self.skill_meta


def _maybe_warn_token_budget(prompt_tokens: int, role: str) -> bool:
    budget = int(getattr(settings, "QA_SKILL_PROMPT_TOKEN_BUDGET", 8000))
    if budget <= 0:
        return False
    if prompt_tokens > budget:
        logger.warning(
            "[skill] role={} prompt_tokens_est={} 超出预算 {}（建议精简 extra_prompt 或换更短 skill）",
            role, prompt_tokens, budget,
        )
        return True
    return False


def _build_system_prompt(
    *,
    role: str,
    output_contract: str,
    skill_id: str | None,
    extra_business_prompt: str | None,
    enable_fewshot: bool,
    lang: str | None,
    fewshot_hint: str = "",
) -> tuple[str, dict[str, Any], bool]:
    """组装 system prompt + 元信息。

    顺序：[Skill 角色定位 + 方法论] → [Few-shot（可选）] → [Output Contract] → [业务自定义]
    """
    final_skill_id = _resolve_skill_id(role, skill_id)
    skill_block = ""
    fewshot_block = ""
    used_fewshot = False
    bundle: SkillBundle | None = None
    skill_meta: dict[str, Any] = {
        "skill_id": "", "loaded": False, "version": "", "lang": "", "content_hash": "",
        "overlays_applied": [],
    }

    if final_skill_id:
        try:
            bundle = load_skill(final_skill_id)
        except SkillNotFoundError as exc:
            logger.warning("[skill] role={} skill_id={} 加载失败 ({})", role, final_skill_id, exc)
            bundle = None

        # 多语言降级：要求 en 但只有 zh 时退化为 zh
        if bundle and lang and bundle.lang and bundle.lang != lang:
            # 尝试找 lang 后缀的兄弟 skill
            sibling_id = f"{final_skill_id}-{lang}"
            try:
                alt = load_skill(sibling_id)
                bundle = alt
                final_skill_id = sibling_id
            except SkillNotFoundError:
                logger.debug("[skill] 无 {} 兄弟 skill，沿用 {}", sibling_id, bundle.lang)

        if bundle:
            skill_meta.update(
                skill_id=bundle.skill_id,
                skill_name=bundle.name,
                description=bundle.description,
                version=bundle.version,
                lang=bundle.lang,
                tags=bundle.tags,
                requires=bundle.requires,
                content_hash=bundle.content_hash,
                overlays_applied=bundle.overlays_applied,
                primary_prompt_file=bundle.primary_prompt_key,
                loaded=True,
            )
            # 依赖 skill 的方法论优先注入（作为辅助 system 段）
            dep_blocks = []
            for dep_id, dep in bundle.dependencies.items():
                if dep.primary_prompt:
                    dep_blocks.append(
                        f"【依赖 Skill: {dep_id} v{dep.version}】\n{dep.primary_prompt.strip()}"
                    )
            if dep_blocks:
                skill_block = "\n\n".join(dep_blocks) + "\n\n" + bundle.primary_prompt.strip()
            else:
                skill_block = bundle.primary_prompt.strip()

            if enable_fewshot and bool(getattr(settings, "QA_SKILL_FEWSHOT_ENABLED", True)):
                example_text = _pick_example_for_role(bundle, role, hint_text=fewshot_hint or "")
                if example_text:
                    fewshot_block = (
                        "【风格参考示例（来自 skill examples，仅供颗粒度/写法参考）】\n"
                        + example_text + "\n\n"
                        + FEW_SHOT_GUARD_NOTE
                    )
                    used_fewshot = True
            logger.debug("[skill] role={} 使用 skill={} v{}", role, bundle.skill_id, bundle.version)

    parts: list[str] = []
    if skill_block:
        parts.append(skill_block)
    if fewshot_block:
        parts.append(fewshot_block)
    parts.append(output_contract)

    safe_extra = _sanitize_extra_prompt(extra_business_prompt)
    if safe_extra:
        parts.append("【业务自定义补充】\n" + safe_extra)

    return "\n\n---\n\n".join(parts), skill_meta, used_fewshot


def _wrap(
    role: str,
    messages: list[dict[str, str]],
    skill_meta: dict[str, Any],
    used_fewshot: bool,
) -> BuildResult:
    total = sum(_approx_token_count(m.get("content") or "") for m in messages)
    over = _maybe_warn_token_budget(total, role)
    skill_meta["prompt_tokens_est"] = total
    skill_meta["over_budget"] = over
    skill_meta["used_fewshot"] = used_fewshot
    return BuildResult(
        messages=messages,
        skill_meta=skill_meta,
        used_fewshot=used_fewshot,
        prompt_tokens_est=total,
        over_budget=over,
    )


# ---------------------- 各 role 专用 builder ----------------------

def build_analysis_messages(
    *,
    text_content: str,
    skill_id: str | None = None,
    extra_business_prompt: str | None = None,
    include_strategy_extension: bool = False,
    enable_fewshot: bool = True,
    lang: str | None = None,
) -> BuildResult:
    """需求分析"""
    if not lang:
        lang = _detect_lang(text_content)

    output_contract = (
        "【输出要求】\n"
        "1. 用清晰的 Markdown 输出（标题分层、要点列表、表格等）。\n"
        "2. 至少覆盖：业务范围、核心功能拆解、关键流程、异常分支、状态机、权限/角色、隐藏逻辑、依赖与风险。\n"
        "3. 突出可测性风险与待澄清的问题，便于后续直接编写测试策略与用例。"
    )
    if include_strategy_extension:
        output_contract += (
            "\n4. 在分析之后，**追加一节《测试策略》**：覆盖正常流程、边界值、异常处理、等价类、"
            "并发与时序、权限、状态机迁移；输出可被下游直接拿去生成用例的颗粒度。"
        )

    system, meta, fs = _build_system_prompt(
        role=ROLE_ANALYSIS,
        output_contract=output_contract,
        skill_id=skill_id,
        extra_business_prompt=extra_business_prompt,
        enable_fewshot=enable_fewshot,
        lang=lang,
        fewshot_hint=text_content[:2000],
    )
    meta["detected_lang"] = lang
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": f"以下是项目文档内容：\n\n{text_content}"},
    ]
    return _wrap(ROLE_ANALYSIS, messages, meta, fs)


def build_generation_messages(
    *,
    design_result: str,
    historical_context: str = "",
    skill_id: str | None = None,
    extra_business_prompt: str | None = None,
    enable_fewshot: bool = True,
    lang: str | None = None,
) -> BuildResult:
    """测试用例生成"""
    if not lang:
        lang = _detect_lang(design_result)
    system, meta, fs = _build_system_prompt(
        role=ROLE_GENERATION,
        output_contract=GENERATION_OUTPUT_CONTRACT,
        skill_id=skill_id,
        extra_business_prompt=extra_business_prompt,
        enable_fewshot=enable_fewshot,
        lang=lang,
        fewshot_hint=design_result[:2000],
    )
    meta["detected_lang"] = lang

    history = (historical_context or "").strip()
    if history:
        user = (
            "【历史相似用例（仅供测试设计风格参考，不得照抄）】\n"
            f"{history}\n\n"
            "【当前需求测试策略】\n"
            f"{design_result}\n\n"
            f"{CONTAMINATION_GUARD}\n\n"
            "请直接返回合法 JSON 对象，包含 cases 数组字段。每条用例必须有非空 steps 与 expected_result。"
        )
    else:
        user = (
            "【当前需求测试策略】\n"
            f"{design_result}\n\n"
            "当前没有历史相似需求可参考，请基于当前策略完整生成测试用例，覆盖正常、异常与边界场景。\n"
            "请直接返回合法 JSON 对象，包含 cases 数组字段。每条用例必须有非空 steps 与 expected_result。"
        )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    return _wrap(ROLE_GENERATION, messages, meta, fs)


def build_review_messages(
    *,
    cases: list[dict[str, Any]],
    analysis: str,
    skill_id: str | None = None,
    extra_business_prompt: str | None = None,
    enable_fewshot: bool = True,
    lang: str | None = None,
) -> BuildResult:
    """测试用例评审"""
    if not lang:
        lang = _detect_lang(analysis)
    system, meta, fs = _build_system_prompt(
        role=ROLE_REVIEW,
        output_contract=REVIEW_OUTPUT_CONTRACT,
        skill_id=skill_id,
        extra_business_prompt=extra_business_prompt,
        enable_fewshot=enable_fewshot,
        lang=lang,
        fewshot_hint=analysis[:2000],
    )
    meta["detected_lang"] = lang
    cases_summary = json.dumps(cases, ensure_ascii=False, indent=2)
    user = (
        "【需求分析结果】：\n"
        f"{analysis}\n\n"
        f"【已生成的测试用例（共 {len(cases)} 条）】：\n"
        f"{cases_summary}"
    )
    messages = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    return _wrap(ROLE_REVIEW, messages, meta, fs)


def build_supplement_messages(
    *,
    analysis: str,
    existing_cases: list[dict[str, Any]],
    missing_scenarios: list[Any],
    next_id: int,
    skill_id: str | None = None,
    extra_business_prompt: str | None = None,
    extra_user_hint: str = "",
    enable_fewshot: bool = False,
    lang: str | None = None,
) -> BuildResult:
    """根据评审 missing_scenarios 补全用例。默认关闭 few-shot（避免再注入更长上下文）。"""
    if not lang:
        lang = _detect_lang(analysis)
    system, meta, fs = _build_system_prompt(
        role=ROLE_SUPPLEMENT,
        output_contract=SUPPLEMENT_OUTPUT_CONTRACT,
        skill_id=skill_id,
        extra_business_prompt=extra_business_prompt,
        enable_fewshot=enable_fewshot,
        lang=lang,
    )
    meta["detected_lang"] = lang
    titles = "\n".join(f"- [{c.get('module','')}] {c.get('title','')}" for c in existing_cases)
    user = (
        f"【需求分析】\n{analysis}\n\n"
        f"【已有用例标题清单（避免重复）】\n{titles}\n\n"
        f"【评审专家指出的缺失场景】\n{json.dumps(missing_scenarios, ensure_ascii=False, indent=2)}\n\n"
        f"请从 id={next_id} 开始递增编号，**只输出新增用例**。"
    )
    msgs = [
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ]
    if extra_user_hint:
        msgs.append({"role": "user", "content": extra_user_hint})
    return _wrap(ROLE_SUPPLEMENT, msgs, meta, fs)
