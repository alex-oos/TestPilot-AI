## ADDED Requirements

### Requirement: KB 检索 MUST 支持多阶段注入

系统 SHALL 提供 `retrieve_kb_context(phase, query_text, **filters)`，在 analysis、strategy、generation 及 generation_batch 阶段分别检索并组装上下文，各阶段 MUST 使用独立 top_k 与字符预算配置。

#### Scenario: 分析阶段注入模块参考

- **WHEN** pipeline 进入需求分析且 KB 命中 task_summary 或 adopted_test_case
- **THEN** analyze_requirements 的 prompt MUST 可接收 KB 上下文，且上下文 MUST NOT 包含可照搬的历史用例步骤全文

#### Scenario: 策略阶段注入测试方法参考

- **WHEN** design_test_strategy 执行且存在相似 task_summary
- **THEN** 策略 prompt MUST 可接收历史模块清单与 case_type 分布摘要

#### Scenario: 分批生成按 module 检索

- **WHEN** 结构化分批生成处理 module「用户登录」
- **THEN** 系统 MUST 以该 module 名与 test_point 标题构造 query，并优先召回 case_module 匹配的 adopted 用例

### Requirement: 采纳入库 MUST 携带结构化 metadata

系统 SHALL 在 `ingest_adopted_test_cases` 写入 case_type、quality_score（若有）、content_hash，并在 manual_review 完成后写入 task_summary 向量。

#### Scenario: adopted 用例含 case_type

- **WHEN** 采纳用例入库且 case 含 case_type 字段
- **THEN** 向量 metadata MUST 包含 `case_type` 供检索与上下文摘要使用

#### Scenario: manual_review 后写入 task_summary

- **WHEN** 任务 manual_review 完成且至少 1 条用例被采纳
- **THEN** 系统 MUST upsert 一条 entry_type=task_summary 的记录，含 modules、case_count、case_type_distribution

#### Scenario: 跨任务检索包含 task_summary

- **WHEN** find_similar_requirement_history 执行跨任务检索
- **THEN** 允许 entry_type 为 adopted_test_case 或 task_summary，且 task_summary 命中 MUST 参与排序

### Requirement: 检索结果 MUST 经 rerank 去同质

系统 SHALL 实现 `rerank_kb_hits()`，pipeline 的 rerank_filter 子步骤 MUST 调用该函数而非空操作。

#### Scenario: MMR 降低同质命中

- **WHEN** 初检返回多条来自同一 task 的相似 adopted 用例
- **THEN** rerank 后 Top-K MUST 包含至少 2 个不同 task_id（在候选足够时）

#### Scenario: payload 标记 rerank

- **WHEN** rerank 成功执行
- **THEN** kb_retrieval MUST 包含 `rerank_applied=true`

### Requirement: 需求入库 MUST 标题感知且治理瞬态任务

系统 SHALL 支持按 Markdown 标题切分 requirement chunk，并对瞬态 task_id 跳过入库或提供清理机制。

#### Scenario: 标题感知 chunk

- **WHEN** 需求文档含 H2/H3 标题
- **THEN** split_requirement_text MUST 优先在标题边界切分，metadata MUST 含 section_title

#### Scenario: 瞬态 task 跳过入库

- **WHEN** KB_SKIP_TRANSIENT_INGEST=true 且 task_id 匹配 stream-* 或 legacy-*
- **THEN** ingest_requirement_document MUST 跳过写入并返回 skipped=true

### Requirement: 入库 MUST 去重 Upsert

系统 SHALL 对同一 task_id + case_id 的 adopted 向量使用稳定 id 覆盖更新，content_hash 相同时 MUST skip。

#### Scenario: 重复采纳覆盖

- **WHEN** 同一 case_id 再次被采纳入库
- **THEN** 系统 MUST upsert 而非追加重复向量

### Requirement: KB 检索 MUST 可观测

analysis 与 generation phase payload MUST 包含 kb_retrieval 结构，含 hit_count、embedding_mode、hits_preview。

#### Scenario: hash embedding 降级暴露

- **WHEN** EmbeddingService 使用 hash fallback
- **THEN** kb_retrieval.embedding_mode MUST 为 hash_fallback

#### Scenario: 零命中冷启动

- **WHEN** 向量检索返回 0 条且 KB_SQL_FALLBACK_ENABLED=true
- **THEN** 系统 MAY 从 test_case_library SQL 召回并标记 retrieval_mode=cold_start_sql

### Requirement: build_generation_history_context MUST 结构化输出

系统 SHALL 在命中 metadata 含 modules 或 case_type_distribution 时输出结构化摘要，单条 snippet 字符上限 MUST 可配置（默认 1200，替代硬编码 600）。

#### Scenario: 结构化覆盖参考段

- **WHEN** 命中 task_summary 含 case_type_distribution
- **THEN** 上下文 MUST 包含「历史覆盖参考：模块数=N，类型分布=...」段落

#### Scenario: 污染防护保留

- **WHEN** 任意 KB 上下文注入 LLM
- **THEN** MUST 包含 CONTAMINATION_GUARD 声明，禁止照搬业务术语与步骤
