## 1. 后端 — 角色配置 API

- [x] 1.1 在 `config_center` 域/schema 增加 `skill_configs`、`qa_skills_enabled` 字段及 CRUD
- [x] 1.2 新增 `GET/PUT /api/ai/skills/role-config` 端点，返回三角色 skill_id、enabled、effective_id、source
- [x] 1.3 扩展 `_load_role_config()` 返回 `skill_enabled`；`ai.py` 三阶段在 `skill_enabled=false` 时跳过 Skill builder
- [x] 1.4 单元测试：enabled 开关、中文角色名、优先级（config > env > default）

## 2. 后端 — 导出与删除

- [x] 2.1 新增 `backend/app/ai/skills/zip_exporter.py`：打包 skill 目录为 ZIP
- [x] 2.2 新增 `GET /ai/skills/{skill_id}/export` 返回 ZIP 流
- [x] 2.3 定义 `PROTECTED_SKILL_IDS`，新增 `DELETE /ai/skills/{skill_id}`：引用检查 + 删目录 + reset_cache
- [x] 2.4 测试：protected 403、引用 409、成功删除、export 往返（export → import）

## 3. 前端 — Skills 中心改造

- [x] 3.1 `skills.ts` 增加 getRoleConfig、updateRoleConfig、exportSkill、deleteSkill API
- [x] 3.2 「角色配置」Tab：三角色 Skill 下拉 + enabled 开关 + 保存；顶部全局 Skill 总开关
- [x] 3.3 「Skill 列表」增加操作列：导出 ZIP、删除（confirm + 409 提示改绑定）
- [x] 3.4 保留并优化现有 GitHub/ZIP 导入对话框（归入 Skill 管理区）

## 4. 集成与校验

- [x] 4.1 health check：角色绑定的 skill_id 不存在时告警
- [x] 4.2 删除/禁用 Skill 后 pipeline 冒烟：三阶段均可正常降级或报错
- [x] 4.3 更新 list_skills 响应：标记 skill 是否 protected、是否被角色引用
