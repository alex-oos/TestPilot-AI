## Context

### 已有能力（无需重复造轮子）

| 能力 | 状态 | 位置 |
|------|------|------|
| 三阶段 Skill 运行时加载 | ✅ | `ai.py` + `role_config._load_role_config()` |
| per-role skill_id + enabled | ✅ 后端 | `skill_configs[].enabled` in config center |
| GitHub 导入 | ✅ | `POST /ai/skills/import/github` |
| ZIP 导入 | ✅ | `POST /ai/skills/import/zip` |
| Skills 中心 UI | ✅ 部分 | `SkillsCenter.vue`（导入已有，映射只读） |
| Skill 导出/删除 API | ❌ | 无 |
| 角色 Skill UI 开关 | ❌ | 前端无 skill_configs 编辑 |
| 全局 USE_QA_SKILLS UI | ❌ | 仅 env 只读告警 |

### 角色与 Skill 默认映射

```
analysis   → requirements-analysis-plus
generation → testcase-writer-plus
review     → test-case-reviewer-plus
```

`enabled=false` 时：该角色使用 `prompt_configs` / DEFAULT_*_PROMPT + legacy 路径（`_use_skills()` 仍为 true 时其他角色不受影响；若需整角色跳过 skill builder，在 `ai.py` 各阶段判断 `role_cfg.get("skill_enabled")`）。

## Goals / Non-Goals

**Goals:**

1. Skills 中心可配置三角色 Skill 绑定与开关，保存到配置中心并立即生效（下次 pipeline 调用读取）
2. 提供 Skill 导出 ZIP、删除 API + UI
3. 保留 GitHub/ZIP 双通道导入，统一在「Skill 管理」操作区
4. 删除/禁用前引用检查，避免 pipeline 指向不存在 Skill

**Non-Goals:**

- 不在线编辑 Skill 文件内容（仍通过导入覆盖）
- 不做 Skill 版本/git 同步（仅导出快照）
- 不改造 supplement/discover 角色的 UI（可后续扩展）

## Decisions

### D1: 配置存储 — 扩展配置中心

**决策**：新增 `skill_configs` 段 API（GET/PUT），结构与现有 `generation_behavior_configs` 类似：

```json
{
  "skill_configs": [
    {"id": "uuid", "role": "analysis", "skill_id": "requirements-analysis-plus", "enabled": true},
    {"id": "uuid", "role": "generation", "skill_id": "testcase-writer-plus", "enabled": true},
    {"id": "uuid", "role": "review", "skill_id": "test-case-reviewer-plus", "enabled": true}
  ],
  "qa_skills_enabled": true
}
```

**理由**：已有 `_pick_role_skill_id` 读取逻辑，只需补 UI 与 PUT API。

### D2: enabled 语义

| 层级 | 字段 | 行为 |
|------|------|------|
| 全局 | `qa_skills_enabled` / `USE_QA_SKILLS` | false → 全部角色 legacy prompt |
| 角色 | `skill_configs[].enabled` | false → 该角色不用 Skill，用 prompt_configs 或 DEFAULT prompt |
| 单项 | Skill 文件存在 | loader 找不到 → health 告警 + pipeline 降级 |

**实现**：`_load_role_config` 返回增加 `skill_enabled: bool`；`analyze_requirements` / `generate_test_cases` / `review_test_cases` 在 `use_skills and role_cfg.get("skill_enabled", True)` 时才走 builder。

### D3: 受保护 Skill 列表

**决策**：`PROTECTED_SKILL_IDS` 常量（内置 library 目录下初始 Skill），删除 API 返回 403。用户通过 GitHub/ZIP 导入的 Skill 可删。

可选：在 Skill 目录写 `.meta.json` 标记 `source: imported|builtin`。

### D4: 导出格式

**决策**：`GET /ai/skills/{skill_id}/export` 返回 `application/zip`，结构与导入兼容（根目录含 SKILL.md），便于跨环境迁移。

实现：`ZipSkillExporter` 遍历 skill 目录打包，排除 `__pycache__`。

### D5: 删除流程

1. 检查 `skill_id in PROTECTED_SKILL_IDS` → 403
2. 检查 `skill_configs` 是否引用 → 409 + 引用列表（前端提示先改绑定）
3. `shutil.rmtree(skill_dir)` + `loader.reset_cache()`

### D6: 前端信息架构

SkillsCenter 调整为：

- **Tab「Skill 管理」**：列表 + 操作列（查看 / 导出 / 删除）+ 顶部导入按钮
- **Tab「角色配置」**：三行表格（角色 | Skill 下拉 | 开关 | 生效 ID）+ 保存
- **顶部**：全局 Skill 总开关

## Risks / Trade-offs

| 风险 | 缓解 |
|------|------|
| 配置中心与 .env 冲突 | 展示优先级：skill_configs > skills map > env > catalog default；UI 标注来源 |
| 删除正在使用的 Skill | 409 引用检查 + 一键跳转角色配置 |
| 导出 ZIP 含敏感 overlay | 仅打包 skill 目录本身，不含 `_overlays` 除非显式勾选 |

## Migration Plan

1. 新增 API 与 UI，默认读取现有 config/env，无数据迁移
2. 首次打开角色配置 Tab 时，用当前 `effective_skill_id` 预填 skill_configs
3. 内置 Skill 标记 protected，不影响现有部署

## Open Questions

1. `qa_skills_enabled` 写配置中心还是仍只读 .env？**建议**：配置中心优先，env 作初始默认值。
2. 是否需要「测试 Skill」按钮（用样例需求跑一轮 analysis）？**建议**：二期。
