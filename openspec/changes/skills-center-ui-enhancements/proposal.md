## Why

Skills 中心首版已上线，但用户在实际使用中反馈：全局总开关点击后状态回弹、Skill 列表与角色配置 Tab 显示「暂无数据」、角色绑定缺少「新增」能力，且 Few-shot / 智能路由默认展示为关闭。根因是前端未正确解析 `{ code, data }` 响应 envelope，叠加部分后端默认值与 UI 预期不一致。需要在不改动 API 契约的前提下修复数据展示与交互，并补齐角色绑定新增流程。

## What Changes

- **修复 API 响应解析**：Skills 中心所有接口统一读取 `response.data.data`（或封装 unwrap 工具），使 Skill 列表、角色配置、统计卡片正确渲染历史 Skill
- **修复全局总开关**：切换后不再被错误的 `loadList` 覆盖；保存/刷新与 UI 状态一致
- **角色配置增强**：增加「新增绑定」操作，支持选择角色 + Skill 并保存；保留编辑/删除已有绑定
- **默认开关状态**：Few-shot（`QA_SKILL_FEWSHOT_ENABLED`）与智能路由（`QA_SKILL_DISCOVER_ENABLED`）默认开启；配置中心/`.env.example` 与 UI 展示一致
- **默认全局 Skill 开关**：`skill_settings` 初始化与 `qa_skills_enabled` 默认 true，避免新环境首屏误报「已禁用」

## Capabilities

### New Capabilities

- `skills-center-data-binding`: 前端正确绑定 Skills 中心 API 响应，列表/角色配置/统计卡片可展示已有数据
- `skill-role-binding-create`: 角色配置 Tab 支持新增角色–Skill 绑定并持久化

### Modified Capabilities

<!-- skill-management-center 能力尚未归档至 openspec/specs，本变更以 delta spec 描述增量 -->

## Impact

- **前端**：`SkillsCenter.vue`、`skills.ts`、`skillRoleConfig.ts`；可选新增 `unwrapApiData` 工具
- **后端**：`config.py` 默认 `QA_SKILL_DISCOVER_ENABLED=true`；`db_initializer` / seed 确保 `skill_settings.qa_skills_enabled=true`
- **配置**：`backend/.env.example` 同步默认开关说明
- **测试**：补充前端响应解析或 API 集成冒烟（list_skills / skill-role-config 返回非空 skills/roles）
