## Context

Skills 中心后端 API 已可用：`GET /api/ai/skills` 返回 5 个 library Skill；`GET /api/ai/skill-role-config` 返回三角色默认绑定。前端 axios 拦截器仅校验 `code !== 0`，**未** unwrap `data` 字段。`SkillsCenter.vue` 多处使用 `res.data` 直接赋值，导致 `summary.skills`、`roleConfig.roles` 为 undefined，表格显示「暂无数据」，统计卡片显示 0 / 关。

全局总开关在 `onGlobalSkillToggle` 成功后调用 `loadList(false)`，其中 `qaSkillsEnabled.value = !!summary.value?.enabled` 因解析错误将开关写回 false。

## Goals / Non-Goals

**Goals:**

1. 统一 Skills 中心 API 数据读取路径，Skill 列表与角色配置正确展示已有 Skill/绑定
2. 全局总开关切换后 UI 与后端 `skill_settings` 一致
3. 角色配置 Tab 支持「新增绑定」（角色 + Skill + enabled）
4. Few-shot、智能路由默认开启（后端 default + env.example + UI 正确读取）

**Non-Goals:**

- 不新增 REST 端点（复用现有 `PUT /api/ai/skill-role-config`）
- 不在线编辑 SKILL.md 内容
- 不改造 discover/supplement 等非 pipeline 三角色

## Decisions

### D1: 响应 unwrap — 页面内修正 vs 拦截器全局 unwrap

**决策**：在 `SkillsCenter.vue`（及本页调用的 API 层）使用 `res.data?.data ?? res.data` 或小型 `unwrapResponse(res)`  helper，**不**修改全局 axios 拦截器（避免影响 export blob 等二进制响应）。

**理由**：Dashboard 等页面已手动使用 `resp.data.data`；全局 unwrap 可能破坏 `exportSkill` 的 Blob 处理。

### D2: 角色「新增绑定」UI

**决策**：在角色配置 Tab 增加「新增绑定」按钮，打开对话框：下拉选择 `analysis | generation | review`（已存在绑定的角色 disabled 或提示覆盖）、Skill 下拉（来自 list_skills）、enabled 默认 true。提交时合并 `roleConfigDraft` 调用 `updateSkillRoleBinding({ skill_configs: [...] })`。

**理由**：后端 PUT 已支持全量 `skill_configs` 数组；无需新 API。

### D3: 默认开关

| 项 | 变更 |
|----|------|
| `QA_SKILL_DISCOVER_ENABLED` | `False` → `True` |
| `QA_SKILL_FEWSHOT_ENABLED` | 保持 `True` |
| `skill_settings` 种子 | 新库默认 `qa_skills_enabled=true` |

### D4: 全局开关与 loadList 顺序

**决策**：`loadList` 不再覆盖 `qaSkillsEnabled`（或仅在 `loadRoleConfig` 路径更新）；全局开关以 `getSkillRoleBinding` / PUT 响应为准。

## Risks / Trade-offs

- [Risk] 部分页面仍用 `res.data` → 仅修 Skills 中心，其他页面不受影响
- [Risk] 用户 `.env` 中 `QA_SKILL_DISCOVER_ENABLED=false` → 仍尊重 env，UI 显示 env 只读状态
- [Trade-off] 角色新增暂限三 pipeline 角色，扩展需后续迭代
