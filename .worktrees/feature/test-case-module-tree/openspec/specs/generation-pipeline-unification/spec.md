# generation-pipeline-unification

## Purpose

生成管线统一：三入口共用 GenerationOrchestrator，分批限并发与动态 token，合并后规范化与流式 batch 进度事件。

## Requirements

### Requirement: 多入口 MUST 共用同一生成内核

系统 SHALL 提供统一的 `GenerationOrchestrator`（或等价 `run_case_generation()`），供 pipeline、流式服务、legacy API 调用。

#### Scenario: pipeline Phase 2 调用 orchestrator

- **WHEN** `pipeline.run_generation_pipeline` 执行 generation 阶段
- **THEN** MUST 通过 orchestrator 调用，不得内联独立生成逻辑

#### Scenario: 流式服务对齐分批与覆盖

- **WHEN** `test_case_generation_service.generate_test_cases_stream` 被调用且结构化策略已启用
- **THEN** MUST 使用与 pipeline 相同的分批、覆盖校验与补全逻辑

#### Scenario: legacy 入口同步行为

- **WHEN** `generation.process_generation_request` 被调用
- **THEN** MUST 委托 orchestrator，保证配置开关对三入口一致生效

### Requirement: 分批生成 MUST 支持限并发与动态 token

系统 SHALL 使用 Semaphore 控制 batch 并发，并按 test_point 数量动态计算 max_tokens。

#### Scenario: 并发上限

- **WHEN** 多 module batch 并行生成且 `GENERATION_BATCH_CONCURRENCY=3`
- **THEN** 同时进行的 LLM 生成调用 MUST NOT 超过 3

#### Scenario: 动态 max_tokens

- **WHEN** 某 batch 含 N 个 test_points
- **THEN** max_tokens MUST 按 `base + per_test_point * N` 计算，且 MUST NOT 超过 `GENERATION_MAX_TOKENS_CAP`

#### Scenario: 单 batch 失败重试

- **WHEN** 某 batch LLM 调用超时或解析失败
- **THEN** 系统 MUST 对该 batch 重试 1 次，失败则记录 batch_stats.error 并继续其他 batch（或整体失败，由配置决定）

### Requirement: 合并后 MUST 规范化用例

系统 SHALL 在跨 batch 合并后执行 id 重排、module 归一与语义去重。

#### Scenario: case id 连续重排

- **WHEN** 多 batch 用例合并完成
- **THEN** 所有 case id MUST 重排为从 1 开始的连续整数

#### Scenario: module 名称归一

- **WHEN** LLM 输出的 module 与 strategy 模块名 fuzzy 匹配
- **THEN** 系统 MUST 映射为 strategy 中的 canonical module 名

#### Scenario: 语义去重

- **WHEN** 两条用例 title 归一化相同且 steps 前 100 字 Jaccard > 0.85
- **THEN** 系统 MUST 保留 quality_gate 分数较高的一条

### Requirement: 流式路径 MUST 输出 batch 进度

当流式生成启用分批模式时，系统 SHALL 推送 batch 级进度事件。

#### Scenario: 流式 batch 事件

- **WHEN** 流式生成正在进行第 k 个 batch（共 n 个）
- **THEN** 客户端 MUST 收到含 `batch_index`、`batch_total`、`module_name` 的进度事件
