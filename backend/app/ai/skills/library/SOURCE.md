# QA Skills Library

本目录的 skill 复制自开源项目 [naodeng/awesome-qa-skills](https://github.com/naodeng/awesome-qa-skills)
（中文版 `skills/zh/testing-types/...` 与 `skills/zh/testing-workflows/...`），仅用于驱动本项目内的 LLM 调用。

## 集成关系

| 项目角色 | 使用 Skill |
|---|---|
| 需求分析（`analyze_requirements`） | `requirements-analysis-plus` |
| 测试策略（`design_test_strategy`） | `requirements-analysis-plus` （复用，启用 strategy 扩展段） |
| 测试用例编写（`generate_test_cases`） | `testcase-writer-plus` |
| 测试用例评审（`review_test_cases`） | `test-case-reviewer-plus` |
| 评审补全（`_supplement_cases_from_review`） | `testcase-writer-plus` （复用） |
| 智能路由（discover）| `discover-testing` |

## 加载到运行时的资源

`SkillLoader` 会扫描每个 skill 目录的：

- `SKILL.md` —— 角色定位/方法论/最低覆盖清单（含 `frontmatter`：`name` / `description` / `version` / `lang` / `tags`）
- `prompts/*.md` —— 主 prompt（同名文件优先作为 primary）
- `output-templates/*` —— 输出模板示例
- `examples/*.md|*.json` —— 用于 few-shot
- `references/**/*.md` —— 引用资料
- `README.md` —— 描述

## 升级方式（推荐用同步脚本）

```bash
python backend/scripts/sync_qa_skills.py \
  --source ~/.codex/skills/zh/testing-types \
  --skills requirements-analysis-plus testcase-writer-plus test-case-reviewer-plus \
  [--dry-run]   # 仅打印 diff，不写入
```

升级完成后调用一次 `POST /api/ai/skills/reload` 即可热重载缓存。

## 项目级 Overlay（不修改主 skill 的前提下叠加）

详见 `_overlays/README.md`。例：

```
library/_overlays/sample-overlay/testcase-writer-plus/prompts/team-style.md
```

启用：`backend/.env` 设置 `QA_SKILL_OVERLAY=sample-overlay`，多个用逗号分隔，按顺序叠加。

## 本地自定义（业务自定义补充）

不要修改 `library/` 中的文件。请在前端「配置中心 → 提示词配置 / 角色配置」中按角色追加内容，
运行时会按 **Skill Methodology → JSON Output Contract → 业务自定义补充 → CONTAMINATION_GUARD** 顺序拼装；
注入防御会过滤明显的 prompt-injection 关键词，并在超过 `QA_SKILL_EXTRA_PROMPT_MAX_CHARS` 时截断。
