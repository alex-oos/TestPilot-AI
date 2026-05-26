---
name: 测试策略增强版
description: 基于需求分析输出结构化 TestStrategyV1 JSON 测试策略。
version: 1.0.0
lang: zh
tags: [strategy,test-strategy,plus]
---

# 测试策略增强版

## 何时使用

- 需要为下游用例生成提供可机器解析的模块/测试点/覆盖类型约束。
- 需要明确 min_cases 与 required_case_types。

## 如何使用

1. 阅读需求分析结果，按业务模块拆分 test_points。
2. 每个 test_point 标注 case_types_required 与 min_cases。
3. 严格输出 TestStrategyV1 JSON，勿输出 Markdown。

## 参考

- `prompts/test-strategy-plus.md`：主提示词与 JSON 示例。
