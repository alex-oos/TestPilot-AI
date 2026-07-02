## ADDED Requirements

### Requirement: 三角色 MUST 可独立配置 Skill

系统 SHALL 为需求分析（analysis）、用例编写（generation）、用例评审（review）三个角色提供独立的 skill_id 配置，配置持久化在配置中心 `skill_configs` 中。

#### Scenario: 保存角色 Skill 绑定

- **WHEN** 管理员在 Skills 中心为「用例编写」选择 skill_id=testcase-writer-plus 并保存
- **THEN** 配置中心 MUST 持久化该绑定，且下次 `generate_test_cases` 调用 MUST 使用该 skill_id

#### Scenario: 中文角色名兼容

- **WHEN** skill_configs 中 role 字段为「用例编写」
- **THEN** 系统 MUST 归一化为 generation 并正确应用配置

### Requirement: 角色 Skill MUST 支持 enabled 开关

每个 skill_configs 条目 MUST 包含 enabled 布尔字段；enabled=false 时该角色 MUST NOT 调用 Skill builder，而使用 legacy prompt 路径。

#### Scenario: 关闭用例评审 Skill

- **WHEN** review 角色 skill_configs.enabled 为 false
- **THEN** review_test_cases MUST 使用 DEFAULT_REVIEW_PROMPT 或 prompt_configs，且不加载 test-case-reviewer-plus

#### Scenario: 关闭单角色不影响其他角色

- **WHEN** generation.enabled 为 false 且 analysis.enabled 为 true
- **THEN** 需求分析 MUST 仍使用 Skill，用例编写 MUST 使用 legacy prompt

### Requirement: 角色配置 API MUST 可读写

系统 SHALL 提供 GET/PUT `/ai/skills/role-config`（或配置中心等价端点）返回并更新 skill_configs 与 qa_skills_enabled。

#### Scenario: 读取当前生效配置

- **WHEN** 客户端 GET 角色 Skill 配置
- **THEN** 响应 MUST 包含三角色各自的 skill_id、enabled、effective_skill_id 及配置来源（config/env/default）
