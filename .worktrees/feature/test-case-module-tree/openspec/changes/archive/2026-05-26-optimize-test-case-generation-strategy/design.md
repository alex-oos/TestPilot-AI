## Context

### 当前架构

```
需求文档 → KB 入库（正式 task）+ 多阶段历史检索（analysis / strategy / generation）
    → Phase 1: analyze_requirements (+ KB 模块参考)
    → Phase 1b: design_test_strategy (+ KB 覆盖密度参考)
    → Phase 2: generate_test_cases (+ KB 风格/颗粒度；分批时 module 级检索)
         → rerank(MMR) → JSON 修复 → 空白字段补全 → quality_gate
    → Phase 3: review（按需）→ supplement
    → manual_review 采纳 → ingest adopted + task_summary
    → Pipeline: expected_result 空白率硬阻断
```

### 主要痛点（来自代码与 prompt 约束分析）

| 痛点 | 根因 | 现有缓解 | 不足 |
|------|------|----------|------|
| 复杂需求用例偏少/截断 | 单次 LLM 调用输出 token 上限 | max_tokens bump、JSON repair | 无法保证每个测试点都有对应用例 |
| 策略颗粒度不稳定 | `design_test_strategy` 复用分析 Skill | strategy_extension 追加《测试策略》节 | 输出非结构化，无法机器校验覆盖 |
| case_type 9 类覆盖不全 | 生成 prompt 仅文字约束 | quality_gate 统计 missing_types | 仅打分不重生成缺失类型 |
| 历史 KB 价值有限 | history 仅注入 generate；600 字截断 | CONTAMINATION_GUARD 防污染 | 分析/策略不用 KB；无 case_type metadata；rerank 空实现 |
| 路由时机偏晚 | `route_by_keywords` 只看 design 前 6k | skill_tags 联合路由 | 未在策略阶段影响测试方法选择 |
| 评审补全滞后 | supplement 在 review 末尾 | missing_scenarios 驱动 | 大量补全说明生成阶段已漏测 |
| 长文档上下文丢失 | `_truncate_for_llm` 硬截断 32k/12k | llm_guardrails 标记 truncated | 尾部模块/异常分支被截掉 |
| KB 数据与检索缺陷 | rerank 空实现；瞬态 task 孤儿入库 | 仅召回 adopted_test_case | 无 task_summary；无模块级检索；双轨 SQL/KB 未打通 |
| 三条生成路径不一致 | pipeline / stream / legacy 各自调用 ai.py | 无 | 新能力无法全入口生效 |
| 兜底模板掩盖低质量 | `_fill_case_blanks` 填通用 steps/expected | quality_gate 后续可重写 | 模板用例仍可能通过粗检 |
| 评审成本固定偏高 | 无论质量分高低都跑全量 review | enable_ai_review 总开关 | 高质量集浪费 token 与时间 |
| 补全后无再验证 | supplement 合并后直接进 manual_review | 无 | 补全用例质量未知 |

### 约束

- 保持现有 pipeline 四阶段 UI 与 task_manager phase 结构，避免前端大改
- 默认行为向后兼容：可通过配置关闭结构化策略/分批生成
- 不引入新外部依赖；继续基于现有 Skill loader + quality_gate 规则引擎
- LLM 调用次数会增加（分批），需有 batch 上限与超时保护

## Goals / Non-Goals

**Goals:**

1. 测试策略输出**结构化 JSON**（模块、测试点、case_type 要求、最少用例数），作为生成的唯一权威输入
2. 用例生成改为**覆盖驱动分批**（按 module 或 test_point batch），生成后**自动覆盖校验**
3. 缺失测试点/缺失 case_type 触发**定向补全**（生成阶段完成，减少 review 负担）
4. 产出**覆盖追溯矩阵**写入 generation phase payload
5. 策略阶段启用独立 **test-strategy** Skill；路由结果写入 skill_audit 供观测
6. 长文档与历史 KB 优化，减少截断丢上下文、提升冷启动质量
7. 评审按需触发 + 补全后再评分，降低无效 LLM 调用
8. pipeline / stream / legacy 三入口共用同一生成内核
9. 知识库全链路增强：多阶段注入、结构化入库、真实 rerank、模块级召回、数据治理

**Non-Goals:**

- 不在本变更中替换 LLM 模型或引入 Agent 框架重构
- 不改造前端覆盖矩阵可视化（仅预留 API 字段）
- 不实现 LLM 版 discover-testing 重路由（保留关键词+tags，后续迭代）
- 不改变人工审核（manual_review）流程
- 人工采纳反馈训练闭环（learn from adoptions）留二期

## Decisions

### D1: 结构化策略 Schema

**决策**：定义 `TestStrategyV1` JSON schema，作为 `design_test_strategy` 的主输出（Markdown 摘要可选附加）。

```json
{
  "version": "1",
  "modules": [
    {
      "name": "素材工单生成",
      "risk_level": "高",
      "test_points": [
        {
          "id": "TP-001",
          "title": "正常创建工单",
          "case_types_required": ["功能-正向"],
          "min_cases": 1,
          "priority_hint": "高"
        }
      ]
    }
  ],
  "global_requirements": {
    "min_total_cases": 20,
    "required_case_types": ["功能-正向", "功能-反向", "边界值", "异常处理", "数据校验"]
  }
}
```

**理由**：机器可校验、可分批、可追溯到 case_id。

**备选**：继续 Markdown + 正则解析 → 脆弱且难维护，**拒绝**。

### D2: 分批生成策略

**决策**：按 `module` 分批调用 `generate_test_cases_batch()`，每批 user prompt 仅含该 module 的 test_points + 全局约束；批间合并去重（title 相似度 + module 相同则保留高分）。

**默认 batch 大小**：1 module/批；模块内 test_point > 15 时拆 sub-batch。

**上限**：`GENERATION_MAX_BATCHES=20`，超出则合并小模块。

**理由**：降低单次输出压力，提升大需求覆盖率。

**备选**：按 case_type 分批 → 模块上下文丢失，**不采用**。

### D3: 独立 test-strategy Skill

**决策**：`design_test_strategy` 默认绑定 `test-strategy-plus`（或 `test-strategy`），输出 JSON；analysis 阶段不再追加 strategy_extension（或仅作 human-readable 摘要）。

**降级**：Skill 不可用时 fallback 到现有 analysis+extension，并尝试 `_markdown_strategy_to_v1()` 启发式转换。

### D4: 覆盖校验与定向补全

**决策**：新增 `coverage_planner.py`：

1. `build_coverage_matrix(strategy, cases)` → `{test_point_id: [case_ids], uncovered: [...]}`
2. `find_missing_case_types(strategy, cases)` → 对比 global + per-point case_types_required
3. 若有 uncovered / missing_types → 调用 `supplement_cases_for_gaps()`（复用 `build_supplement_messages` 逻辑，输入为结构化 gap 列表）

**触发时机**：在 `generate_test_cases` 内部、quality_gate 之前；quality_gate 之后可再跑一轮（可配置 `COVERAGE_REFINE_ROUNDS=1`）。

### D5: 质量门禁增强

**决策**：扩展 `quality_gate.score_cases` 返回 `module_coverage`（有/无正向用例的模块列表）；`_apply_quality_gate` 除低分重写外，若 `missing_types` 非空且 `QUALITY_GATE_TYPE_SUPPLEMENT_ENABLED=true`，追加一次类型定向补全。

**理由**：现有门禁只修单条质量，不修系统性类型缺失。

### D6: 路由增强

**决策**：在 `analyze_requirements` 完成后调用 `route_combined(analysis[:8000])`，结果存入 `analysis_payload.routing`；`design_test_strategy` 与 `generate_test_cases` 读取该路由，避免重复计算。复合类型（如 API+安全）取 primary + secondary skill overlay。

**暂不启用** LLM discover-testing（成本高），保留 `QA_SKILL_DISCOVER_LLM=false`。

### D7: Pipeline 产物扩展

**决策**：`generation_payload` 新增 optional 字段：

```python
{
  "coverage_matrix": {...},
  "strategy_version": "1",
  "generation_mode": "batched" | "legacy",
  "batch_stats": [{"module": "...", "cases": 12, "duration_ms": 3400}],
  "quality_audit": {...}  # 已有 quality_gate API 结构
}
```

### D8: 长文档智能压缩

**决策**：新增 `context_compressor.py`，在 `_truncate_for_llm` 之前尝试：

1. 若文档含 Markdown 标题，按 H2/H3 切分模块，优先保留「功能/流程/接口/权限/异常」相关章节
2. 策略输入优先使用结构化 analysis 模块列表 + 各模块摘要，而非 raw 全文截断
3. 仍超限则 fallback 现有 char 截断，并在 payload 标记 `compression_mode: heading|summary|hard_truncate`

**理由**：当前 `LLM_MAX_ANALYSIS_CHARS_FOR_STRATEGY=12000` 硬切常丢掉尾部模块。

### D9: 历史 KB 结构化检索

**决策**：扩展 `build_generation_history_context()`：

- 检索命中时，若 metadata 含 `modules` / `case_count` / `case_types`，一并注入「历史覆盖参考」段
- 入库时（`ingest_requirement_document` 后）可选写入模块清单与 case_type 分布摘要
- 仍保留 CONTAMINATION_GUARD，历史仅作**颗粒度与覆盖密度**参考，禁止照搬业务术语

### D10: 生成前用例量预估

**决策**：从 TestStrategyV1 计算：

```python
expected_min_cases = sum(tp.min_cases for tp in all_test_points)
expected_min_cases = max(expected_min_cases, global.min_total_cases)
```

生成后若 `len(cases) < expected_min_cases * 0.8`，触发一轮「缺口模块」定向补全（不等 review）。

### D11: 评审按需触发（Review Gating）

**决策**：pipeline Phase 3 增加条件：

| 条件 | 行为 |
|------|------|
| `quality_audit.overall_score >= REVIEW_SKIP_THRESHOLD`（默认 85）且无 uncovered test_points | 跳过全量 `review_test_cases`，仅跑规则校验 + 写 summary |
| `overall_score` 在 70~84 | 轻量 review：只传 quality_gate 低分用例 + missing_types 摘要 |
| `< 70` 或有 uncovered | 全量 review + supplement |

配置：`REVIEW_GATING_ENABLED=true`，阈值可调。

### D12: 兜底分级（Strict Fill Mode）

**决策**：新增 `GENERATION_FILL_MODE`：

- `strict`（推荐生产）：禁止 `_fill_case_blanks` 写模板；空白字段触发 targeted re-gen 或 pipeline 失败
- `warn`：允许 fill，但在 quality_audit 标记 `filled_by_template: [case_ids]`，overall_score 封顶 75
- `legacy`：保持现有行为

**理由**：模板 steps/expected 会骗过粗检，降低用例可执行性。

### D13: 分批并行与动态 Token

**决策**：

- 模块 batch 使用 `asyncio.Semaphore(GENERATION_BATCH_CONCURRENCY=3)` 并行
- `max_tokens = base + per_test_point * count`，上限 `GENERATION_MAX_TOKENS_CAP`
- 单 batch 超时沿用 `LLM_STEP_TIMEOUT_SECONDS`，失败 batch 单独重试 1 次

### D14: 合并后规范化

**决策**：`coverage_planner.normalize_merged_cases()`：

1. 跨 batch 重排 id（连续整数）
2. module 名映射表（strategy 模块名为 canonical，LLM 输出 fuzzy match 归一）
3. 语义去重：title 归一化 + steps 前 100 字 Jaccard > 0.85 → 保留 quality_gate 高分条

### D15: 多路径统一

**决策**：抽取 `GenerationOrchestrator`（或 `run_case_generation()` 单函数），供以下入口调用：

- `pipeline.run_generation_pipeline` Phase 2
- `test_case_generation_service.generate_test_cases_stream`
- `generation.process_generation_request`

流式路径逐步输出 batch 进度事件；legacy 保持同步返回。

### D16: 补全后再评分

**决策**：在 `supplement_cases_for_gaps()` 与 `review` supplement 之后，**必须**再调用 `quality_gate.score_cases()`，将 `pre_supplement_score` / `post_supplement_score` 写入 generation/review payload。

### D17: 知识库多阶段注入

**决策**：新增 `retrieve_kb_context(phase, query, *, module=None)` 统一检索入口：

| phase | query 来源 | 默认 top_k | 字符预算 |
|-------|-----------|------------|----------|
| analysis | 需求全文摘要 | `KB_TOP_K_ANALYSIS=3` | 800 |
| strategy | analysis 前 8k + 模块名列表 | `KB_TOP_K_STRATEGY=3` | 600 |
| generation | 策略全文或当前 module + test_points | `KB_TOP_K=5` | 1200 |
| generation_batch | 当前 module 名 + test_point titles | `KB_TOP_K_MODULE=3` | 800 |

各阶段通过 Skill builder 可选注入；**禁止**在 analysis 阶段注入具体历史用例步骤（仅模块/方法参考）。

### D18: 结构化 KB 入库 Schema

**决策**：扩展 metadata：

**adopted_test_case** 增加：`case_type`、`quality_score`（来自 quality_gate）、`content_hash`

**新增 entry_type=task_summary**（manual_review 完成后）：

```json
{
  "task_id": "...",
  "entry_type": "task_summary",
  "modules": ["登录", "权限"],
  "case_count": 42,
  "case_type_distribution": {"功能-正向": 12, "边界值": 5},
  "source_file_name": "req.md",
  "adopted_at": "ISO8601"
}
```

跨任务检索 `CROSS_TASK_ALLOWED_TYPES` 扩展为 `{"adopted_test_case", "task_summary"}`，task_summary 优先排序。

### D19: 真实 Rerank（MMR）

**决策**：实现 `rerank_kb_hits(hits, *, diversity_lambda=0.3)`：

1. 初排：`(similarity, hit_count)` 已有
2. MMR：迭代选取与已选集合 embedding 距离最大的候选，降低同质 adopted 用例
3. pipeline `rerank_filter` 子步骤调用此函数，payload 标记 `rerank_applied=true`

**备选**：调用 cross-encoder API → 增加依赖与延迟，**一期不采用**。

### D20: 模块级检索

**决策**：分批生成时 `find_similar_requirement_history(query_text=module_query, module_filter=module_name)`，Qdrant must filter `case_module` 或 task_summary.modules 包含该 module。

### D21: 标题感知 Chunk 与瞬态任务治理

**决策**：

- `split_requirement_text` 优先按 Markdown H2/H3 边界切分，metadata 写 `section_title`
- `KB_SKIP_TRANSIENT_INGEST=true`（默认）：`task_id` 匹配 `stream-*`/`legacy-*` 时跳过 `ingest_requirement_document`
- 可选 cron：`purge_kb_by_task_prefix(["stream-", "legacy-"])` 清理历史孤儿

### D22: 入库去重与 Upsert

**决策**：adopted case 的 vector id 固定为 `{task_id}:adopted:{case_id}`（去掉 `:idx` 后缀），重复采纳覆盖更新；入库前 `content_hash` 相同则 skip。

### D23: 检索可观测性与 Embedding 状态

**决策**：analysis/generation payload 统一 `kb_retrieval`：

```python
{
  "phase": "generation",
  "hit_count": 3,
  "embedding_mode": "openai" | "hash_fallback",
  "rerank_applied": true,
  "hits_preview": [{"task_id", "similarity", "entry_type", "case_module"}],
  "cold_start_fallback": "test_case_library" | null
}
```

### D24: 冷启动 SQL Fallback

**决策**：向量检索 0 命中且 `KB_SQL_FALLBACK_ENABLED=true` 时，从 `test_case_library` 按需求关键词 + module 模糊匹配 Top-3，标记 `retrieval_mode=cold_start_sql`。

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 分批生成 LLM 调用次数增加，成本/延迟上升 | batch 上限、小模块合并、并行 batch（asyncio.gather，限并发 3） |
| 策略 JSON 解析失败阻断流程 | 降级 Markdown 策略 + 启发式转换；解析失败回退 legacy 单次生成 |
| 合并去重误删合法用例 | 仅对 title 归一化后 Levenshtein > 0.92 且 steps 高度相似时去重；保留 priority 更高者 |
| test-strategy Skill 未入库 | SOURCE.md 增加映射；health check 告警；fallback 路径 |
| 覆盖矩阵计算与 LLM 命名不一致 | test_point title 模糊匹配 + module 名强制相等 |
| 并行 batch 导致 rate limit | Semaphore + 指数退避重试；可配置并发为 1 降级串行 |
| Review gating 跳过评审漏问题 | 仅在高分且无 uncovered 时跳过；阈值保守默认 85 |
| strict fill 提高失败率 | 配合 targeted re-gen；配置可切 warn 模式 |
| 三路径统一改动面大 | 先抽 orchestrator，stream/legacy 逐入口切换 |
| task_summary 与 adopted 重复召回 | rerank MMR + entry_type 配额（summary 至少 1 条） |
| 多阶段 KB 增加 embedding 调用 | 复用 query embedding 缓存；module batch 共用 module 向量 |
| 瞬态不入库后 stream 无法「自检索」 | stream 本就不跨任务检索当前 doc，仅 pipeline 正式 task 入库 |

## Migration Plan

1. **Phase A（兼容）**：新增配置 `STRUCTURED_STRATEGY_ENABLED=false`（默认 false），仅增加 schema 解析与 audit 日志，不改变生成路径
2. **Phase B（灰度）**：staging 开启 structured strategy + batched generation，对比 legacy A/B 指标（已有 `QA_SKILL_AB_ENABLED` 可复用）
3. **Phase C（默认开启）**：生产默认 `STRUCTURED_STRATEGY_ENABLED=true`；保留 legacy 开关 2 个版本周期
4. **回滚**：配置切回 false 即恢复现有单次生成路径，无 DB migration

## Open Questions

1. `test-strategy-plus` Skill 是否已在 library 目录就绪，或需从 `.claude/skills` 同步？
2. 分批并行度 3 是否满足现有 LLM rate limit？
3. 前端是否需要在本次变更中展示覆盖矩阵，还是仅 API 预留？
4. Review gating 默认阈值 85 是否适合当前业务（偏保守可设 90）？
5. strict fill 是否作为 staging 默认，生产仍用 warn 过渡？
6. 二期增量差分生成是否依赖需求文档版本存储（当前 KB 是否已存 doc hash）？
7. `KB_SQL_FALLBACK_ENABLED` 默认开启还是仅 staging？
8. 是否需一次性脚本清理现有 `stream-*`/`legacy-*` 孤儿向量？
