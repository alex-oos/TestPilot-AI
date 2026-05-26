## ADDED Requirements

### Requirement: 用例生成 MUST 支持按模块分批

当结构化策略已启用时，系统 SHALL 按 strategy.modules 分批调用 LLM 生成用例，每批输入 MUST 仅包含当前 module 的 test_points 及全局约束摘要。

#### Scenario: 多模块需求分批生成

- **WHEN** 策略包含 3 个 module 且分批生成已启用
- **THEN** 系统 MUST 发起至少 3 次生成调用（或经合并后不超过 GENERATION_MAX_BATCHES），并最终合并为单一 cases 列表

#### Scenario: 单模块 test_point 过多拆分

- **WHEN** 某 module 的 test_points 数量超过配置阈值（默认 15）
- **THEN** 系统 MUST 将该 module 拆为多个 sub-batch 分别生成

### Requirement: 生成后 MUST 执行覆盖校验

系统 SHALL 在合并用例后构建 coverage_matrix，映射每个 test_point.id 到覆盖它的 case_ids，并识别 uncovered test_points。

#### Scenario: 全部测试点已覆盖

- **WHEN** 每个 test_point 至少关联 1 条用例
- **THEN** coverage_matrix.uncovered MUST 为空数组

#### Scenario: 存在未覆盖测试点

- **WHEN** 某 test_point 无关联用例
- **THEN** 系统 MUST 将该 test_point 列入 uncovered 并触发定向补全（若 COVERAGE_SUPPLEMENT_ENABLED=true）

### Requirement: 缺失 case_type MUST 触发定向补全

系统 SHALL 对比已生成用例的 case_type 分布与策略要求的 required_case_types / case_types_required，对缺失类型发起 supplement 生成。

#### Scenario: 缺少边界值类型

- **WHEN** quality_gate 或 coverage 校验发现"边界值" case_type 计数为 0 且策略要求该类型
- **THEN** 系统 MUST 生成至少 1 条 case_type=边界值 的补全用例

#### Scenario: 补全后合并去重

- **WHEN** 定向补全返回新用例
- **THEN** 新用例 MUST 分配递增 id 并合并入主 cases 列表，且不得删除已有用例

### Requirement: 覆盖矩阵 MUST 写入 generation phase

系统 SHALL 将 coverage_matrix、batch_stats、generation_mode 写入 generation phase payload，供 API 与前端消费。

#### Scenario: API 返回覆盖信息

- **WHEN** 客户端查询已完成生成的 task generation phase
- **THEN** 响应 MUST 包含 coverage_matrix 字段（legacy 模式下可为 null）

### Requirement: 分批生成 MUST 有上限保护

系统 MUST 遵守 GENERATION_MAX_BATCHES 配置（默认 20），超出时 SHALL 合并较小 module 到同一 batch 并记录 warning 日志。

#### Scenario: 模块数超过 batch 上限

- **WHEN** strategy.modules 数量大于 GENERATION_MAX_BATCHES
- **THEN** 系统 MUST 合并模块而非无限增加 LLM 调用次数
