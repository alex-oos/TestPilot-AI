## 1. 前端 — API 响应解析修复

- [x] 1.1 在 `frontend/src/utils/request.ts` 或 `frontend/src/api/skills.ts` 增加 `unwrapApiData(res)`，返回 `res.data?.data ?? res.data`
- [x] 1.2 `SkillsCenter.vue` 的 `loadList`、`loadRoleConfig`、`onGlobalSkillToggle` 等全部改用 unwrap，修复 Skill 列表「暂无数据」
- [x] 1.3 `loadList` 不再用 `summary.enabled` 覆盖 `qaSkillsEnabled`（全局开关以 role-config 为准）
- [x] 1.4 修复后验证：已加载 Skill 数量、Few-shot/智能路由卡片、角色配置三行默认数据可见

## 2. 前端 — 全局总开关

- [x] 2.1 页面初始化时 `loadRoleConfig` 设置 `qaSkillsEnabled`；`loadList` 仅更新 `summary` 统计
- [x] 2.2 `onGlobalSkillToggle` 成功后刷新 summary 与 role-config，开关保持用户选择状态
- [x] 2.3 当 `summary.enabled === false` 时显示告警；启用后告警消失

## 3. 前端 — 角色配置「新增绑定」

- [x] 3.1 角色配置 Tab 增加「新增绑定」按钮与对话框（角色下拉 + Skill 下拉 + enabled 开关）
- [x] 3.2 可选角色：`analysis`、`generation`、`review`；已绑定角色在新增时禁用或引导编辑
- [x] 3.3 保存时将 draft 转为 `skill_configs` 数组调用 `updateSkillRoleBinding`
- [x] 3.4 支持编辑已有行的 skill_id / enabled；保存后表格刷新

## 4. 后端 — 默认开关

- [x] 4.1 `config.py` 将 `QA_SKILL_DISCOVER_ENABLED` 默认值改为 `True`
- [x] 4.2 确认 `QA_SKILL_FEWSHOT_ENABLED` 默认 `True`（已满足则仅文档说明）
- [x] 4.3 `db_initializer` / seed：`skill_settings` 不存在时默认 `qa_skills_enabled=true`
- [x] 4.4 更新 `backend/.env.example` 中 Few-shot、智能路由、USE_QA_SKILLS 默认说明

## 5. 验证

- [x] 5.1 手动：打开 Skills 中心 → Skill 列表显示历史 5 个 Skill
- [x] 5.2 手动：角色配置显示三角色绑定；新增/保存绑定成功
- [x] 5.3 手动：全局开关开启后不回弹；Few-shot、智能路由卡片默认「开」
- [x] 5.4 运行相关后端测试（如有）确保无回归
