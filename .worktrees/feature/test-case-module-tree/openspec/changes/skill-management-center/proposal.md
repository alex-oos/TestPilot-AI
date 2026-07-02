## Why

平台已在运行时通过 Skill 驱动需求分析、用例编写、用例评审（`USE_QA_SKILLS` + `role_config.skill_configs`），GitHub/ZIP 导入也已落地，但**管理面不完整**：角色级 Skill 开关与绑定只能在配置中心 JSON 里改、前端 Skills 中心无法导出/删除 Skill、全局 Skill 总开关缺少 UI。测试团队需要在 Skills 中心一站式完成「选 Skill → 开/关 → 导入/导出/删除」，而不依赖改 `.env` 或手工删目录。

## What Changes

- **角色 Skill 绑定 UI**：需求分析 / 用例编写 / 用例评审三角色各自选择 Skill，支持 **enabled 开关**（关闭时该角色回退 legacy prompt，不加载 Skill）
- **全局 Skill 总开关**：UI 控制 `USE_QA_SKILLS` 等价配置（写入配置中心，运行时生效）
- **Skill 生命周期管理**：
  - **导入**：保留现有 GitHub 一键导入 + ZIP 包导入（已有 API/UI，补齐体验与校验提示）
  - **导出**：单个 Skill 导出为 ZIP（含 SKILL.md、prompts、examples 等）
  - **删除**：删除 library 中用户导入的 Skill（内置/受保护 Skill 不可删）
- **配置中心集成**：`skill_configs` / `extra_prompt_configs` 通过 API CRUD，替代仅 env 只读展示
- **运行态校验**：删除/禁用 Skill 前检查是否被某角色引用，给出阻断或强制切换提示

## Capabilities

### New Capabilities

- `skill-role-binding`: 三角色 Skill 选择与 per-role enabled 开关，持久化到配置中心
- `skill-lifecycle`: Skill 导出 ZIP、删除（含受保护列表与引用检查）
- `skill-global-toggle`: 全局 QA Skills 启用/禁用及与 legacy fallback 联动说明

### Modified Capabilities

<!-- 无既有 openspec/specs 基线 -->

## Impact

- **后端**：`backend/app/api/endpoints/skills.py`（export/delete/config API）、`config_center` 域（skill_configs CRUD）、`role_config.py`（enabled=false 时跳过 Skill）
- **前端**：`SkillsCenter.vue` 角色映射 Tab 改为可编辑；Skill 列表增加导出/删除操作
- **已有复用**：`github_importer.py`、`zip_importer.py`、import 对话框（微调即可）
- **安全**：删除/导出需登录；内置 Skill（requirements-analysis-plus、testcase-writer-plus、test-case-reviewer-plus 等）标记 `protected`
