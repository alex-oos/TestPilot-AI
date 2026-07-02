## ADDED Requirements

### Requirement: 路由 MUST 在分析阶段完成并复用

系统 SHALL 在 analyze_requirements 完成后执行 route_combined，并将路由结果（generation、review、category、decided_by）写入 analysis phase payload 的 routing 字段，供策略与生成阶段读取。

#### Scenario: 关键词命中 API 类需求

- **WHEN** 需求文本包含 "REST" 或 "接口" 等 API 关键词
- **THEN** routing.category MUST 为 api 且 routing.generation MUST 指向 api 类 generation skill（如 api-test-pytest）

#### Scenario: 下游读取路由

- **WHEN** generate_test_cases 执行且 analysis phase 已有 routing
- **THEN** 系统 MUST 优先使用已存 routing，不得重复计算除非显式 force_reroute

### Requirement: 路由结果 MUST 写入 skill_audit

每次路由决策 SHALL 记录到 skill_audit，包含 decided_by（keyword / skill_tags / default / fallback）与 matched_pattern。

#### Scenario: 审计可追溯

- **WHEN** 一次生成任务完成
- **THEN** skill_audit MUST 包含 role=discover 或 routing 相关条目，且 extra 中含 category 与 generation skill_id

### Requirement: 策略 Skill 选择 MUST 考虑路由 category

当 routing.category 非 functional 时，test-strategy 生成 MUST 注入对应测试类型的策略模板片段（如 api 策略强调契约/状态码/鉴权）。

#### Scenario: API 类需求策略

- **WHEN** routing.category 为 api
- **THEN** 策略 prompt MUST 包含 API 测试方法提示（契约、状态码、鉴权、幂等）

#### Scenario: 默认功能测试策略

- **WHEN** routing.category 为 functional 或未命中规则
- **THEN** 系统 MUST 使用默认功能测试策略模板

### Requirement: 路由 MUST 支持 Skill 不可用降级

当 routing 指向的 generation skill 不在 library 可用列表中时，系统 MUST 降级到 DEFAULT_ROUTE（testcase-writer-plus）并标记 decided_by=fallback。

#### Scenario: 路由 skill 缺失

- **WHEN** routing.generation 为 mobile-testing 但该 skill 未安装
- **THEN** 实际生成 MUST 使用 testcase-writer-plus 且 audit 记录 fallback 原因
