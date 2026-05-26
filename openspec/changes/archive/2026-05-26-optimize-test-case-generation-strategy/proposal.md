## Why

当前测试用例生成链路（需求分析 → 测试策略 → 一次性 LLM 生成 → 规则质量门禁 → AI 评审补全）在复杂需求下存在多类系统性问题：**策略与用例之间缺乏可机器校验的覆盖映射**、**单次大批量生成易截断/漏测**、**测试策略阶段复用分析 Skill 导致策略颗粒度不稳定**，以及 **pipeline / stream / legacy 三条路径能力不一致**、**长文档硬截断丢上下文**、**历史 KB 仅作风格参考**、**评审阶段无论质量高低都全量跑 LLM**。这些问题表现为：用例数量与需求复杂度不匹配、9 类 case_type 覆盖不全、评审阶段大量 missing_scenarios 需事后补全、质量门禁频繁触发低分重写、以及 `_fill_case_blanks` 兜底模板掩盖真实质量问题。现在优化策略层，可以在不更换模型的前提下显著提升覆盖率、可执行性与生成稳定性。

## What Changes

- 引入**结构化测试策略**输出契约（模块 → 测试点 → 期望 case_type/优先级/最少用例数），替代当前自由 Markdown 策略作为生成唯一输入
- 将用例生成从**单次全量**改为**按模块/测试点分批生成 + 合并去重**，降低截断与漏测风险
- 启用独立 **test-strategy** Skill（或 test-strategy-plus）专责策略设计，与需求分析解耦
- 增加**覆盖度闭环**：生成后自动对照策略测试点清单校验，缺失项触发定向补全（复用 supplement 能力，前置到生成阶段）
- 增强**智能路由**：在分析/策略阶段联合判定测试类型（功能/API/性能/安全等），支持多标签复合路由
- 优化**质量门禁策略**：除低分单条重写外，对 `missing_types` / 模块零覆盖触发批量补全；支持可配置迭代轮次
- 建立**策略-用例追溯矩阵**（test_point_id → case_ids），写入 generation phase 产物供前端展示
- 将 pipeline 末尾的 expected_result 空白率硬阻断与生成阶段 quality_gate 审计结果统一暴露给前端
- **长文档智能压缩**：替代 `LLM_MAX_*` 硬截断，按模块/章节保留策略相关上下文
- **历史 KB 增强**：相似需求检索返回结构化测试点/模块清单，而不只是 600 字风格片段
- **知识库全链路增强**（见下方「知识库专项」）：多阶段注入、结构化入库、真实 rerank、模块级检索、孤儿数据治理等
- **生成前用例量预估**：根据策略 test_points 计算 `expected_min_cases`，生成后校验缺口
- **多路径能力对齐**：`pipeline.py`、`test_case_generation_service` 流式、`generation.py` legacy 共用同一生成内核
- **评审按需触发**：quality_gate overall_score ≥ 阈值时跳过全量 AI review，仅做规则校验 + 缺口补全
- **兜底分级策略**：`_fill_case_blanks` 改为可配置 strict/warn 模式，strict 下禁止模板填充、强制重生成
- **分批并行与动态 token**：模块 batch 限并发 3，按 test_point 数量动态分配 max_tokens
- **合并后规范化**：跨 batch 统一 case id、module 名称归一、语义去重（title+steps 相似度）
- **补全后再评分**：supplement / 缺口补全完成后必须再跑一轮 quality_gate，结果写入 payload

### 知识库专项（requirement-knowledge-base）

基于 `backend/app/rag/knowledge_base.py` 现状，当前 KB 存在以下可优化点：

| 现状 | 问题 |
|------|------|
| 检索结果**仅注入 generate 阶段** | 分析/策略阶段无法借鉴历史模块划分与测试方法 |
| `build_generation_history_context` 每条截断 **600 字** | 高相似命中无法传递完整颗粒度参考 |
| 采纳入库 metadata **无 case_type** | 无法按类型分布做历史覆盖参考 |
| pipeline `rerank_filter` 子步骤**无实际实现** | 多 chunk 检索合并后无 MMR/重排，易返回同质用例 |
| stream/legacy 用 `stream-*`/`legacy-*` **瞬态 task_id 入库** | 需求 chunk 成为孤儿向量，占用存储且永不参与召回 |
| 需求 chunk 固定 **700 字**切分 | 与 Markdown 章节/模块边界不对齐 |
| 跨任务召回**仅 adopted_test_case** | 设计正确，但缺少 **task_summary** 聚合层，检索粒度偏碎 |
| 分批生成时检索 query 为**全文** | 无法按当前 module 做定向召回 |
| **无入库去重** | 重复采纳/重复上传产生冗余向量 |
| embedding 降级 **hash** 时仅日志 | pipeline payload 未暴露，召回质量不可观测 |
| **test_case_library（SQL）与向量 KB 双轨** | 冷启动时无法 fallback 到库内结构化用例 |

**一期 KB 优化项：**

- **多阶段 KB 注入**：分析、策略、生成（及分批时按 module）分阶段检索与 prompt 组装，各阶段独立 `top_k` / 字符预算
- **结构化采纳入库**：`ingest_adopted_test_cases` 增加 `case_type`、`quality_score`、task 级 `modules[]` / `case_type_distribution` 摘要
- **任务摘要向量**（`entry_type=task_summary`）：manual_review 完成后写入，供跨任务检索时一次命中覆盖全貌
- **真实 rerank**：实现 `rerank_kb_hits()`（MMR 多样性 + similarity×hit_count 加权），替换 pipeline 空壳 `rerank_filter`
- **模块级检索**：分批生成时对当前 module 名 + test_point 标题构造 query，metadata 过滤 `case_module`
- **标题感知 chunk 入库**：需求文档按 H2/H3 切 chunk，metadata 带 `section_title`
- **瞬态任务不入库或 TTL 清理**：`stream-*`/`legacy-*` 跳过 `ingest_requirement_document`，或异步清理 job
- **入库 content-hash 去重**：同 task 同 case_id 重复采纳 upsert 而非追加
- **检索可观测性**：analysis/generation payload 写入 `kb_retrieval`（hits、scores、embedding_mode、rerank_applied）
- **冷启动 fallback**：向量检索 0 命中时，可选从 `test_case_library` 按 module 关键词 SQL 召回 Top-N

**二期 KB（proposal 预留）：**

- 驳回用例负样本池（`rejected_test_case`，检索时 must_not）
- Hybrid 检索（向量 + metadata 关键词）
- 需求文档 `content_hash` 版本链，支撑增量差分生成
- KB 管理 API / 前端（统计、重建索引、按 task  purge）

### 二期 / 可选优化（本变更不实现，规格预留）

- **增量差分生成**：需求文档版本对比后，仅对变更 module 重新生成，其余 module 复用已采纳用例
- **Skill/Prompt 版本审计**：generation payload 记录 `skill_id`、`skill_version`、`prompt_hash`，便于 A/B 与回溯
- **Token 成本预算**：`GENERATION_TOKEN_BUDGET` 超限时停止后续 batch 或降级为 legacy 单次生成
- **用例可执行性启发式预检**：规则检测 steps 是否含具体操作对象（页面元素/API 路径/输入字段），低分标记 `low_executability`
- **测试数据与边界值注入**：test_point 携带 `suggested_boundaries`，生成 prompt 强制覆盖枚举边界
- **人工采纳反馈闭环**：从 manual_review 采纳/驳回样本更新 KB 权重（与 skill-management 联动）

## Capabilities

### New Capabilities

- `structured-test-strategy`: 结构化测试策略的 schema、生成契约与下游消费规则（测试点清单、覆盖矩阵）
- `coverage-driven-generation`: 基于测试点清单的分批生成、合并去重、覆盖校验与定向补全
- `generation-routing`: 多阶段测试类型识别与 Skill 路由（分析/策略/生成/评审角色联动）
- `context-and-kb-optimization`: 长文档智能压缩、历史 KB 结构化检索、生成前用例量预估
- `requirement-knowledge-base`: 向量库入库/检索/重排/多阶段注入、任务摘要、模块级召回、数据治理
- `generation-quality-governance`: 评审按需触发、兜底分级、补全后再评分、质量指标统一暴露
- `generation-pipeline-unification`: 多入口（pipeline/stream/legacy）共用生成内核与配置开关

### Modified Capabilities

<!-- 项目尚无 openspec/specs/ 基线 spec，本次为首次建立能力规格 -->

## Impact

- **后端核心**：`backend/app/ai/ai.py`（`design_test_strategy`、`generate_test_cases`）、`backend/app/ai/skills/builder.py`、`backend/app/services/pipeline.py`
- **质量门禁**：`backend/app/ai/quality_gate.py`（扩展模块级/类型级覆盖检测）
- **Skill 库**：新增或启用 `test-strategy` / `test-strategy-plus` 映射；更新 `SOURCE.md` 角色绑定
- **配置项**：新增分批生成开关、覆盖补全轮次、策略 JSON schema 版本等环境变量
- **前端**：SkillsCenter / 任务详情页可选展示覆盖矩阵与缺失测试点（非必须，可作为二期）
- **API**：generation phase JSON 结构扩展（向后兼容，新增字段 optional）
- **测试**：`test_skills_smoke.py`、`test_quality_gate.py` 及新增覆盖驱动生成集成测试
- **RAG/KB**：`knowledge_base.py` 全链路增强（入库 schema、rerank、多阶段检索、task_summary、孤儿清理）；`vector_store.py` embedding 状态暴露
- **流式服务**：`test_case_generation_service.py` 对齐新策略（结构化策略 + 覆盖校验）
