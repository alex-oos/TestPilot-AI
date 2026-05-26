## ADDED Requirements

### Requirement: 全局 QA Skills MUST 可开关

系统 SHALL 支持全局启用或禁用 QA Skills 能力；禁用时所有角色 MUST 走 legacy prompt 路径，不调用 Skill loader。

#### Scenario: 全局禁用

- **WHEN** qa_skills_enabled 或 USE_QA_SKILLS 为 false
- **THEN** analyze_requirements、generate_test_cases、review_test_cases MUST NOT 调用 build_*_messages

#### Scenario: UI 展示全局状态

- **WHEN** 用户打开 Skills 中心
- **THEN** 页面 MUST 展示当前全局开关状态，并允许管理员切换（写入配置中心）

### Requirement: 全局开关与 legacy fallback MUST 语义清晰

当全局 Skill 关闭或某角色 enabled=false 时，系统 MUST 在 QA_SKILL_LEGACY_FALLBACK_ENABLED=false 且 Skill 路径不可用时抛出明确错误，而非静默空输出。

#### Scenario: Skill 禁用且 fallback 关闭

- **WHEN** USE_QA_SKILLS=false 且 QA_SKILL_LEGACY_FALLBACK_ENABLED=false
- **THEN** pipeline MUST 失败并提示 Skill 与 legacy 均不可用
