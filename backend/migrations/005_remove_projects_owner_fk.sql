-- 检查条件: table=projects fk_exists=owner_id
PRAGMA foreign_keys=OFF;

CREATE TABLE projects_new (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name VARCHAR NOT NULL,
    description VARCHAR,
    status VARCHAR DEFAULT 'draft',
    owner_id INTEGER,
    created_at VARCHAR,
    updated_at VARCHAR
);

INSERT INTO projects_new (id, name, description, status, owner_id, created_at, updated_at)
SELECT id, name, description, status, owner_id, created_at, updated_at FROM projects;

DROP TABLE projects;
ALTER TABLE projects_new RENAME TO projects;
CREATE INDEX ix_projects_name ON projects (name);

PRAGMA foreign_keys=ON;
