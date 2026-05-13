-- 检查条件: table=test_cases fk_exists=task_id
PRAGMA foreign_keys=OFF;

CREATE TABLE test_cases_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER REFERENCES projects(id),
    requirement_id INTEGER REFERENCES requirements(id),
    task_id VARCHAR,
    title VARCHAR NOT NULL,
    module VARCHAR,
    priority VARCHAR DEFAULT 'medium',
    case_type VARCHAR DEFAULT 'functional',
    description TEXT,
    precondition TEXT,
    status VARCHAR DEFAULT 'active',
    source VARCHAR DEFAULT 'manual',
    assignee_id INTEGER REFERENCES users(id),
    last_result VARCHAR,
    created_at VARCHAR,
    updated_at VARCHAR
);

INSERT INTO test_cases_new SELECT * FROM test_cases;
DROP TABLE test_cases;
ALTER TABLE test_cases_new RENAME TO test_cases;
CREATE INDEX ix_test_cases_project_id ON test_cases (project_id);
CREATE INDEX ix_test_cases_requirement_id ON test_cases (requirement_id);
CREATE INDEX ix_test_cases_task_id ON test_cases (task_id);
CREATE INDEX ix_test_cases_title ON test_cases (title);

PRAGMA foreign_keys=ON;
