## ADDED Requirements

### Requirement: Skill MUST 支持 ZIP 导出

系统 SHALL 提供导出接口，将指定 skill_id 的 library 目录打包为 ZIP，结构与 ZIP 导入格式兼容。

#### Scenario: 导出已安装 Skill

- **WHEN** 用户对 skill_id=api-test-pytest 发起导出
- **THEN** 系统 MUST 返回 application/zip 文件，且解压后根目录包含 SKILL.md

#### Scenario: 导出不存在 Skill

- **WHEN** skill_id 不存在
- **THEN** 系统 MUST 返回 404

### Requirement: Skill MUST 支持删除

系统 SHALL 提供删除接口，移除 library 中指定 Skill 目录并重载 loader 缓存。

#### Scenario: 删除用户导入 Skill

- **WHEN** 用户删除通过 GitHub 导入的自定义 Skill 且无任何角色引用
- **THEN** 系统 MUST 删除目录、清空缓存，且 list_skills 不再包含该 skill_id

#### Scenario: 删除受保护内置 Skill

- **WHEN** 用户尝试删除 requirements-analysis-plus
- **THEN** 系统 MUST 返回 403 且目录保持不变

#### Scenario: 删除被引用的 Skill

- **WHEN** 某 Skill 仍被 skill_configs 中 enabled 条目引用
- **THEN** 系统 MUST 返回 409 并列出引用角色，不得删除

### Requirement: Skill 导入 MUST 支持 GitHub 与 ZIP 两种方式

系统 SHALL 继续支持 GitHub 一键导入与 ZIP 包导入，均写入 library 并重载缓存。

#### Scenario: GitHub 导入

- **WHEN** 用户提供有效 GitHub tree 链接或 skill_id 简写
- **THEN** 系统 MUST 下载并校验 SKILL.md 后写入 library

#### Scenario: ZIP 导入

- **WHEN** 用户上传含 SKILL.md 的有效 ZIP
- **THEN** 系统 MUST 解析 skill_id 并写入 library，支持 overwrite 参数
