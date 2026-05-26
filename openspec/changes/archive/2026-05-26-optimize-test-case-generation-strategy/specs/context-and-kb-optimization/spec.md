## ADDED Requirements

### Requirement: 长文档 MUST 优先智能压缩而非硬截断

当需求文档或策略输入超过 LLM 上下文限制时，系统 SHALL 在调用 `_truncate_for_llm` 之前尝试按章节/模块压缩，并记录 `compression_mode`。

#### Scenario: Markdown 文档按标题切分

- **WHEN** 需求文档包含 H2/H3 标题且总长度超过 `LLM_MAX_ANALYSIS_CHARS`
- **THEN** 系统 MUST 优先保留功能、流程、接口、权限、异常相关章节摘要，并在 payload 标记 `compression_mode=heading`

#### Scenario: 仍超限则硬截断降级

- **WHEN** 智能压缩后仍超过字符上限
- **THEN** 系统 MUST fallback 到现有 char 截断，并标记 `compression_mode=hard_truncate`

#### Scenario: 策略输入优先结构化 analysis

- **WHEN** 结构化 analysis 已包含 modules 列表
- **THEN** 策略阶段 MUST 优先使用 analysis 模块摘要拼接，而非 raw 全文截断

### Requirement: 历史 KB MUST 提供结构化覆盖参考

系统 SHALL 扩展 `build_generation_history_context()`，在相似需求命中时返回模块清单、case_type 分布等结构化字段，而不只是风格片段。

#### Scenario: 命中历史含 metadata

- **WHEN** KB 检索命中且 metadata 含 `modules` 或 `case_types` 分布
- **THEN** 生成上下文 MUST 注入「历史覆盖参考」段，包含模块数与类型分布摘要

#### Scenario: 禁止污染当前需求

- **WHEN** 历史上下文注入生成 prompt
- **THEN** 系统 MUST 保留 CONTAMINATION_GUARD，禁止照搬历史业务术语与具体用例步骤

### Requirement: 生成前 MUST 计算 expected_min_cases

系统 SHALL 从 TestStrategyV1 汇总各 test_point.min_cases 与 global.min_total_cases，得到 `expected_min_cases` 并写入 generation payload。

#### Scenario: 策略含 min_cases 约束

- **WHEN** 策略中 test_points 定义了 min_cases
- **THEN** `expected_min_cases` MUST 等于各 test_point.min_cases 之和与 global.min_total_cases 的较大值

#### Scenario: 生成数量显著不足

- **WHEN** 合并后 `len(cases) < expected_min_cases * 0.8`
- **THEN** 系统 MUST 触发缺口模块定向补全，且不得等待 review 阶段才补全
