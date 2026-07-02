"""
数据库初始化与迁移引擎
- 建表: 读取 schema.sql，缺表时自动执行
- 迁移: 扫描 migrations/*.sql，按编号顺序执行，已完成的自动跳过
- 迁移 SQL 首行注释声明前置检查条件，不满足则跳过

迁移文件命名: 001_description.sql, 002_description.sql ...
首行注释支持的条件指令 (可组合, 用空格分隔):
  table=<name>              目标表必须存在
  column_missing=<col>      目标表中该列不存在时才执行
  fk_exists=<col>           目标表中该列存在外键时才执行
"""
import re
from pathlib import Path

from sqlalchemy import inspect, text
from loguru import logger

from app.core.database import async_engine
from app.models import Base
from app.modules.domain import user_domain

_BASE_DIR = Path(__file__).resolve().parent.parent.parent
SCHEMA_SQL_PATH = _BASE_DIR / "schema.sql"
MIGRATIONS_DIR = _BASE_DIR / "migrations"


async def _execute_sql_file(conn, sql_path: Path) -> None:
    """逐条执行一个 SQL 文件中的语句"""
    sql_content = sql_path.read_text(encoding="utf-8")
    for statement in sql_content.split(";"):
        stmt = statement.strip()
        if not stmt:
            continue
        # 去掉语句块前的注释行，避免 CREATE TABLE 被误判为纯注释而跳过
        lines = [ln for ln in stmt.splitlines() if ln.strip() and not ln.strip().startswith("--")]
        stmt = "\n".join(lines).strip()
        if not stmt:
            continue
        try:
            await conn.execute(text(stmt))
        except Exception as e:
            logger.warning(f"SQL 执行跳过 ({sql_path.name}): {stmt[:80]}... | {e}")


def _get_existing_tables(sync_conn) -> set:
    return set(inspect(sync_conn).get_table_names())


def _get_table_columns(sync_conn, table: str) -> set:
    inspector = inspect(sync_conn)
    if not inspector.has_table(table):
        return set()
    return {c["name"] for c in inspector.get_columns(table)}


def _get_table_fk_columns(sync_conn, table: str) -> set:
    inspector = inspect(sync_conn)
    if not inspector.has_table(table):
        return set()
    fk_cols = set()
    for fk in inspector.get_foreign_keys(table):
        fk_cols.update(fk.get("constrained_columns", []))
    return fk_cols


def _parse_conditions(first_line: str) -> dict:
    """
    解析迁移文件首行的条件注释
    格式: -- 检查条件: table=xxx column_missing=yyy fk_exists=zzz
    """
    conditions = {}
    match = re.search(r"检查条件:\s*(.+)", first_line)
    if not match:
        return conditions
    for token in match.group(1).strip().split():
        if "=" in token:
            key, val = token.split("=", 1)
            conditions.setdefault(key.strip(), []).append(val.strip())
    return conditions


async def _should_run_migration(conn, sql_path: Path) -> bool:
    """根据 SQL 文件首行注释中的条件判断是否需要执行"""
    content = sql_path.read_text(encoding="utf-8")
    lines = content.strip().splitlines()
    if not lines:
        return False

    conditions = _parse_conditions(lines[0])
    if not conditions:
        return True

    table = conditions.get("table", [None])[0]
    if not table:
        return True

    existing_tables = await conn.run_sync(_get_existing_tables)
    if table not in existing_tables:
        return False

    for col in conditions.get("column_missing", []):
        columns = await conn.run_sync(lambda sc: _get_table_columns(sc, table))
        if col in columns:
            return False

    for col in conditions.get("fk_exists", []):
        fk_cols = await conn.run_sync(lambda sc: _get_table_fk_columns(sc, table))
        if col not in fk_cols:
            return False

    return True


async def _init_schema(conn) -> None:
    """检测表是否齐全，不齐则用 schema.sql 建表"""
    existing = await conn.run_sync(_get_existing_tables)

    if SCHEMA_SQL_PATH.exists():
        sql_content = SCHEMA_SQL_PATH.read_text(encoding="utf-8")
        expected = set(re.findall(r"CREATE\s+TABLE\s+IF\s+NOT\s+EXISTS\s+(\w+)", sql_content, re.IGNORECASE))
    else:
        expected = set()

    if not expected:
        logger.info("schema.sql 未找到或无有效表定义，使用 SQLAlchemy metadata 创建表")
        await conn.run_sync(Base.metadata.create_all)
        return

    missing = expected - existing
    if missing:
        logger.info(f"检测到 {len(missing)} 张表缺失，执行 schema.sql 初始化")
        await _execute_sql_file(conn, SCHEMA_SQL_PATH)
        updated = await conn.run_sync(_get_existing_tables)
        created = missing & updated
        logger.info(f"schema.sql 初始化完成，新建 {len(created)} 张表")
    else:
        logger.info(f"数据库已包含全部 {len(expected)} 张表，跳过建表")


async def _run_migrations(conn) -> None:
    """
    扫描 migrations/ 目录下所有 .sql 文件，按文件名排序执行。
    使用 _schema_migrations 表记录已执行的迁移，避免重复。
    """
    if not MIGRATIONS_DIR.exists():
        return

    await conn.execute(text("""
        CREATE TABLE IF NOT EXISTS _schema_migrations (
            version VARCHAR PRIMARY KEY,
            applied_at VARCHAR DEFAULT (datetime('now','localtime'))
        )
    """))

    result = await conn.execute(text("SELECT version FROM _schema_migrations"))
    applied = {row[0] for row in result.fetchall()}

    sql_files = sorted(MIGRATIONS_DIR.glob("*.sql"), key=lambda p: p.name)

    for sql_path in sql_files:
        version = sql_path.stem
        if version in applied:
            continue

        should_run = await _should_run_migration(conn, sql_path)
        if not should_run:
            await conn.execute(text("INSERT INTO _schema_migrations (version) VALUES (:v)"), {"v": version})
            logger.debug(f"Migration 跳过 (条件不满足): {sql_path.name}")
            continue

        logger.info(f"执行迁移: {sql_path.name}")
        await _execute_sql_file(conn, sql_path)
        await conn.execute(text("INSERT INTO _schema_migrations (version) VALUES (:v)"), {"v": version})
        logger.info(f"迁移完成: {sql_path.name}")


async def init_db() -> None:
    async with async_engine.begin() as conn:
        await _init_schema(conn)
        await _run_migrations(conn)

    await user_domain.ensure_user("admin", password="123456")
    logger.info("SQLAlchemy initialized")
