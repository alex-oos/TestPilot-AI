## ADDED Requirements

### Requirement: Skills center SHALL unwrap API envelope

The Skills center frontend MUST read business payloads from the standard `{ code, data, msg }` response envelope so list, role config, and summary cards display server data.

#### Scenario: Skill list shows library skills

- **WHEN** user opens the Skill list tab and `GET /api/ai/skills` returns `code=0` with skills array
- **THEN** the table displays all loaded skills with skill_id, name, version, and operations

#### Scenario: Role config shows default bindings

- **WHEN** user opens the role config tab and `GET /api/ai/skill-role-config` returns roles
- **THEN** the table displays analysis, generation, and review bindings with effective skill and source

#### Scenario: Summary cards reflect server flags

- **WHEN** skills list API returns `fewshot_enabled=true` and `discover_enabled=true`
- **THEN** the Few-shot and intelligent routing summary cards show「开」
