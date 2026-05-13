-- ============================================================
-- TestPilot-AI 完整建表脚本 (SQLite)
-- 项目启动时如果表不存在则自动执行
-- ============================================================

PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

-- 1. 用户表
CREATE TABLE IF NOT EXISTS users (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    username    VARCHAR NOT NULL UNIQUE,
    password    VARCHAR NOT NULL,
    is_active   BOOLEAN DEFAULT 1,
    created_at  VARCHAR,
    updated_at  VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_users_username ON users (username);

-- 2. 任务表
CREATE TABLE IF NOT EXISTS tasks (
    id                VARCHAR PRIMARY KEY,
    task_name         VARCHAR,
    user_id           INTEGER REFERENCES users(id),
    source_type       VARCHAR,
    doc_url           VARCHAR,
    file_name         VARCHAR,
    file_path         VARCHAR,
    status            VARCHAR NOT NULL,
    status_text       VARCHAR,
    decision_status   VARCHAR,
    decision_by       VARCHAR,
    decision_note     VARCHAR,
    decision_at       VARCHAR,
    error             VARCHAR,
    mindmap           VARCHAR,
    feishu_mindmap_url VARCHAR,
    created_at        VARCHAR,
    updated_at        VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_tasks_task_name ON tasks (task_name);
CREATE INDEX IF NOT EXISTS ix_tasks_status ON tasks (status);

-- 3. 任务详情表
CREATE TABLE IF NOT EXISTS task_details (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id     VARCHAR NOT NULL REFERENCES tasks(id),
    phase_key   VARCHAR NOT NULL,
    phase_label VARCHAR NOT NULL,
    status      VARCHAR NOT NULL,
    data_json   VARCHAR,
    error       VARCHAR,
    created_at  VARCHAR,
    updated_at  VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_task_details_task_id ON task_details (task_id);

-- 4. AI 配置表
CREATE TABLE IF NOT EXISTS ai_configs (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    record_type  VARCHAR NOT NULL,
    config_id    VARCHAR NOT NULL UNIQUE,
    name         VARCHAR DEFAULT '',
    model_type   VARCHAR DEFAULT '',
    api_key      VARCHAR DEFAULT '',
    api_base_url VARCHAR DEFAULT '',
    model_name   VARCHAR DEFAULT '',
    max_tokens   INTEGER DEFAULT 4096,
    temperature  REAL    DEFAULT 0.7,
    top_p        REAL    DEFAULT 0.9,
    enabled      BOOLEAN DEFAULT 1,
    creator      VARCHAR DEFAULT 'admin',
    modifier     VARCHAR DEFAULT 'admin',
    created_at   VARCHAR,
    updated_at   VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_ai_configs_record_type ON ai_configs (record_type);
CREATE INDEX IF NOT EXISTS ix_ai_configs_config_id ON ai_configs (config_id);

-- 5. 角色配置表
CREATE TABLE IF NOT EXISTS role_configs (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    config_id        VARCHAR NOT NULL UNIQUE,
    name             VARCHAR DEFAULT '',
    role_type        VARCHAR NOT NULL,
    mapped_model_name VARCHAR DEFAULT '',
    enabled          BOOLEAN DEFAULT 1,
    creator          VARCHAR DEFAULT 'admin',
    modifier         VARCHAR DEFAULT 'admin',
    created_at       VARCHAR,
    updated_at       VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_role_configs_config_id ON role_configs (config_id);
CREATE INDEX IF NOT EXISTS ix_role_configs_role_type ON role_configs (role_type);

-- 6. 提示词配置表
CREATE TABLE IF NOT EXISTS prompt_configs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    record_type VARCHAR NOT NULL,
    config_id   VARCHAR NOT NULL UNIQUE,
    role        VARCHAR NOT NULL,
    name        VARCHAR DEFAULT '',
    content     VARCHAR DEFAULT '',
    enabled     BOOLEAN DEFAULT 1,
    creator     VARCHAR DEFAULT 'admin',
    created_at  VARCHAR,
    updated_at  VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_prompt_configs_record_type ON prompt_configs (record_type);
CREATE INDEX IF NOT EXISTS ix_prompt_configs_config_id ON prompt_configs (config_id);
CREATE INDEX IF NOT EXISTS ix_prompt_configs_role ON prompt_configs (role);

-- 7. 通知配置表
CREATE TABLE IF NOT EXISTS notification_configs (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    channel         VARCHAR NOT NULL UNIQUE,
    name            VARCHAR DEFAULT '',
    enabled         BOOLEAN DEFAULT 0,
    webhook         VARCHAR DEFAULT '',
    secret          VARCHAR DEFAULT '',
    custom_keyword  VARCHAR DEFAULT '',
    created_at      VARCHAR,
    updated_at      VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_notification_configs_channel ON notification_configs (channel);

-- 8. 生成行为配置表
CREATE TABLE IF NOT EXISTS generation_behavior_configs (
    id                     INTEGER PRIMARY KEY AUTOINCREMENT,
    config_id              VARCHAR NOT NULL UNIQUE,
    name                   VARCHAR DEFAULT '',
    output_mode            VARCHAR DEFAULT 'stream',
    enable_ai_review       BOOLEAN DEFAULT 1,
    review_timeout_seconds INTEGER DEFAULT 1500,
    enabled                BOOLEAN DEFAULT 1,
    created_at             VARCHAR,
    updated_at             VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_generation_behavior_configs_config_id ON generation_behavior_configs (config_id);

-- 9. 项目表
CREATE TABLE IF NOT EXISTS projects (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        VARCHAR NOT NULL,
    description VARCHAR,
    status      VARCHAR DEFAULT 'draft',
    owner_id    INTEGER,
    created_at  VARCHAR,
    updated_at  VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_projects_name ON projects (name);

-- 10. 项目成员表
CREATE TABLE IF NOT EXISTS project_members (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id),
    user_id     INTEGER NOT NULL REFERENCES users(id),
    employee_id INTEGER,
    role        VARCHAR DEFAULT 'tester',
    created_at  VARCHAR,
    updated_at  VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_project_members_project_id ON project_members (project_id);
CREATE INDEX IF NOT EXISTS ix_project_members_user_id ON project_members (user_id);

-- 11. 项目版本表
CREATE TABLE IF NOT EXISTS project_versions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id),
    name        VARCHAR NOT NULL,
    description VARCHAR,
    status      VARCHAR DEFAULT 'planning',
    start_date  VARCHAR,
    end_date    VARCHAR,
    created_at  VARCHAR,
    updated_at  VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_project_versions_project_id ON project_versions (project_id);

-- 12. 团队表
CREATE TABLE IF NOT EXISTS teams (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    name        VARCHAR NOT NULL UNIQUE,
    description VARCHAR,
    leader_id   INTEGER,
    created_at  VARCHAR,
    updated_at  VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_teams_name ON teams (name);

-- 13. 员工表
CREATE TABLE IF NOT EXISTS employees (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id     INTEGER UNIQUE REFERENCES users(id),
    name        VARCHAR NOT NULL,
    email       VARCHAR,
    phone       VARCHAR,
    position    VARCHAR,
    department  VARCHAR,
    team_id     INTEGER REFERENCES teams(id),
    role        VARCHAR DEFAULT 'developer',
    level       VARCHAR DEFAULT 'member',
    hire_date   VARCHAR,
    sync_source VARCHAR,
    sync_id     VARCHAR,
    status      VARCHAR DEFAULT 'active',
    created_at  VARCHAR,
    updated_at  VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_employees_name ON employees (name);

-- 14. 员工技能表
CREATE TABLE IF NOT EXISTS employee_skills (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    skill_name  VARCHAR NOT NULL,
    level       VARCHAR DEFAULT 'intermediate',
    created_at  VARCHAR,
    updated_at  VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_employee_skills_employee_id ON employee_skills (employee_id);

-- 15. 排班表
CREATE TABLE IF NOT EXISTS schedules (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id   INTEGER NOT NULL REFERENCES employees(id),
    project_id    INTEGER REFERENCES projects(id),
    title         VARCHAR NOT NULL,
    schedule_date VARCHAR NOT NULL,
    start_time    VARCHAR,
    end_time      VARCHAR,
    hours         VARCHAR,
    schedule_type VARCHAR DEFAULT 'work',
    description   VARCHAR,
    created_at    VARCHAR,
    updated_at    VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_schedules_employee_id ON schedules (employee_id);
CREATE INDEX IF NOT EXISTS ix_schedules_schedule_date ON schedules (schedule_date);

-- 16. 请假记录表
CREATE TABLE IF NOT EXISTS leave_records (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL REFERENCES employees(id),
    leave_type  VARCHAR NOT NULL,
    start_date  VARCHAR NOT NULL,
    end_date    VARCHAR NOT NULL,
    status      VARCHAR DEFAULT 'pending',
    reason      VARCHAR,
    created_at  VARCHAR,
    updated_at  VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_leave_records_employee_id ON leave_records (employee_id);

-- 17. 需求表
CREATE TABLE IF NOT EXISTS requirements (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id       INTEGER REFERENCES projects(id),
    title            VARCHAR NOT NULL,
    description      TEXT,
    priority         VARCHAR DEFAULT 'medium',
    status           VARCHAR DEFAULT 'requirement_review',
    req_type         VARCHAR DEFAULT 'functional',
    version_id       INTEGER REFERENCES project_versions(id),
    assignee_id      INTEGER REFERENCES users(id),
    source           VARCHAR,
    product_owner_id INTEGER,
    dev_owner_id     INTEGER,
    test_owner_id    INTEGER,
    created_at       VARCHAR,
    updated_at       VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_requirements_project_id ON requirements (project_id);
CREATE INDEX IF NOT EXISTS ix_requirements_title ON requirements (title);

-- 18. 需求追溯表
CREATE TABLE IF NOT EXISTS requirement_traces (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    requirement_id INTEGER NOT NULL REFERENCES requirements(id),
    target_type    VARCHAR NOT NULL,
    target_id      VARCHAR NOT NULL,
    relation       VARCHAR DEFAULT 'covers',
    created_at     VARCHAR,
    updated_at     VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_requirement_traces_requirement_id ON requirement_traces (requirement_id);

-- 19. 需求节点人员表
CREATE TABLE IF NOT EXISTS requirement_node_members (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    requirement_id INTEGER NOT NULL REFERENCES requirements(id),
    node           VARCHAR NOT NULL,
    role           VARCHAR NOT NULL,
    employee_id    INTEGER NOT NULL REFERENCES employees(id),
    planned_time   VARCHAR,
    created_at     VARCHAR,
    updated_at     VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_requirement_node_members_requirement_id ON requirement_node_members (requirement_id);
CREATE INDEX IF NOT EXISTS ix_requirement_node_members_node ON requirement_node_members (node);

-- 20. 测试用例表
CREATE TABLE IF NOT EXISTS test_cases (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id     INTEGER REFERENCES projects(id),
    requirement_id INTEGER REFERENCES requirements(id),
    task_id        VARCHAR,
    title          VARCHAR NOT NULL,
    module         VARCHAR,
    priority       VARCHAR DEFAULT 'medium',
    case_type      VARCHAR DEFAULT 'functional',
    description    TEXT,
    precondition   TEXT,
    status         VARCHAR DEFAULT 'active',
    source         VARCHAR DEFAULT 'manual',
    assignee_id    INTEGER REFERENCES users(id),
    last_result    VARCHAR,
    created_at     VARCHAR,
    updated_at     VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_test_cases_project_id ON test_cases (project_id);
CREATE INDEX IF NOT EXISTS ix_test_cases_requirement_id ON test_cases (requirement_id);
CREATE INDEX IF NOT EXISTS ix_test_cases_task_id ON test_cases (task_id);
CREATE INDEX IF NOT EXISTS ix_test_cases_title ON test_cases (title);

-- 21. 测试用例步骤表
CREATE TABLE IF NOT EXISTS test_case_steps (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    test_case_id    INTEGER NOT NULL REFERENCES test_cases(id),
    "order"         INTEGER NOT NULL,
    action          TEXT NOT NULL,
    expected_result TEXT,
    test_data       TEXT,
    created_at      VARCHAR,
    updated_at      VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_test_case_steps_test_case_id ON test_case_steps (test_case_id);

-- 22. 测试执行表
CREATE TABLE IF NOT EXISTS test_executions (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    title         VARCHAR NOT NULL,
    project_id    INTEGER REFERENCES projects(id),
    plan_type     VARCHAR DEFAULT 'manual',
    status        VARCHAR DEFAULT 'pending',
    total_cases   INTEGER DEFAULT 0,
    passed_cases  INTEGER DEFAULT 0,
    failed_cases  INTEGER DEFAULT 0,
    blocked_cases INTEGER DEFAULT 0,
    skipped_cases INTEGER DEFAULT 0,
    executor_id   INTEGER REFERENCES users(id),
    started_at    VARCHAR,
    completed_at  VARCHAR,
    created_at    VARCHAR,
    updated_at    VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_test_executions_title ON test_executions (title);
CREATE INDEX IF NOT EXISTS ix_test_executions_project_id ON test_executions (project_id);

-- 23. 测试执行结果表
CREATE TABLE IF NOT EXISTS test_execution_results (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id  INTEGER NOT NULL REFERENCES test_executions(id),
    test_case_id  INTEGER NOT NULL REFERENCES test_cases(id),
    status        VARCHAR DEFAULT 'pending',
    actual_result TEXT,
    notes         TEXT,
    executed_at   VARCHAR,
    executor_id   INTEGER REFERENCES users(id),
    created_at    VARCHAR,
    updated_at    VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_test_execution_results_execution_id ON test_execution_results (execution_id);
CREATE INDEX IF NOT EXISTS ix_test_execution_results_test_case_id ON test_execution_results (test_case_id);

-- 24. 测试报告表
CREATE TABLE IF NOT EXISTS test_reports (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id  INTEGER NOT NULL REFERENCES test_executions(id),
    title         VARCHAR NOT NULL,
    summary       TEXT,
    total_cases   INTEGER DEFAULT 0,
    passed_cases  INTEGER DEFAULT 0,
    failed_cases  INTEGER DEFAULT 0,
    blocked_cases INTEGER DEFAULT 0,
    skipped_cases INTEGER DEFAULT 0,
    pass_rate     REAL,
    generated_at  VARCHAR,
    created_at    VARCHAR,
    updated_at    VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_test_reports_execution_id ON test_reports (execution_id);
CREATE INDEX IF NOT EXISTS ix_test_reports_title ON test_reports (title);

-- 25. API 接口表
CREATE TABLE IF NOT EXISTS api_endpoints (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id    INTEGER REFERENCES projects(id),
    name          VARCHAR NOT NULL,
    method        VARCHAR NOT NULL,
    path          VARCHAR NOT NULL,
    description   VARCHAR,
    headers_json  TEXT,
    body_json     TEXT,
    response_json TEXT,
    tags          VARCHAR,
    created_at    VARCHAR,
    updated_at    VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_api_endpoints_project_id ON api_endpoints (project_id);

-- 26. API 环境表
CREATE TABLE IF NOT EXISTS api_environments (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id     INTEGER REFERENCES projects(id),
    name           VARCHAR NOT NULL,
    base_url       VARCHAR NOT NULL,
    variables_json TEXT,
    is_default     VARCHAR DEFAULT 'false',
    created_at     VARCHAR,
    updated_at     VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_api_environments_project_id ON api_environments (project_id);

-- 27. API 测试用例表
CREATE TABLE IF NOT EXISTS api_test_cases (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    endpoint_id INTEGER REFERENCES api_endpoints(id),
    project_id  INTEGER REFERENCES projects(id),
    name        VARCHAR NOT NULL,
    description VARCHAR,
    priority    VARCHAR DEFAULT 'medium',
    status      VARCHAR DEFAULT 'active',
    created_at  VARCHAR,
    updated_at  VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_api_test_cases_endpoint_id ON api_test_cases (endpoint_id);
CREATE INDEX IF NOT EXISTS ix_api_test_cases_project_id ON api_test_cases (project_id);

-- 28. API 测试步骤表
CREATE TABLE IF NOT EXISTS api_test_steps (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    test_case_id    INTEGER NOT NULL REFERENCES api_test_cases(id),
    "order"         INTEGER NOT NULL,
    name            VARCHAR NOT NULL,
    method          VARCHAR NOT NULL,
    url             VARCHAR NOT NULL,
    headers_json    TEXT,
    body_json       TEXT,
    extractors_json TEXT,
    assertions_json TEXT,
    created_at      VARCHAR,
    updated_at      VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_api_test_steps_test_case_id ON api_test_steps (test_case_id);

-- 29. API 执行记录表
CREATE TABLE IF NOT EXISTS api_executions (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id     INTEGER REFERENCES projects(id),
    environment_id INTEGER REFERENCES api_environments(id),
    status         VARCHAR DEFAULT 'running',
    total          INTEGER DEFAULT 0,
    passed         INTEGER DEFAULT 0,
    failed         INTEGER DEFAULT 0,
    duration_ms    INTEGER,
    trigger_type   VARCHAR DEFAULT 'manual',
    created_at     VARCHAR,
    updated_at     VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_api_executions_project_id ON api_executions (project_id);

-- 30. API 执行结果表
CREATE TABLE IF NOT EXISTS api_execution_results (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id  INTEGER NOT NULL REFERENCES api_executions(id),
    test_case_id  INTEGER REFERENCES api_test_cases(id),
    status        VARCHAR NOT NULL,
    duration_ms   INTEGER,
    response_code INTEGER,
    response_body TEXT,
    error         TEXT,
    created_at    VARCHAR,
    updated_at    VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_api_execution_results_execution_id ON api_execution_results (execution_id);

-- 31. 性能测试场景表
CREATE TABLE IF NOT EXISTS perf_scenarios (
    id               INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id       INTEGER REFERENCES projects(id),
    name             VARCHAR NOT NULL,
    description      TEXT,
    test_type        VARCHAR DEFAULT 'load',
    target_url       VARCHAR,
    concurrency      INTEGER,
    duration_seconds INTEGER,
    ramp_up_seconds  INTEGER,
    status           VARCHAR DEFAULT 'draft',
    created_at       VARCHAR,
    updated_at       VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_perf_scenarios_project_id ON perf_scenarios (project_id);
CREATE INDEX IF NOT EXISTS ix_perf_scenarios_name ON perf_scenarios (name);

-- 32. 性能测试脚本表
CREATE TABLE IF NOT EXISTS perf_scripts (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id INTEGER NOT NULL REFERENCES perf_scenarios(id),
    name        VARCHAR NOT NULL,
    script_type VARCHAR DEFAULT 'k6',
    content     TEXT,
    file_path   VARCHAR,
    created_at  VARCHAR,
    updated_at  VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_perf_scripts_scenario_id ON perf_scripts (scenario_id);

-- 33. 性能测试执行表
CREATE TABLE IF NOT EXISTS perf_executions (
    id           INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id  INTEGER NOT NULL REFERENCES perf_scenarios(id),
    status       VARCHAR DEFAULT 'running',
    started_at   VARCHAR,
    finished_at  VARCHAR,
    summary_json TEXT,
    created_at   VARCHAR,
    updated_at   VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_perf_executions_scenario_id ON perf_executions (scenario_id);

-- 34. 性能测试结果表
CREATE TABLE IF NOT EXISTS perf_results (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    execution_id    INTEGER NOT NULL REFERENCES perf_executions(id),
    timestamp       VARCHAR NOT NULL,
    avg_response_ms REAL,
    p95_response_ms REAL,
    p99_response_ms REAL,
    tps             REAL,
    error_rate      REAL,
    concurrent_users INTEGER,
    created_at      VARCHAR,
    updated_at      VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_perf_results_execution_id ON perf_results (execution_id);

-- 35. 性能基线表
CREATE TABLE IF NOT EXISTS perf_baselines (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    scenario_id     INTEGER NOT NULL REFERENCES perf_scenarios(id),
    name            VARCHAR NOT NULL,
    avg_response_ms REAL,
    p95_response_ms REAL,
    max_tps         REAL,
    max_error_rate  REAL,
    created_at      VARCHAR,
    updated_at      VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_perf_baselines_scenario_id ON perf_baselines (scenario_id);

-- 36. 缺陷表
CREATE TABLE IF NOT EXISTS defects (
    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id         INTEGER REFERENCES projects(id),
    title              VARCHAR NOT NULL,
    description        TEXT,
    severity           VARCHAR DEFAULT 'medium',
    priority           VARCHAR DEFAULT 'medium',
    status             VARCHAR DEFAULT 'open',
    defect_type        VARCHAR DEFAULT 'functional',
    module             VARCHAR,
    reporter_id        INTEGER REFERENCES users(id),
    assignee_id        INTEGER REFERENCES users(id),
    requirement_id     INTEGER REFERENCES requirements(id),
    version_id         INTEGER REFERENCES project_versions(id),
    environment        VARCHAR,
    steps_to_reproduce TEXT,
    expected_result    TEXT,
    actual_result      TEXT,
    resolved_at        VARCHAR,
    closed_at          VARCHAR,
    created_at         VARCHAR,
    updated_at         VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_defects_project_id ON defects (project_id);
CREATE INDEX IF NOT EXISTS ix_defects_title ON defects (title);

-- 37. 缺陷评论表
CREATE TABLE IF NOT EXISTS defect_comments (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    defect_id INTEGER NOT NULL REFERENCES defects(id),
    user_id   INTEGER REFERENCES users(id),
    content   TEXT NOT NULL,
    created_at VARCHAR,
    updated_at VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_defect_comments_defect_id ON defect_comments (defect_id);

-- 38. 缺陷附件表
CREATE TABLE IF NOT EXISTS defect_attachments (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    defect_id INTEGER NOT NULL REFERENCES defects(id),
    file_name VARCHAR NOT NULL,
    file_path VARCHAR NOT NULL,
    file_type VARCHAR,
    file_size INTEGER,
    created_at VARCHAR,
    updated_at VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_defect_attachments_defect_id ON defect_attachments (defect_id);

-- 39. 缺陷历史表
CREATE TABLE IF NOT EXISTS defect_history (
    id        INTEGER PRIMARY KEY AUTOINCREMENT,
    defect_id INTEGER NOT NULL REFERENCES defects(id),
    user_id   INTEGER REFERENCES users(id),
    field     VARCHAR NOT NULL,
    old_value VARCHAR,
    new_value VARCHAR,
    created_at VARCHAR,
    updated_at VARCHAR
);
CREATE INDEX IF NOT EXISTS ix_defect_history_defect_id ON defect_history (defect_id);
