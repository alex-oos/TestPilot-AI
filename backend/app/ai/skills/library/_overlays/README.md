# 项目级 Skill Overlay

在 `_overlays/<overlay-name>/<skill_id>/...` 下放置同名子目录（prompts/、examples/、output-templates/、references/），加载器会**叠加**到对应 skill 的资源中（不会覆盖主 skill 的 SKILL.md / 主 prompt）。

## 启用方式

在 `backend/.env`：

```
QA_SKILL_OVERLAY=sample-overlay
# 多个 overlay 用逗号分隔，按顺序叠加
QA_SKILL_OVERLAY=sample-overlay,team-payment
```

## 叠加规则

| 资源类型           | 叠加策略                                    |
| ------------------ | ------------------------------------------- |
| prompts/*.md       | 添加为辅助 prompt（key 加前缀），不覆盖主   |
| output-templates/  | 同名追加（key 加 `_overlay_<name>__` 前缀） |
| examples/          | 全量追加，调用 builder 时一并参与 few-shot 选择 |
| references/        | 同名追加                                    |

## 适用场景

- 团队/项目特有的业务术语库、隐私词表
- 行业特定的测试规范引用
- 一些不希望污染主 skill 的实验性补丁

## 命名约定

- overlay 目录名小写、kebab-case
- 子目录名必须与 library 中的 skill_id 完全一致
