## ADDED Requirements

### Requirement: User SHALL create role-skill binding from UI

The Skills center role configuration tab MUST provide an action to add a new binding between a pipeline role and a skill, persisting via the existing skill-role-config API.

#### Scenario: Add new binding

- **WHEN** user clicks「新增绑定」, selects role `generation`, skill `testcase-writer-plus`, enabled on, and saves
- **THEN** the binding appears in the role table and subsequent pipeline generation uses that skill when enabled

#### Scenario: Prevent duplicate role without override

- **WHEN** user attempts to add a binding for a role that already has a configuration row
- **THEN** the UI prevents duplicate entry or prompts to edit the existing row instead

#### Scenario: Global toggle persists

- **WHEN** user toggles the global QA Skills switch to enabled and the PUT succeeds
- **THEN** the switch remains enabled and the warning banner is hidden after refresh
