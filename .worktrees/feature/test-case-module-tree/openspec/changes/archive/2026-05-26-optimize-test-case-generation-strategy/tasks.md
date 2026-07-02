## 1. 配置与 Schema 基础

- [x] 1.1 在 `backend/app/core/config.py`（或 settings）新增 `STRUCTURED_STRATEGY_ENABLED`、`GENERATION_MAX_BATCHES`、`COVERAGE_SUPPLEMENT_ENABLED`、`COVERAGE_REFINE_ROUNDS`、`QUALITY_GATE_TYPE_SUPPLEMENT_ENABLED` 等配置项及 `.env.example` 说明
- [x] 1.2 新增 `backend/app/ai/strategy_schema.py`：定义 `TestStrategyV1` dataclass/Pydantic 模型、JSON 解析与校验函数
- [x] 1.3 实现 `_markdown_strategy_to_v1()` 启发式转换（Markdown 策略 → 最小可用 V1 JSON），供降级路径使用

## 2. 结构化测试策略（structured-test-strategy）

- [x] 2.1 在 `backend/app/ai/skills/builder.py` 新增 `build_strategy_messages()`，绑定 test-strategy-plus / test-strategy Skill，输出 JSON 契约
- [x] 2.2 更新 `backend/app/ai/skills/library/SOURCE.md`：strategy 角色映射到 test-strategy Skill
- [x] 2.3 重构 `design_test_strategy()`（`ai.py`）：优先 JSON 输出 + 解析；失败时 fallback legacy extension
- [x] 2.4 扩展 `pipeline.py` analysis phase payload：写入 `design_structured`、`generation_mode` 字段

## 3. 智能路由增强（generation-routing）

- [x] 3.1 在 `analyze_requirements` 或 pipeline Phase 1 末尾调用 `route_combined`，结果写入 `analysis_payload.routing`
- [x] 3.2 `generate_test_cases` 读取已存 routing，避免重复路由；审计写入 skill_audit（role=discover）
- [x] 3.3 `build_strategy_messages` 根据 routing.category 注入 API/性能/安全等策略模板片段

## 4. 覆盖驱动分批生成（coverage-driven-generation）

- [x] 4.1 新增 `backend/app/ai/coverage_planner.py`：`build_coverage_matrix()`、`find_coverage_gaps()`、`merge_and_dedupe_cases()`
- [x] 4.2 新增 `generate_test_cases_batch()`：单 module/sub-batch 生成，复用现有 skill builder 与 JSON 解析
- [x] 4.3 重构 `generate_test_cases()`：当 `STRUCTURED_STRATEGY_ENABLED` 时走分批路径，否则保持 legacy 单次生成
- [x] 4.4 实现 `supplement_cases_for_gaps()`：基于 uncovered test_points 与 missing case_types 调用 supplement messages
- [x] 4.5 扩展 `pipeline.py` generation payload：`coverage_matrix`、`batch_stats`、`quality_audit`

## 5. 质量门禁增强

- [x] 5.1 扩展 `quality_gate.score_cases`：返回 `module_coverage`（零覆盖模块列表）
- [x] 5.2 增强 `_apply_quality_gate()`：当 `missing_types` 非空且配置启用时，追加类型定向补全
- [x] 5.3 统一 pipeline 末尾 expected_result 阻断与 quality_gate 审计结果到同一 payload 结构

## 6. Skill 库与测试

- [x] 6.1 确认/同步 test-strategy-plus Skill 到 `backend/app/ai/skills/library/`，补充 health check
- [x] 6.2 新增 `backend/tests/test_strategy_schema.py`：V1 解析、降级转换单测
- [x] 6.3 新增 `backend/tests/test_coverage_planner.py`：覆盖矩阵、缺口检测、去重逻辑单测
- [x] 6.4 更新 `test_skills_smoke.py`：build_strategy_messages 冒烟
- [x] 6.5 集成测试：mock LLM 验证分批生成 + 覆盖补全完整链路（可选 e2e pipeline test）

## 7. 灰度与文档

- [x] 7.1 默认 `STRUCTURED_STRATEGY_ENABLED=false`，staging 验证后切换默认值
- [x] 7.2 在 generation API 响应/schema 文档中说明新增 optional 字段（代码注释即可，不单独写 md 文档）

## 8. 上下文与 KB 优化（context-and-kb-optimization）

- [x] 8.1 新增 `backend/app/ai/context_compressor.py`：按 Markdown 标题切分、模块摘要拼接、compression_mode 标记
- [x] 8.2 在 `analyze_requirements` / `design_test_strategy` 入口接入压缩器，优先于 `_truncate_for_llm`
- [x] 8.3 扩展 `build_generation_history_context()`：注入 modules、case_types 分布等结构化 KB 字段
- [x] 8.4 可选：入库时写入 cases 元数据摘要（module 清单、case_type 计数）供后续检索
- [x] 8.5 实现 `compute_expected_min_cases(strategy_v1)` 并在 generation payload 写入；不足 80% 触发前置补全

## 9. 质量治理（generation-quality-governance）

- [x] 9.1 新增配置：`REVIEW_GATING_ENABLED`、`REVIEW_SKIP_THRESHOLD`、`GENERATION_FILL_MODE`
- [x] 9.2 实现 review gating：高分跳过 / 中分轻量 / 低分全量，写入 review phase summary
- [x] 9.3 重构 `_fill_case_blanks`：strict 禁止模板、warn 写 `filled_by_template` 并封顶分数
- [x] 9.4 supplement / 缺口补全后强制再跑 `quality_gate`，写入 pre/post supplement 分数
- [x] 9.5 统一 `quality_audit` 结构：合并 expected_result 空白率、module_coverage、filled_by_template

## 10. 多路径统一与并行（generation-pipeline-unification）

- [x] 10.1 抽取 `GenerationOrchestrator`（或 `run_case_generation()`）：封装策略解析、分批、覆盖、补全、评分
- [x] 10.2 `pipeline.py` Phase 2 改为调用 orchestrator
- [x] 10.3 `test_case_generation_service.py` 流式路径接入 orchestrator，推送 batch 进度事件
- [x] 10.4 `generation.py` legacy 入口委托 orchestrator，保证开关一致
- [x] 10.5 分批并行：`asyncio.Semaphore(GENERATION_BATCH_CONCURRENCY)` + 动态 max_tokens + 单 batch 重试
- [x] 10.6 `coverage_planner.normalize_merged_cases()`：id 重排、module 归一、语义去重
- [x] 10.7 新增集成测试：三入口在 mock LLM 下行为一致（至少 pipeline vs stream）

## 11. 知识库全链路（requirement-knowledge-base）

- [x] 11.1 新增配置：`KB_TOP_K_ANALYSIS`、`KB_TOP_K_STRATEGY`、`KB_TOP_K_MODULE`、`KB_CONTEXT_MAX_CHARS`、`KB_SKIP_TRANSIENT_INGEST`、`KB_SQL_FALLBACK_ENABLED`
- [x] 11.2 实现 `retrieve_kb_context()` + `rerank_kb_hits()`（MMR），替换 pipeline 空壳 rerank_filter
- [x] 11.3 扩展 `ingest_adopted_test_cases`：case_type、quality_score、content_hash；稳定 vector id upsert
- [x] 11.4 实现 `ingest_task_summary()`，在 manual_review 采纳流程末尾调用
- [x] 11.5 扩展 `CROSS_TASK_ALLOWED_TYPES` 含 task_summary；检索排序优先 summary
- [x] 11.6 标题感知 `split_requirement_text` + section_title metadata
- [x] 11.7 瞬态 task 跳过入库；可选 `purge_kb_by_task_prefix` 清理脚本
- [x] 11.8 模块级检索：`find_similar_requirement_history(module_filter=...)`
- [x] 11.9 多阶段注入：analysis / design_test_strategy / generate / batch 接入 retrieve_kb_context
- [x] 11.10 重构 `build_generation_history_context`：结构化摘要、可配置 snippet 长度
- [x] 11.11 冷启动 SQL fallback：对接 test_case_library 关键词召回
- [x] 11.12 payload `kb_retrieval` 写入 analysis + generation phase；暴露 embedding_mode
- [x] 11.13 新增 `backend/tests/test_knowledge_base_rerank.py`、`test_kb_multi_phase.py`
