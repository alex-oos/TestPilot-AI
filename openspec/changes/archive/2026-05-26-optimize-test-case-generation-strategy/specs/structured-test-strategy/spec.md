## ADDED Requirements

### Requirement: 测试策略 MUST 输出结构化 JSON

系统 SHALL 在测试策略生成阶段产出符合 `TestStrategyV1` schema 的 JSON 对象，包含 modules、test_points、case_types_required、min_cases 与 global_requirements 字段。

#### Scenario: 策略生成成功

- **WHEN** 需求分析完成且结构化策略功能已启用
- **THEN** 系统 MUST 返回 version=1 的 JSON 策略，且每个 module 至少包含 1 个 test_point

#### Scenario: 策略 JSON 解析失败降级

- **WHEN** LLM 返回的策略无法解析为 TestStrategyV1
- **THEN** 系统 MUST 回退到 legacy Markdown 策略路径，并记录降级原因到 skill_audit

### Requirement: 测试策略 MUST 使用独立 Skill

系统 SHALL 使用专责 test-strategy 类 Skill（如 test-strategy-plus）生成策略，不得默认复用 requirements-analysis-plus 的 strategy_extension 作为主输出。

#### Scenario: 独立 Skill 可用

- **WHEN** test-strategy Skill 已在 library 中注册
- **THEN** design_test_strategy MUST 通过 build_strategy_messages（或等价 builder）拼装 prompt

#### Scenario: 独立 Skill 不可用

- **WHEN** 配置的 test-strategy Skill 加载失败
- **THEN** 系统 MUST fallback 到现有 analysis+extension 流程并标记 decided_by=fallback

### Requirement: 策略 MUST 包含全局覆盖约束

结构化策略 MUST 在 global_requirements 中声明 min_total_cases 与 required_case_types（至少包含：功能-正向、功能-反向、边界值、异常处理、数据校验）。

#### Scenario: 全局约束声明

- **WHEN** 策略 JSON 生成完成
- **THEN** global_requirements.required_case_types MUST 非空，且 min_total_cases MUST ≥ 1

### Requirement: 策略产物 MUST 持久化到 analysis phase

系统 SHALL 将结构化策略 JSON 写入 analysis phase payload 的 design 字段（或新增 design_structured 字段），供下游生成与覆盖校验读取。

#### Scenario: Pipeline 落库

- **WHEN** run_generation_pipeline 完成策略阶段
- **THEN** task analysis phase 数据 MUST 包含可解析的策略 JSON 或显式 generation_mode=legacy 标记
