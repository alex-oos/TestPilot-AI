## ADDED Requirements

### Requirement: 评审 MUST 支持按需触发（Review Gating）

系统 SHALL 根据 quality_gate 分数与 uncovered test_points 决定是否跳过或缩减 AI review。

#### Scenario: 高质量集跳过全量 review

- **WHEN** `REVIEW_GATING_ENABLED=true` 且 `overall_score >= REVIEW_SKIP_THRESHOLD`（默认 85）且 uncovered 为空
- **THEN** 系统 MUST 跳过全量 `review_test_cases`，仅执行规则校验并写入 review summary

#### Scenario: 中等质量轻量 review

- **WHEN** overall_score 在 70（含）至 REVIEW_SKIP_THRESHOLD（不含）之间
- **THEN** 系统 MUST 仅对 quality_gate 低分用例与 missing_types 摘要发起轻量 review

#### Scenario: 低质量或存在 uncovered 全量 review

- **WHEN** overall_score < 70 或 coverage_matrix.uncovered 非空
- **THEN** 系统 MUST 执行全量 review 并允许 supplement

### Requirement: 兜底填充 MUST 支持 strict/warn/legacy 分级

系统 SHALL 通过 `GENERATION_FILL_MODE` 控制 `_fill_case_blanks` 行为。

#### Scenario: strict 模式禁止模板填充

- **WHEN** `GENERATION_FILL_MODE=strict` 且用例存在空白 steps 或 expected_result
- **THEN** 系统 MUST NOT 写入模板占位内容，并 MUST 触发 targeted re-gen 或标记 generation 失败

#### Scenario: warn 模式标记模板填充

- **WHEN** `GENERATION_FILL_MODE=warn` 且发生模板填充
- **THEN** quality_audit MUST 包含 `filled_by_template` 列表，且 overall_score MUST 封顶 75

#### Scenario: legacy 保持现有行为

- **WHEN** `GENERATION_FILL_MODE=legacy` 或未配置
- **THEN** 系统 SHALL 保持现有 `_fill_case_blanks` 行为

### Requirement: 补全后 MUST 再评分

系统 SHALL 在 supplement 或缺口补全合并后再次调用 `quality_gate.score_cases()`。

#### Scenario: supplement 后写入双分

- **WHEN** 任意 supplement 流程向 cases 追加新用例
- **THEN** payload MUST 包含 `pre_supplement_score` 与 `post_supplement_score`

#### Scenario: 补全后分数下降可观测

- **WHEN** post_supplement_score 低于 pre_supplement_score
- **THEN** 系统 MUST 记录 warning 日志，且不得静默丢弃该差异

### Requirement: 质量指标 MUST 统一暴露

系统 SHALL 将 quality_gate 审计、expected_result 空白率、module_coverage、filled_by_template 写入同一 `quality_audit` 结构供 API 消费。

#### Scenario: generation phase 含完整 audit

- **WHEN** 客户端查询 generation phase 完成态
- **THEN** 响应 MUST 包含 quality_audit（含 overall_score、missing_types、module_coverage）
