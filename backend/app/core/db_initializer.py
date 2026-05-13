from sqlalchemy import inspect, text
from loguru import logger

from app.core.database import async_engine
from app.models import Base
from app.modules.domain import config_center_domain, user_domain


async def init_db() -> None:
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

        def _table_missing_custom_keyword(sync_conn) -> bool:
            inspector = inspect(sync_conn)
            if not inspector.has_table("notification_configs"):
                return False
            columns = {col.get("name") for col in inspector.get_columns("notification_configs")}
            return "custom_keyword" not in columns

        missing_custom_keyword = await conn.run_sync(_table_missing_custom_keyword)
        if missing_custom_keyword:
            await conn.execute(text("ALTER TABLE notification_configs ADD COLUMN custom_keyword VARCHAR DEFAULT ''"))

        def _table_missing_feishu_mindmap_url(sync_conn) -> bool:
            inspector = inspect(sync_conn)
            if not inspector.has_table("tasks"):
                return False
            columns = {col.get("name") for col in inspector.get_columns("tasks")}
            return "feishu_mindmap_url" not in columns

        missing_feishu_mindmap_url = await conn.run_sync(_table_missing_feishu_mindmap_url)
        if missing_feishu_mindmap_url:
            await conn.execute(text("ALTER TABLE tasks ADD COLUMN feishu_mindmap_url VARCHAR"))

        def _employees_missing_columns(sync_conn) -> list:
            inspector = inspect(sync_conn)
            if not inspector.has_table("employees"):
                return []
            columns = {col.get("name") for col in inspector.get_columns("employees")}
            missing = []
            for col in ("role", "level", "hire_date", "sync_source", "sync_id"):
                if col not in columns:
                    missing.append(col)
            return missing

        emp_missing = await conn.run_sync(_employees_missing_columns)
        for col in emp_missing:
            await conn.execute(text(f"ALTER TABLE employees ADD COLUMN {col} VARCHAR"))

        def _requirements_missing_columns(sync_conn) -> list:
            inspector = inspect(sync_conn)
            if not inspector.has_table("requirements"):
                return []
            columns = {col.get("name") for col in inspector.get_columns("requirements")}
            missing = []
            for col in ("product_owner_id", "dev_owner_id", "test_owner_id"):
                if col not in columns:
                    missing.append(col)
            return missing

        req_missing = await conn.run_sync(_requirements_missing_columns)
        for col in req_missing:
            await conn.execute(text(f"ALTER TABLE requirements ADD COLUMN {col} INTEGER"))

        def _projects_owner_has_fk(sync_conn) -> bool:
            inspector = inspect(sync_conn)
            if not inspector.has_table("projects"):
                return False
            fks = inspector.get_foreign_keys("projects")
            for fk in fks:
                if "owner_id" in fk.get("constrained_columns", []):
                    return True
            return False

        needs_projects_migration = await conn.run_sync(_projects_owner_has_fk)
        if needs_projects_migration:
            await conn.execute(text("PRAGMA foreign_keys=OFF"))
            await conn.execute(text("""
                CREATE TABLE projects_new (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name VARCHAR NOT NULL,
                    description VARCHAR,
                    status VARCHAR DEFAULT 'draft',
                    owner_id INTEGER,
                    created_at VARCHAR,
                    updated_at VARCHAR
                )
            """))
            await conn.execute(text("""
                INSERT INTO projects_new (id, name, description, status, owner_id, created_at, updated_at)
                SELECT id, name, description, status, owner_id, created_at, updated_at FROM projects
            """))
            await conn.execute(text("DROP TABLE projects"))
            await conn.execute(text("ALTER TABLE projects_new RENAME TO projects"))
            await conn.execute(text("CREATE INDEX ix_projects_name ON projects (name)"))
            await conn.execute(text("PRAGMA foreign_keys=ON"))
            logger.info("Migrated projects table: removed FK on owner_id, dropped owner_ids column")

        def _test_cases_task_id_has_fk(sync_conn) -> bool:
            inspector = inspect(sync_conn)
            if not inspector.has_table("test_cases"):
                return False
            fks = inspector.get_foreign_keys("test_cases")
            for fk in fks:
                if "task_id" in fk.get("constrained_columns", []):
                    return True
            return False

        needs_tc_migration = await conn.run_sync(_test_cases_task_id_has_fk)
        if needs_tc_migration:
            await conn.execute(text("PRAGMA foreign_keys=OFF"))
            await conn.execute(text("""
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
                )
            """))
            await conn.execute(text("""
                INSERT INTO test_cases_new
                SELECT * FROM test_cases
            """))
            await conn.execute(text("DROP TABLE test_cases"))
            await conn.execute(text("ALTER TABLE test_cases_new RENAME TO test_cases"))
            await conn.execute(text("CREATE INDEX ix_test_cases_project_id ON test_cases (project_id)"))
            await conn.execute(text("CREATE INDEX ix_test_cases_requirement_id ON test_cases (requirement_id)"))
            await conn.execute(text("CREATE INDEX ix_test_cases_task_id ON test_cases (task_id)"))
            await conn.execute(text("CREATE INDEX ix_test_cases_title ON test_cases (title)"))
            await conn.execute(text("PRAGMA foreign_keys=ON"))
            logger.info("Migrated test_cases table: removed FK on task_id")

        def _test_cases_missing_columns(sync_conn) -> list:
            inspector = inspect(sync_conn)
            if not inspector.has_table("test_cases"):
                return []
            columns = {col.get("name") for col in inspector.get_columns("test_cases")}
            missing = []
            if "description" not in columns:
                missing.append(("description", "TEXT"))
            return missing

        tc_missing = await conn.run_sync(_test_cases_missing_columns)
        for col_name, col_type in tc_missing:
            await conn.execute(text(f"ALTER TABLE test_cases ADD COLUMN {col_name} {col_type}"))
            logger.info(f"Migrated test_cases table: added {col_name} column")

    await user_domain.ensure_user("admin", password="123456")
    # await config_center_domain.seed_default_config_center()
    logger.info("SQLAlchemy initialized")
