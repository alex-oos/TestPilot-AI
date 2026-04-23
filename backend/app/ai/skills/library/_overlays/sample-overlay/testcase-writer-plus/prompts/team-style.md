# 示例：团队补充 prompt（项目级 overlay）

> 这是一个示例 overlay，演示如何在不修改主 skill 的前提下叠加项目级 prompt 风格补丁。
> 启用方式：在 `backend/.env` 中设置 `QA_SKILL_OVERLAY=sample-overlay` 并调用 `/api/ai/skills/reload`。

## 团队约定

- 测试用例标题前缀：`[业务模块]` 必须放在标题最前面（示例："[订单服务] 验证下单时…"）。
- 步骤必须可在内部测试环境直接执行，不引用任何线上数据。
- 模糊词如"正常"、"成功"、"OK" 全部禁用，必须替换为具体可断言指标。
