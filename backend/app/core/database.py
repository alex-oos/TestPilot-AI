import json
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import settings
from app.models import Base
from app.repositories import ConfigRepository, TaskRepository, UserRepository
from app.security.password_hasher import hash_password


_DB_PATH = Path(settings.SQLITE_DB_PATH)
_BEIJING_TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")
_DB_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def _utc_now() -> str:
    return datetime.now(_BEIJING_TZ).strftime(_DB_TIME_FORMAT)


def _to_beijing_time_text(value: Any) -> str:
    if value is None:
        return ""

    dt: Optional[datetime] = None
    if isinstance(value, datetime):
        dt = value
    else:
        text_value = str(value).strip()
        if not text_value:
            return ""
        parse_value = text_value[:-1] + "+00:00" if text_value.endswith("Z") else text_value
        try:
            dt = datetime.fromisoformat(parse_value)
        except ValueError:
            for fmt in (_DB_TIME_FORMAT, "%Y-%m-%d %H:%M:%S.%f"):
                try:
                    dt = datetime.strptime(text_value, fmt)
                    break
                except ValueError:
                    continue
            if dt is None:
                return text_value

    if dt.tzinfo is None:
        return dt.strftime(_DB_TIME_FORMAT)
    return dt.astimezone(_BEIJING_TZ).strftime(_DB_TIME_FORMAT)


def _build_engine():
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(
        f"sqlite:///{_DB_PATH}",
        future=True,
        connect_args={"check_same_thread": False},
    )


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


@contextmanager
def transactional_session() -> Session:
    with SessionLocal() as db:
        with db.begin():
            yield db


def init_db() -> None:
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    required = {
        "users",
        "tasks",
        "task_details",
        "ai_configs",
        "role_configs",
        "prompt_configs",
        "notification_configs",
        "generation_behavior_configs",
    }
    missing = required - existing
    if missing:
        logger.info(f"Missing tables detected: {sorted(missing)}. Creating...")

    Base.metadata.create_all(bind=engine, checkfirst=True)
    _migrate_config_tables_schema()
    _ensure_role_configs_defaults()
    _migrate_legacy_columns()

    seed_default_user()
    seed_default_config_center()
    logger.info(f"SQLAlchemy initialized: {_DB_PATH}")


def _migrate_config_tables_schema() -> None:
    _migrate_role_configs_schema()
    _migrate_notification_configs_remove_business_types()
    inspector = inspect(engine)
    table_columns = {
        "ai_configs": {
            "record_type",
            "config_id",
            "name",
            "model_type",
            "api_key",
            "api_base_url",
            "model_name",
            "max_tokens",
            "temperature",
            "top_p",
            "enabled",
            "created_at",
            "updated_at",
        },
        "role_configs": {
            "config_id",
            "name",
            "role_type",
            "mapped_model_name",
            "enabled",
            "creator",
            "modifier",
            "created_at",
            "updated_at",
        },
        "prompt_configs": {"record_type", "config_id", "role", "content"},
        "notification_configs": {"channel", "enabled", "webhook"},
        "generation_behavior_configs": {"config_id", "output_mode", "enable_ai_review"},
    }

    need_recreate = []
    for table, expected_columns in table_columns.items():
        existing_tables = set(inspector.get_table_names())
        if table not in existing_tables:
            continue
        current_columns = {col["name"] for col in inspector.get_columns(table)}
        if not expected_columns.issubset(current_columns):
            need_recreate.append(table)

    if not need_recreate:
        _migrate_ai_configs_remove_role()
        return

    with engine.begin() as conn:
        for table in need_recreate:
            logger.info(f"Recreating config table with new schema: {table}")
            conn.execute(text(f"DROP TABLE IF EXISTS {table}"))

    Base.metadata.create_all(bind=engine, checkfirst=True)
    _migrate_ai_configs_remove_role()


def _migrate_notification_configs_remove_business_types() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "notification_configs" not in tables:
        return

    current_columns = {col["name"] for col in inspector.get_columns("notification_configs")}
    if "business_types" not in current_columns:
        return

    logger.info("Migrating notification_configs schema: removing business_types column")
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE notification_configs RENAME TO notification_configs_legacy"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS notification_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                channel VARCHAR NOT NULL,
                name VARCHAR DEFAULT '',
                enabled BOOLEAN DEFAULT 0,
                webhook VARCHAR DEFAULT '',
                secret VARCHAR DEFAULT '',
                created_at VARCHAR,
                updated_at VARCHAR
            )
        """))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_notification_configs_channel ON notification_configs (channel)"))

        conn.execute(text("""
            INSERT INTO notification_configs (channel, name, enabled, webhook, secret, created_at, updated_at)
            SELECT
                COALESCE(channel, ''),
                COALESCE(name, ''),
                COALESCE(enabled, 0),
                COALESCE(webhook, ''),
                COALESCE(secret, ''),
                COALESCE(created_at, ''),
                COALESCE(updated_at, '')
            FROM notification_configs_legacy
        """))

        conn.execute(text("DROP TABLE IF EXISTS notification_configs_legacy"))


def _migrate_role_configs_schema() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "role_configs" not in tables and "role_model_mappings" not in tables:
        return

    logger.info("Migrating role config tables to latest schema")
    with engine.begin() as conn:
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS role_configs_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                config_id VARCHAR NOT NULL UNIQUE,
                name VARCHAR NOT NULL DEFAULT '',
                role_type VARCHAR NOT NULL,
                mapped_model_name VARCHAR NOT NULL DEFAULT '',
                enabled BOOLEAN NOT NULL DEFAULT 1,
                creator VARCHAR NOT NULL DEFAULT 'admin',
                modifier VARCHAR NOT NULL DEFAULT 'admin',
                created_at VARCHAR NOT NULL,
                updated_at VARCHAR NOT NULL
            )
        """))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_role_configs_new_role_type ON role_configs_new (role_type)"))

        if "role_configs" in tables:
            current_columns = {col["name"] for col in inspector.get_columns("role_configs")}
            if {"config_id", "name", "role_type", "mapped_model_name", "enabled", "creator", "modifier", "created_at", "updated_at"}.issubset(current_columns):
                conn.execute(text("""
                    INSERT OR REPLACE INTO role_configs_new
                    (config_id, name, role_type, mapped_model_name, enabled, creator, modifier, created_at, updated_at)
                    SELECT config_id, name, role_type, mapped_model_name, enabled, creator, modifier, created_at, updated_at
                    FROM role_configs
                """))
            else:
                source_role_col = "role_type" if "role_type" in current_columns else "role"
                source_model_col = "mapped_model_name" if "mapped_model_name" in current_columns else "model_name"
                conn.execute(text(f"""
                    INSERT OR REPLACE INTO role_configs_new
                    (config_id, name, role_type, mapped_model_name, enabled, creator, modifier, created_at, updated_at)
                    SELECT
                        'legacy-' || COALESCE({source_role_col}, ''),
                        CASE COALESCE({source_role_col}, '')
                            WHEN 'analysis' THEN '默认需求分析专家配置'
                            WHEN 'generation' THEN '默认测试用例编写专家配置'
                            WHEN 'review' THEN '默认测试用例评审专家配置'
                            ELSE '默认角色配置'
                        END,
                        COALESCE({source_role_col}, ''),
                        COALESCE({source_model_col}, ''),
                        1,
                        'admin',
                        'admin',
                        COALESCE(created_at, ''),
                        COALESCE(updated_at, '')
                    FROM role_configs
                    WHERE COALESCE({source_role_col}, '') IN ('analysis', 'generation', 'review')
                """))

        if "role_model_mappings" in tables:
            conn.execute(text("""
                INSERT OR REPLACE INTO role_configs_new
                (config_id, name, role_type, mapped_model_name, enabled, creator, modifier, created_at, updated_at)
                SELECT
                    'legacy-' || COALESCE(role, ''),
                    CASE COALESCE(role, '')
                        WHEN 'analysis' THEN '默认需求分析专家配置'
                        WHEN 'generation' THEN '默认测试用例编写专家配置'
                        WHEN 'review' THEN '默认测试用例评审专家配置'
                        ELSE '默认角色配置'
                    END,
                    COALESCE(role, ''),
                    COALESCE(model_name, ''),
                    1,
                    'admin',
                    'admin',
                    COALESCE(created_at, ''),
                    COALESCE(updated_at, '')
                FROM role_model_mappings
                WHERE COALESCE(role, '') IN ('analysis', 'generation', 'review')
            """))

        conn.execute(text("DROP TABLE IF EXISTS role_model_mappings"))
        conn.execute(text("DROP TABLE IF EXISTS role_configs"))
        conn.execute(text("ALTER TABLE role_configs_new RENAME TO role_configs"))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_role_configs_config_id ON role_configs (config_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_role_configs_role_type ON role_configs (role_type)"))


def _ensure_role_configs_defaults() -> None:
    now = _utc_now()
    with transactional_session() as db:
        existing_roles = {
            _normalize_role_type(str(item.role_type or ""))
            for item in ConfigRepository.list_role_configs(db)
        }
        for role, name in (
            ("analysis", "默认需求分析专家配置"),
            ("generation", "默认测试用例编写专家配置"),
            ("review", "默认测试用例评审专家配置"),
        ):
            if role in existing_roles:
                continue
            ConfigRepository.create_role_config(
                db,
                config_id=f"default-{role}-role-config",
                name=name,
                role_type=role,
                mapped_model_name=settings.LLM_MODEL,
                enabled=True,
                creator="admin",
                modifier="admin",
                created_at=now,
                updated_at=now,
            )


def _migrate_ai_configs_remove_role() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "ai_configs" not in tables:
        return

    ai_columns = {col["name"] for col in inspector.get_columns("ai_configs")}
    has_legacy_role = "role" in ai_columns

    if not has_legacy_role:
        return

    logger.info("Migrating ai_configs schema: removing legacy role column and moving defaults to role_configs")
    with engine.begin() as conn:
        conn.execute(text("ALTER TABLE ai_configs RENAME TO ai_configs_legacy"))
        conn.execute(text("""
            CREATE TABLE IF NOT EXISTS ai_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                record_type VARCHAR,
                config_id VARCHAR,
                name VARCHAR DEFAULT '',
                model_type VARCHAR DEFAULT '',
                api_key VARCHAR DEFAULT '',
                api_base_url VARCHAR DEFAULT '',
                model_name VARCHAR DEFAULT '',
                max_tokens INTEGER DEFAULT 4096,
                temperature FLOAT DEFAULT 0.7,
                top_p FLOAT DEFAULT 0.9,
                enabled BOOLEAN DEFAULT 1,
                created_at VARCHAR,
                updated_at VARCHAR
            )
        """))
        conn.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_ai_configs_config_id ON ai_configs (config_id)"))
        conn.execute(text("CREATE INDEX IF NOT EXISTS ix_ai_configs_record_type ON ai_configs (record_type)"))

        conn.execute(text("""
            INSERT INTO ai_configs (
                record_type, config_id, name, model_type, api_key, api_base_url, model_name,
                max_tokens, temperature, top_p, enabled, created_at, updated_at
            )
            SELECT
                COALESCE(record_type, 'model'),
                config_id,
                COALESCE(name, ''),
                COALESCE(model_type, ''),
                COALESCE(api_key, ''),
                COALESCE(api_base_url, ''),
                COALESCE(model_name, ''),
                COALESCE(max_tokens, 4096),
                COALESCE(temperature, 0.7),
                COALESCE(top_p, 0.9),
                COALESCE(enabled, 1),
                COALESCE(created_at, ''),
                COALESCE(updated_at, '')
            FROM ai_configs_legacy
            WHERE COALESCE(record_type, '') = 'model'
        """))

        conn.execute(text("""
            INSERT OR REPLACE INTO role_configs
            (config_id, name, role_type, mapped_model_name, enabled, creator, modifier, created_at, updated_at)
            SELECT
                'legacy-' || role,
                CASE role
                    WHEN 'analysis' THEN '默认需求分析专家配置'
                    WHEN 'generation' THEN '默认测试用例编写专家配置'
                    WHEN 'review' THEN '默认测试用例评审专家配置'
                    ELSE '默认角色配置'
                END,
                role,
                MAX(COALESCE(model_name, '')),
                1,
                'admin',
                'admin',
                MAX(COALESCE(created_at, '')),
                MAX(COALESCE(updated_at, created_at, ''))
            FROM ai_configs_legacy
            WHERE COALESCE(record_type, '') = 'default'
              AND role IN ('analysis', 'generation', 'review')
            GROUP BY role
        """))

        conn.execute(text("DROP TABLE IF EXISTS ai_configs_legacy"))


def _migrate_legacy_columns() -> None:
    inspector = inspect(engine)
    task_columns = {col["name"] for col in inspector.get_columns("tasks")}
    statements = []
    if "task_name" not in task_columns:
        statements.append("ALTER TABLE tasks ADD COLUMN task_name TEXT")
    if "file_name" not in task_columns:
        statements.append("ALTER TABLE tasks ADD COLUMN file_name TEXT")
    if "file_path" not in task_columns:
        statements.append("ALTER TABLE tasks ADD COLUMN file_path TEXT")
    if "decision_status" not in task_columns:
        statements.append("ALTER TABLE tasks ADD COLUMN decision_status TEXT")
    if "decision_by" not in task_columns:
        statements.append("ALTER TABLE tasks ADD COLUMN decision_by TEXT")
    if "decision_note" not in task_columns:
        statements.append("ALTER TABLE tasks ADD COLUMN decision_note TEXT")
    if "decision_at" not in task_columns:
        statements.append("ALTER TABLE tasks ADD COLUMN decision_at TEXT")

    if not statements:
        return

    with engine.begin() as conn:
        for sql in statements:
            logger.info(f"Applying migration: {sql}")
            conn.execute(text(sql))


def seed_default_user() -> None:
    now = _utc_now()
    with transactional_session() as db:
        existing = UserRepository.get_by_username(db, "admin")
        if existing:
            return
        UserRepository.create(db, username="admin", password=hash_password("123456"), created_at=now, updated_at=now)


def _default_config_center() -> Dict[str, Any]:
    defaults = {
        "role_configs": {
            "analysis": settings.LLM_MODEL,
            "generation": settings.LLM_MODEL,
            "review": settings.LLM_MODEL,
        },
        "ai_model_configs": [],
        "prompts": {
            "analysis": (
                "你是一个资深的软件需求分析师。请阅读用户上传的项目文档内容，提取关键功能点、业务流程、"
                "边界与限制条件，并使用清晰 Markdown 输出。"
            ),
            "generation": (
                "你是一个资深的软件测试工程师。请基于输入策略生成结构化测试用例，覆盖正常、边界、异常、"
                "兼容与回归场景，并保证输出可解析。"
            ),
            "review": (
                "你是一个资深的软件质量保证专家。请对生成的测试用例做质量评审，指出问题、优化建议、缺失场景，"
                "并给出质量评分与总结。"
            ),
        },
        "notifications": {
            "feishu": {
                "name": "",
                "enabled": False,
                "webhook": "",
                "secret": "",
            },
            "dingtalk": {
                "name": "",
                "enabled": False,
                "webhook": "",
                "secret": "",
            },
            "wecom": {
                "name": "",
                "enabled": False,
                "webhook": "",
                "secret": "",
            },
        },
    }
    defaults["prompt_configs"] = _build_default_prompt_configs(defaults["prompts"])
    defaults["role_config_items"] = _build_default_role_config_items(defaults["role_configs"])
    defaults["generation_behavior_configs"] = _build_default_generation_behavior_configs()
    return defaults


def _role_type_display_name(role_type: str) -> str:
    if role_type == "analysis":
        return "需求分析专家"
    if role_type == "generation":
        return "测试用例编写专家"
    if role_type == "review":
        return "测试用例评审专家"
    return role_type


def _build_default_role_config_items(role_configs: Dict[str, str]) -> List[Dict[str, Any]]:
    now = _utc_now()
    items: List[Dict[str, Any]] = []
    for role in ("analysis", "generation", "review"):
        items.append(
            {
                "id": f"default-{role}-role-config",
                "name": f"默认{_role_type_display_name(role)}配置",
                "role_type": role,
                "mapped_model_name": str((role_configs or {}).get(role) or settings.LLM_MODEL),
                "enabled": True,
                "created_at": now,
                "updated_at": now,
                "creator": "admin",
                "modifier": "admin",
            }
        )
    return items


def _normalize_prompt_type(prompt_type: str) -> str:
    value = (prompt_type or "").strip().lower()
    if value in {"analysis", "需求分析", "需求分析角色"}:
        return "analysis"
    if value in {"generation", "用例编写", "测试用例编写", "测试用例编写角色"}:
        return "generation"
    if value in {"review", "用例评审", "测试用例评审", "测试用例评审角色"}:
        return "review"
    return value or "generation"


def _build_default_prompt_configs(prompts: Dict[str, str]) -> List[Dict[str, Any]]:
    now = _utc_now()
    return [
        {
            "id": "default-analysis-prompt",
            "name": "默认需求分析提示词",
            "role": "analysis",
            "prompt_type": "analysis",
            "content": prompts.get("analysis") or "",
            "enabled": True,
            "created_at": now,
            "updated_at": now,
            "creator": "admin",
        },
        {
            "id": "default-generation-prompt",
            "name": "默认用例编写提示词",
            "role": "generation",
            "prompt_type": "generation",
            "content": prompts.get("generation") or "",
            "enabled": True,
            "created_at": now,
            "updated_at": now,
            "creator": "admin",
        },
        {
            "id": "default-review-prompt",
            "name": "默认用例评审提示词",
            "role": "review",
            "prompt_type": "review",
            "content": prompts.get("review") or "",
            "enabled": True,
            "created_at": now,
            "updated_at": now,
            "creator": "admin",
        },
    ]


def _build_default_generation_behavior_configs() -> List[Dict[str, Any]]:
    now = _utc_now()
    return [
        {
            "id": "default-generation-behavior",
            "name": "默认生成配置",
            "output_mode": "stream",
            "enable_ai_review": True,
            "review_timeout_seconds": 1500,
            "enabled": True,
            "created_at": now,
            "updated_at": now,
        }
    ]


def _normalize_ai_model_configs(items: Any) -> List[Dict[str, Any]]:
    if not isinstance(items, list):
        return []

    normalized: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "id": str(item.get("id") or ""),
                "name": str(item.get("name") or ""),
                "model_type": str(item.get("model_type") or "other"),
                "api_key": str(item.get("api_key") or ""),
                "api_base_url": str(item.get("api_base_url") or settings.LLM_BASE_URL),
                "model_name": str(item.get("model_name") or settings.LLM_MODEL),
                "max_tokens": int(item.get("max_tokens") or 4096),
                "temperature": float(item.get("temperature") if item.get("temperature") is not None else 0.7),
                "top_p": float(item.get("top_p") if item.get("top_p") is not None else 0.9),
                "enabled": bool(item.get("enabled", True)),
                "created_at": _to_beijing_time_text(item.get("created_at")) or _utc_now(),
            }
        )
    return normalized


def _normalize_role_type(value: str) -> str:
    role = (value or "").strip().lower()
    if role in {"analysis", "需求分析", "需求分析角色", "需求分析专家"}:
        return "analysis"
    if role in {"generation", "用例编写", "测试用例编写", "测试用例编写角色", "测试用例编写专家"}:
        return "generation"
    if role in {"review", "用例评审", "测试用例评审", "测试用例评审角色", "测试用例评审专家"}:
        return "review"
    return role if role in {"analysis", "generation", "review"} else "generation"


def _normalize_role_config_items(items: Any, fallback_map: Dict[str, str]) -> List[Dict[str, Any]]:
    if not isinstance(items, list):
        return _build_default_role_config_items(fallback_map)

    normalized: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        role_type = _normalize_role_type(str(item.get("role_type") or item.get("role") or ""))
        now = _utc_now()
        normalized.append(
            {
                "id": str(item.get("id") or item.get("config_id") or ""),
                "name": str(item.get("name") or f"{_role_type_display_name(role_type)}配置"),
                "role_type": role_type,
                "mapped_model_name": str(item.get("mapped_model_name") or item.get("model_name") or fallback_map.get(role_type) or settings.LLM_MODEL),
                "enabled": bool(item.get("enabled", True)),
                "created_at": _to_beijing_time_text(item.get("created_at")) or now,
                "updated_at": _to_beijing_time_text(item.get("updated_at")) or now,
                "creator": str(item.get("creator") or "admin"),
                "modifier": str(item.get("modifier") or item.get("creator") or "admin"),
            }
        )
    if not normalized:
        return _build_default_role_config_items(fallback_map)
    return normalized


def _normalize_prompt_configs(items: Any, fallback_prompts: Dict[str, str]) -> List[Dict[str, Any]]:
    if not isinstance(items, list):
        return _build_default_prompt_configs(fallback_prompts)

    normalized: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        role = _normalize_prompt_type(str(item.get("role") or item.get("prompt_type") or ""))
        normalized.append(
            {
                "id": str(item.get("id") or ""),
                "name": str(item.get("name") or ""),
                "role": role,
                "prompt_type": role,
                "content": str(item.get("content") or ""),
                "enabled": bool(item.get("enabled", True)),
                "created_at": _to_beijing_time_text(item.get("created_at")) or _utc_now(),
                "updated_at": _to_beijing_time_text(item.get("updated_at")) or _utc_now(),
                "creator": str(item.get("creator") or "admin"),
            }
        )
    if not normalized:
        return _build_default_prompt_configs(fallback_prompts)
    return normalized


def _normalize_generation_behavior_configs(items: Any) -> List[Dict[str, Any]]:
    defaults = _build_default_generation_behavior_configs()
    if not isinstance(items, list):
        return defaults

    normalized: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        timeout = int(item.get("review_timeout_seconds") or 1500)
        normalized.append(
            {
                "id": str(item.get("id") or ""),
                "name": str(item.get("name") or "默认生成配置"),
                "output_mode": str(item.get("output_mode") or "stream"),
                "enable_ai_review": bool(item.get("enable_ai_review", True)),
                "review_timeout_seconds": max(60, min(timeout, 3600)),
                "enabled": bool(item.get("enabled", True)),
                "created_at": _to_beijing_time_text(item.get("created_at")) or _utc_now(),
                "updated_at": _to_beijing_time_text(item.get("updated_at")) or _utc_now(),
            }
        )
    if not normalized:
        return defaults
    return normalized


def _sync_prompts_from_prompt_configs(config: Dict[str, Any]) -> None:
    prompts = dict(config.get("prompts", {}))
    for role in ("analysis", "generation", "review"):
        for item in config.get("prompt_configs", []):
            if not isinstance(item, dict):
                continue
            if not item.get("enabled", True):
                continue
            if _normalize_prompt_type(str(item.get("role") or item.get("prompt_type") or "")) != role:
                continue
            content = str(item.get("content") or "").strip()
            if content:
                prompts[role] = content
                break
    config["prompts"] = prompts


def _sync_role_configs_from_items(config: Dict[str, Any]) -> None:
    role_configs = dict(config.get("role_configs", {}))
    items = config.get("role_config_items") or []
    for role in ("analysis", "generation", "review"):
        enabled = next(
            (
                x for x in items
                if isinstance(x, dict)
                and _normalize_role_type(str(x.get("role_type") or "")) == role
                and bool(x.get("enabled", True))
                and str(x.get("mapped_model_name") or "").strip()
            ),
            None,
        )
        if enabled:
            role_configs[role] = str(enabled.get("mapped_model_name") or "").strip()
    config["role_configs"] = role_configs


def _merge_config_center(defaults: Dict[str, Any], loaded: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(defaults)
    merged["role_configs"] = {**defaults.get("role_configs", {}), **(loaded.get("role_configs") or {})}
    merged["prompts"] = {**defaults.get("prompts", {}), **(loaded.get("prompts") or {})}

    notifications = defaults.get("notifications", {})
    loaded_notifications = loaded.get("notifications") or {}
    merged["notifications"] = {
        "feishu": {**notifications.get("feishu", {}), **(loaded_notifications.get("feishu") or {})},
        "dingtalk": {**notifications.get("dingtalk", {}), **(loaded_notifications.get("dingtalk") or {})},
        "wecom": {**notifications.get("wecom", {}), **(loaded_notifications.get("wecom") or {})},
    }
    merged["role_config_items"] = _normalize_role_config_items(loaded.get("role_config_items"), merged["role_configs"])
    merged["ai_model_configs"] = _normalize_ai_model_configs(loaded.get("ai_model_configs"))
    merged["prompt_configs"] = _normalize_prompt_configs(loaded.get("prompt_configs"), merged["prompts"])
    merged["generation_behavior_configs"] = _normalize_generation_behavior_configs(loaded.get("generation_behavior_configs"))
    _sync_role_configs_from_items(merged)
    _sync_prompts_from_prompt_configs(merged)
    return merged


def _load_role_configs_from_table(db) -> Dict[str, str]:
    models = {
        "analysis": settings.LLM_MODEL,
        "generation": settings.LLM_MODEL,
        "review": settings.LLM_MODEL,
    }
    for item in _load_role_config_items_from_table(db):
        role = _normalize_role_type(str(item.get("role_type") or ""))
        if role in ("analysis", "generation", "review") and bool(item.get("enabled", True)):
            mapped_model_name = str(item.get("mapped_model_name") or "").strip()
            if mapped_model_name:
                models[role] = mapped_model_name
    return models


def _load_role_config_items_from_table(db) -> List[Dict[str, Any]]:
    loaded: List[Dict[str, Any]] = []
    for row in ConfigRepository.list_role_configs(db):
        loaded.append(
            {
                "id": row.config_id,
                "name": row.name,
                "role_type": row.role_type,
                "mapped_model_name": row.mapped_model_name,
                "enabled": row.enabled,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
                "creator": row.creator,
                "modifier": row.modifier,
            }
        )
    fallback = {
        "analysis": settings.LLM_MODEL,
        "generation": settings.LLM_MODEL,
        "review": settings.LLM_MODEL,
    }
    return _normalize_role_config_items(loaded, fallback)


def _load_ai_model_configs_from_table(db) -> List[Dict[str, Any]]:
    loaded: List[Dict[str, Any]] = []
    for row in ConfigRepository.list_ai_configs(db):
        if row.record_type != "model":
            continue
        loaded.append(
            {
                "id": row.config_id,
                "name": row.name,
                "model_type": row.model_type,
                "api_key": row.api_key,
                "api_base_url": row.api_base_url,
                "model_name": row.model_name,
                "max_tokens": row.max_tokens,
                "temperature": row.temperature,
                "top_p": row.top_p,
                "enabled": row.enabled,
                "created_at": row.created_at,
            }
        )
    return _normalize_ai_model_configs(loaded)


def _load_prompts_from_table(db) -> Dict[str, str]:
    defaults = _default_config_center().get("prompts", {})
    prompts = {
        "analysis": str(defaults.get("analysis") or ""),
        "generation": str(defaults.get("generation") or ""),
        "review": str(defaults.get("review") or ""),
    }
    for row in ConfigRepository.list_prompt_configs(db):
        if row.record_type != "default":
            continue
        role = _normalize_prompt_type(str(row.role or ""))
        if role in ("analysis", "generation", "review"):
            prompts[role] = str(row.content or "")
    return prompts


def _load_prompt_configs_from_table(db, prompts: Dict[str, str]) -> List[Dict[str, Any]]:
    loaded: List[Dict[str, Any]] = []
    for row in ConfigRepository.list_prompt_configs(db):
        if row.record_type == "default":
            continue
        loaded.append(
            {
                "id": row.config_id,
                "name": row.name,
                "role": row.role,
                "prompt_type": row.role,
                "content": row.content,
                "enabled": row.enabled,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
                "creator": row.creator,
            }
        )
    return _normalize_prompt_configs(loaded, prompts)


def _load_notifications_from_table(db) -> Dict[str, Dict[str, Any]]:
    defaults = _default_config_center().get("notifications", {})
    notifications = {
        "feishu": dict(defaults.get("feishu") or {}),
        "dingtalk": dict(defaults.get("dingtalk") or {}),
        "wecom": dict(defaults.get("wecom") or {}),
    }
    for row in ConfigRepository.list_notification_configs(db):
        channel = str(row.channel or "").strip()
        if channel not in notifications:
            continue
        notifications[channel] = {
            "name": row.name,
            "enabled": row.enabled,
            "webhook": row.webhook,
            "secret": row.secret,
        }
    return notifications


def _load_generation_behavior_configs_from_table(db) -> List[Dict[str, Any]]:
    loaded: List[Dict[str, Any]] = []
    for row in ConfigRepository.list_generation_behavior_configs(db):
        loaded.append(
            {
                "id": row.config_id,
                "name": row.name,
                "output_mode": row.output_mode,
                "enable_ai_review": row.enable_ai_review,
                "review_timeout_seconds": row.review_timeout_seconds,
                "enabled": row.enabled,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
        )
    return _normalize_generation_behavior_configs(loaded)


def _load_split_config_from_tables(db) -> Dict[str, Any]:
    loaded: Dict[str, Any] = {
        "role_configs": {},
        "role_config_items": [],
        "ai_model_configs": [],
        "prompts": {},
        "prompt_configs": [],
        "notifications": {},
        "generation_behavior_configs": [],
    }

    loaded["role_config_items"] = _load_role_config_items_from_table(db)
    for item in loaded["role_config_items"]:
        role = _normalize_role_type(str(item.get("role_type") or ""))
        if bool(item.get("enabled", True)):
            model_name = str(item.get("mapped_model_name") or "").strip()
            if model_name:
                loaded["role_configs"][role] = model_name

    for row in ConfigRepository.list_ai_configs(db):
        if row.record_type != "model":
            continue
        loaded["ai_model_configs"].append(
            {
                "id": row.config_id,
                "name": row.name,
                "model_type": row.model_type,
                "api_key": row.api_key,
                "api_base_url": row.api_base_url,
                "model_name": row.model_name,
                "max_tokens": row.max_tokens,
                "temperature": row.temperature,
                "top_p": row.top_p,
                "enabled": row.enabled,
                "created_at": row.created_at,
            }
        )

    for row in ConfigRepository.list_prompt_configs(db):
        if row.record_type == "default":
            loaded["prompts"][row.role] = row.content
            continue
        loaded["prompt_configs"].append(
            {
                "id": row.config_id,
                "name": row.name,
                "role": row.role,
                "prompt_type": row.role,
                "content": row.content,
                "enabled": row.enabled,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
                "creator": row.creator,
            }
        )

    for row in ConfigRepository.list_notification_configs(db):
        loaded["notifications"][row.channel] = {
            "name": row.name,
            "enabled": row.enabled,
            "webhook": row.webhook,
            "secret": row.secret,
        }

    for row in ConfigRepository.list_generation_behavior_configs(db):
        loaded["generation_behavior_configs"].append(
            {
                "id": row.config_id,
                "name": row.name,
                "output_mode": row.output_mode,
                "enable_ai_review": row.enable_ai_review,
                "review_timeout_seconds": row.review_timeout_seconds,
                "enabled": row.enabled,
                "created_at": row.created_at,
                "updated_at": row.updated_at,
            }
        )

    return loaded


def _save_split_config_to_tables(db, merged: Dict[str, Any], now: str) -> None:
    role_items = _normalize_role_config_items(merged.get("role_config_items"), merged.get("role_configs") or {})
    merged["role_config_items"] = role_items
    _sync_role_configs_from_items(merged)

    ConfigRepository.clear_role_configs(db)
    for item in role_items:
        ConfigRepository.create_role_config(
            db,
            config_id=str(item.get("id") or f"role-config-{_utc_now()}"),
            name=str(item.get("name") or ""),
            role_type=_normalize_role_type(str(item.get("role_type") or "")),
            mapped_model_name=str(item.get("mapped_model_name") or settings.LLM_MODEL),
            enabled=bool(item.get("enabled", True)),
            creator=str(item.get("creator") or "admin"),
            modifier=str(item.get("modifier") or "admin"),
            created_at=str(item.get("created_at") or now),
            updated_at=str(item.get("updated_at") or now),
        )

    ConfigRepository.clear_ai_configs(db)
    for item in merged.get("ai_model_configs") or []:
        ConfigRepository.create_ai_config(
            db,
            record_type="model",
            config_id=str(item.get("id") or f"ai-model-{_utc_now()}"),
            name=str(item.get("name") or ""),
            model_type=str(item.get("model_type") or "other"),
            api_key=str(item.get("api_key") or ""),
            api_base_url=str(item.get("api_base_url") or settings.LLM_BASE_URL),
            model_name=str(item.get("model_name") or settings.LLM_MODEL),
            max_tokens=int(item.get("max_tokens") or 4096),
            temperature=float(item.get("temperature") if item.get("temperature") is not None else 0.7),
            top_p=float(item.get("top_p") if item.get("top_p") is not None else 0.9),
            enabled=bool(item.get("enabled", True)),
            created_at=str(item.get("created_at") or now),
            updated_at=now,
        )

    ConfigRepository.clear_prompt_configs(db)
    for role in ("analysis", "generation", "review"):
        ConfigRepository.create_prompt_config(
            db,
            record_type="default",
            config_id=f"system-default-{role}-prompt",
            role=role,
            name=f"default-{role}",
            content=str((merged.get("prompts") or {}).get(role) or ""),
            enabled=True,
            creator="system",
            created_at=now,
            updated_at=now,
        )
    for item in merged.get("prompt_configs") or []:
        prompt_role = _normalize_prompt_type(str(item.get("role") or item.get("prompt_type") or ""))
        ConfigRepository.create_prompt_config(
            db,
            record_type="prompt",
            config_id=str(item.get("id") or f"prompt-{_utc_now()}"),
            role=prompt_role,
            name=str(item.get("name") or ""),
            content=str(item.get("content") or ""),
            enabled=bool(item.get("enabled", True)),
            creator=str(item.get("creator") or "admin"),
            created_at=str(item.get("created_at") or now),
            updated_at=str(item.get("updated_at") or now),
        )

    ConfigRepository.clear_notification_configs(db)
    notifications = merged.get("notifications") or {}
    for channel in ("feishu", "dingtalk", "wecom"):
        item = notifications.get(channel) or {}
        ConfigRepository.create_notification_config(
            db,
            channel=channel,
            name=str(item.get("name") or ""),
            enabled=bool(item.get("enabled", False)),
            webhook=str(item.get("webhook") or ""),
            secret=str(item.get("secret") or ""),
            created_at=now,
            updated_at=now,
        )

    ConfigRepository.clear_generation_behavior_configs(db)
    for item in merged.get("generation_behavior_configs") or []:
        timeout = int(item.get("review_timeout_seconds") or 1500)
        ConfigRepository.create_generation_behavior_config(
            db,
            config_id=str(item.get("id") or f"behavior-{_utc_now()}"),
            name=str(item.get("name") or "默认生成配置"),
            output_mode=str(item.get("output_mode") or "stream"),
            enable_ai_review=bool(item.get("enable_ai_review", True)),
            review_timeout_seconds=max(60, min(timeout, 3600)),
            enabled=bool(item.get("enabled", True)),
            created_at=str(item.get("created_at") or now),
            updated_at=str(item.get("updated_at") or now),
        )


def _drop_legacy_app_config_table() -> None:
    inspector = inspect(engine)
    tables = set(inspector.get_table_names())
    if "app_configs" not in tables:
        return
    with engine.begin() as conn:
        logger.info("Dropping legacy table: app_configs")
        conn.execute(text("DROP TABLE IF EXISTS app_configs"))


def seed_default_config_center() -> None:
    now = _utc_now()
    defaults = _default_config_center()
    with transactional_session() as db:
        loaded = _load_split_config_from_tables(db)
        merged = _merge_config_center(defaults, loaded)
        _save_split_config_to_tables(db, merged, now)
    _drop_legacy_app_config_table()


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    with SessionLocal() as db:
        user = UserRepository.get_by_username(db, username)
        if not user:
            return None
        return {
            "id": user.id,
            "username": user.username,
            "password": user.password,
            "is_active": user.is_active,
            "created_at": _to_beijing_time_text(user.created_at),
            "updated_at": _to_beijing_time_text(user.updated_at),
        }


def ensure_user(username: str, password: str = "123456") -> Dict[str, Any]:
    existing = get_user_by_username(username)
    if existing:
        return existing

    now = _utc_now()
    with transactional_session() as db:
        user = UserRepository.create(
            db,
            username=username,
            password=hash_password(password),
            created_at=now,
            updated_at=now,
        )
        return {
            "id": user.id,
            "username": user.username,
            "password": user.password,
            "is_active": user.is_active,
            "created_at": _to_beijing_time_text(user.created_at),
            "updated_at": _to_beijing_time_text(user.updated_at),
        }


def update_user_password_hash(username: str, password_hash: str) -> bool:
    now = _utc_now()
    with transactional_session() as db:
        user = UserRepository.get_by_username(db, username)
        if not user:
            return False
        UserRepository.update_password(db, user, password=password_hash, updated_at=now)
        return True


def create_task_record(
    task_id: str,
    task_name: Optional[str],
    source_type: Optional[str],
    doc_url: Optional[str],
    file_name: Optional[str] = None,
    file_path: Optional[str] = None,
    status: str = "uploaded",
    status_text: Optional[str] = "文件已上传",
    user_id: Optional[int] = None,
) -> None:
    now = _utc_now()
    with transactional_session() as db:
        TaskRepository.create_task(
            db,
            task_id=task_id,
            task_name=task_name,
            source_type=source_type,
            doc_url=doc_url,
            file_name=file_name,
            file_path=file_path,
            status=status,
            status_text=status_text,
            user_id=user_id,
            created_at=now,
            updated_at=now,
        )
        TaskRepository.create_task_detail(
            db,
            task_id=task_id,
            phase_key="upload",
            phase_label="文件上传",
            status="completed",
            created_at=now,
            updated_at=now,
        )
        TaskRepository.create_task_detail(
            db,
            task_id=task_id,
            phase_key="analysis",
            phase_label="需求分析",
            status="pending",
            created_at=now,
            updated_at=now,
        )
        TaskRepository.create_task_detail(
            db,
            task_id=task_id,
            phase_key="generation",
            phase_label="用例编写",
            status="pending",
            created_at=now,
            updated_at=now,
        )
        TaskRepository.create_task_detail(
            db,
            task_id=task_id,
            phase_key="review",
            phase_label="用例评审",
            status="pending",
            created_at=now,
            updated_at=now,
        )
        TaskRepository.create_task_detail(
            db,
            task_id=task_id,
            phase_key="notify",
            phase_label="钉钉通知",
            status="pending",
            created_at=now,
            updated_at=now,
        )


def reset_task_for_retry(task_id: str, status_text: Optional[str] = None) -> bool:
    now = _utc_now()
    with transactional_session() as db:
        found = TaskRepository.reset_task_for_retry(
            db,
            task_id=task_id,
            status="running",
            status_text=status_text,
            updated_at=now,
        )
        if not found:
            return False
        TaskRepository.reset_task_details_for_retry(db, task_id=task_id, updated_at=now)
        return True


def update_task_status(
    task_id: str,
    status: str,
    error: Optional[str] = None,
    status_text: Optional[str] = None,
) -> None:
    now = _utc_now()
    with transactional_session() as db:
        task = TaskRepository.get_task(db, task_id)
        if not task:
            return
        task.status = status
        task.error = error
        if status_text is not None:
            task.status_text = status_text
        task.updated_at = now


def update_task_mindmap(task_id: str, mindmap: str) -> None:
    now = _utc_now()
    with transactional_session() as db:
        task = TaskRepository.get_task(db, task_id)
        if not task:
            return
        task.mindmap = mindmap
        task.updated_at = now


def update_task_phase(
    task_id: str,
    phase_key: str,
    status: str,
    data: Optional[Any] = None,
    error: Optional[str] = None,
) -> None:
    now = _utc_now()
    with transactional_session() as db:
        detail = TaskRepository.get_task_detail_by_phase(db, task_id, phase_key)
        if not detail:
            return
        detail.status = status
        if data is not None:
            detail.data_json = json.dumps(data, ensure_ascii=False)
        detail.error = error
        detail.updated_at = now


def get_task_record(task_id: str) -> Optional[Dict[str, Any]]:
    with SessionLocal() as db:
        task = TaskRepository.get_task(db, task_id)
        if not task:
            return None
        details = TaskRepository.get_task_details(db, task_id)

    phases: Dict[str, Dict[str, Any]] = {}
    for row in details:
        parsed_data = None
        if row.data_json:
            try:
                parsed_data = json.loads(row.data_json)
            except json.JSONDecodeError:
                parsed_data = None
        phases[row.phase_key] = {
            "status": row.status,
            "label": row.phase_label,
            "data": parsed_data,
        }

    return {
        "id": task.id,
        "task_name": task.task_name,
        "user_id": task.user_id,
        "source_type": task.source_type,
        "doc_url": task.doc_url,
        "file_name": task.file_name,
        "file_path": task.file_path,
        "status": task.status,
        "status_text": task.status_text,
        "decision_status": task.decision_status,
        "decision_by": task.decision_by,
        "decision_note": task.decision_note,
        "decision_at": _to_beijing_time_text(task.decision_at),
        "phases": phases,
        "mindmap": task.mindmap,
        "error": task.error,
    }


def list_tasks(
    page: int = 1,
    page_size: int = 10,
    task_name: Optional[str] = None,
    task_id: Optional[str] = None,
    source_type: Optional[str] = None,
    status: Optional[str] = None,
    submitter: Optional[str] = None,
) -> Dict[str, Any]:
    with SessionLocal() as db:
        total, rows = TaskRepository.list_tasks(
            db,
            page=page,
            page_size=page_size,
            task_name=task_name,
            task_id=task_id,
            source_type=source_type,
            status=status,
            submitter=submitter,
        )

    items = []
    for task, username in rows:
        items.append(
            {
                "id": task.id,
                "task_name": task.task_name or "",
                "user_id": task.user_id,
                "source_type": task.source_type,
                "doc_url": task.doc_url,
                "file_name": task.file_name,
                "status": task.status,
                "status_text": task.status_text,
                "decision_status": task.decision_status,
                "error": task.error,
                "created_at": _to_beijing_time_text(task.created_at),
                "updated_at": _to_beijing_time_text(task.updated_at),
                "submitter": username or "admin",
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def delete_task_record(task_id: str) -> bool:
    return delete_task_records([task_id]) > 0


def delete_task_records(task_ids: List[str]) -> int:
    unique_task_ids = [x for x in dict.fromkeys(task_ids or []) if x]
    if not unique_task_ids:
        return 0

    with transactional_session() as db:
        TaskRepository.delete_task_details_by_task_ids(db, unique_task_ids)
        deleted_count = TaskRepository.delete_tasks_by_ids(db, unique_task_ids)
    return deleted_count


def update_task_decision(
    task_id: str,
    *,
    decision_status: str,
    decision_by: Optional[str] = None,
    decision_note: Optional[str] = None,
) -> bool:
    now = _utc_now()
    with transactional_session() as db:
        task = TaskRepository.get_task(db, task_id)
        if not task:
            return False
        task.decision_status = decision_status
        task.decision_by = decision_by
        task.decision_note = decision_note
        task.decision_at = now
        task.updated_at = now
        return True


def get_config_center() -> Dict[str, Any]:
    defaults = _default_config_center()
    with SessionLocal() as db:
        loaded = _load_split_config_from_tables(db)
        merged = _merge_config_center(defaults, loaded)
    return merged


def get_default_prompt_configs() -> List[Dict[str, Any]]:
    defaults = _default_config_center()
    prompts = defaults.get("prompts", {})
    return _build_default_prompt_configs(prompts)


def get_ai_model_configs_section() -> Dict[str, Any]:
    with SessionLocal() as db:
        ai_model_configs = _load_ai_model_configs_from_table(db)
    return {"ai_model_configs": ai_model_configs}


def update_ai_model_configs_section(ai_model_configs: Any) -> Dict[str, Any]:
    now = _utc_now()
    normalized = _normalize_ai_model_configs(ai_model_configs)
    with transactional_session() as db:
        ConfigRepository.clear_ai_configs(db)
        for item in normalized:
            ConfigRepository.create_ai_config(
                db,
                record_type="model",
                config_id=str(item.get("id") or f"ai-model-{_utc_now()}"),
                name=str(item.get("name") or ""),
                model_type=str(item.get("model_type") or "other"),
                api_key=str(item.get("api_key") or ""),
                api_base_url=str(item.get("api_base_url") or settings.LLM_BASE_URL),
                model_name=str(item.get("model_name") or settings.LLM_MODEL),
                max_tokens=int(item.get("max_tokens") or 4096),
                temperature=float(item.get("temperature") if item.get("temperature") is not None else 0.7),
                top_p=float(item.get("top_p") if item.get("top_p") is not None else 0.9),
                enabled=bool(item.get("enabled", True)),
                created_at=str(item.get("created_at") or now),
                updated_at=now,
            )
    return {"ai_model_configs": normalized}


def get_role_configs_section() -> Dict[str, Any]:
    with SessionLocal() as db:
        role_config_items = _load_role_config_items_from_table(db)
        role_configs = _load_role_configs_from_table(db)
        ai_model_configs = _load_ai_model_configs_from_table(db)
    return {
        "role_configs": role_configs,
        "role_config_items": role_config_items,
        "ai_model_configs": ai_model_configs,
    }


def update_role_configs_section(payload: Dict[str, Any]) -> Dict[str, Any]:
    now = _utc_now()
    with transactional_session() as db:
        current_map = _load_role_configs_from_table(db)
        current_items = _load_role_config_items_from_table(db)

        role_configs_payload = payload.get("role_configs") or payload.get("ai_models")
        role_items_payload = payload.get("role_config_items")

        if role_items_payload is not None:
            merged_items = _normalize_role_config_items(role_items_payload, current_map)
        else:
            merged_map = {
                "analysis": str((role_configs_payload or {}).get("analysis") or current_map.get("analysis") or settings.LLM_MODEL),
                "generation": str((role_configs_payload or {}).get("generation") or current_map.get("generation") or settings.LLM_MODEL),
                "review": str((role_configs_payload or {}).get("review") or current_map.get("review") or settings.LLM_MODEL),
            }
            merged_items = _normalize_role_config_items(current_items, merged_map)
            for item in merged_items:
                role = _normalize_role_type(str(item.get("role_type") or ""))
                item["mapped_model_name"] = merged_map.get(role) or item.get("mapped_model_name") or settings.LLM_MODEL
                item["updated_at"] = now
                item["modifier"] = "admin"

        ConfigRepository.clear_role_configs(db)
        for item in merged_items:
            ConfigRepository.create_role_config(
                db,
                config_id=str(item.get("id") or f"role-config-{_utc_now()}"),
                name=str(item.get("name") or ""),
                role_type=_normalize_role_type(str(item.get("role_type") or "")),
                mapped_model_name=str(item.get("mapped_model_name") or settings.LLM_MODEL),
                enabled=bool(item.get("enabled", True)),
                creator=str(item.get("creator") or "admin"),
                modifier=str(item.get("modifier") or "admin"),
                created_at=str(item.get("created_at") or now),
                updated_at=str(item.get("updated_at") or now),
            )
        merged_map = _load_role_configs_from_table(db)
        merged_items = _load_role_config_items_from_table(db)
        ai_model_configs = _load_ai_model_configs_from_table(db)
    return {
        "role_configs": merged_map,
        "role_config_items": merged_items,
        "ai_model_configs": ai_model_configs,
    }


def get_prompt_configs_section() -> Dict[str, Any]:
    with SessionLocal() as db:
        prompts = _load_prompts_from_table(db)
        prompt_configs = _load_prompt_configs_from_table(db, prompts)
    merged = {"prompts": prompts, "prompt_configs": prompt_configs}
    _sync_prompts_from_prompt_configs(merged)
    return merged


def update_prompt_configs_section(payload: Dict[str, Any]) -> Dict[str, Any]:
    now = _utc_now()
    with transactional_session() as db:
        current_prompts = _load_prompts_from_table(db)
        current_prompt_configs = _load_prompt_configs_from_table(db, current_prompts)

        prompts_payload = payload.get("prompts")
        prompt_configs_payload = payload.get("prompt_configs")

        prompts = dict(current_prompts)
        if isinstance(prompts_payload, dict):
            prompts.update({k: str(v or "") for k, v in prompts_payload.items() if k in ("analysis", "generation", "review")})

        if prompt_configs_payload is not None:
            prompt_configs = _normalize_prompt_configs(prompt_configs_payload, prompts)
        else:
            prompt_configs = current_prompt_configs

        merged = {"prompts": prompts, "prompt_configs": prompt_configs}
        _sync_prompts_from_prompt_configs(merged)

        ConfigRepository.clear_prompt_configs(db)
        for role in ("analysis", "generation", "review"):
            ConfigRepository.create_prompt_config(
                db,
                record_type="default",
                config_id=f"system-default-{role}-prompt",
                role=role,
                name=f"default-{role}",
                content=str((merged.get("prompts") or {}).get(role) or ""),
                enabled=True,
                creator="system",
                created_at=now,
                updated_at=now,
            )
        for item in merged.get("prompt_configs") or []:
            prompt_role = _normalize_prompt_type(str(item.get("role") or item.get("prompt_type") or ""))
            ConfigRepository.create_prompt_config(
                db,
                record_type="prompt",
                config_id=str(item.get("id") or f"prompt-{_utc_now()}"),
                role=prompt_role,
                name=str(item.get("name") or ""),
                content=str(item.get("content") or ""),
                enabled=bool(item.get("enabled", True)),
                creator=str(item.get("creator") or "admin"),
                created_at=str(item.get("created_at") or now),
                updated_at=str(item.get("updated_at") or now),
            )

    return {
        "prompts": merged["prompts"],
        "prompt_configs": merged["prompt_configs"],
    }


def get_generation_behavior_configs_section() -> Dict[str, Any]:
    with SessionLocal() as db:
        generation_behavior_configs = _load_generation_behavior_configs_from_table(db)
    return {"generation_behavior_configs": generation_behavior_configs}


def update_generation_behavior_configs_section(items: Any) -> Dict[str, Any]:
    now = _utc_now()
    normalized = _normalize_generation_behavior_configs(items)
    with transactional_session() as db:
        ConfigRepository.clear_generation_behavior_configs(db)
        for item in normalized:
            timeout = int(item.get("review_timeout_seconds") or 1500)
            ConfigRepository.create_generation_behavior_config(
                db,
                config_id=str(item.get("id") or f"behavior-{_utc_now()}"),
                name=str(item.get("name") or "默认生成配置"),
                output_mode=str(item.get("output_mode") or "stream"),
                enable_ai_review=bool(item.get("enable_ai_review", True)),
                review_timeout_seconds=max(60, min(timeout, 3600)),
                enabled=bool(item.get("enabled", True)),
                created_at=str(item.get("created_at") or now),
                updated_at=str(item.get("updated_at") or now),
            )
    return {"generation_behavior_configs": normalized}


def get_notifications_section() -> Dict[str, Any]:
    with SessionLocal() as db:
        notifications = _load_notifications_from_table(db)
    return {"notifications": notifications}


def update_notifications_section(notifications_payload: Dict[str, Any]) -> Dict[str, Any]:
    now = _utc_now()
    with transactional_session() as db:
        current = _load_notifications_from_table(db)
        merged = {
            "feishu": {**current.get("feishu", {}), **(notifications_payload.get("feishu") or {})},
            "dingtalk": {**current.get("dingtalk", {}), **(notifications_payload.get("dingtalk") or {})},
            "wecom": {**current.get("wecom", {}), **(notifications_payload.get("wecom") or {})},
        }
        ConfigRepository.clear_notification_configs(db)
        for channel in ("feishu", "dingtalk", "wecom"):
            item = merged.get(channel) or {}
            ConfigRepository.create_notification_config(
                db,
                channel=channel,
                name=str(item.get("name") or ""),
                enabled=bool(item.get("enabled", False)),
                webhook=str(item.get("webhook") or ""),
                secret=str(item.get("secret") or ""),
                created_at=now,
                updated_at=now,
            )
    return {"notifications": merged}


def update_config_center(payload: Dict[str, Any]) -> Dict[str, Any]:
    now = _utc_now()
    current = get_config_center()
    merged = dict(current)

    if "ai_models" in payload and "role_configs" not in payload:
        payload["role_configs"] = payload.get("ai_models")

    for section in ("role_configs", "prompts", "notifications"):
        if section in payload and isinstance(payload[section], dict):
            if section == "notifications":
                merged[section] = {
                    "feishu": {**current["notifications"]["feishu"], **(payload[section].get("feishu") or {})},
                    "dingtalk": {**current["notifications"]["dingtalk"], **(payload[section].get("dingtalk") or {})},
                    "wecom": {**current["notifications"]["wecom"], **(payload[section].get("wecom") or {})},
                }
            else:
                merged[section] = {**current.get(section, {}), **payload[section]}

    if "ai_model_configs" in payload:
        merged["ai_model_configs"] = _normalize_ai_model_configs(payload.get("ai_model_configs"))
    if "role_config_items" in payload:
        merged["role_config_items"] = _normalize_role_config_items(
            payload.get("role_config_items"),
            merged.get("role_configs") or current.get("role_configs") or {},
        )
    if "prompt_configs" in payload:
        merged["prompt_configs"] = _normalize_prompt_configs(payload.get("prompt_configs"), merged.get("prompts", {}))
    if "generation_behavior_configs" in payload:
        merged["generation_behavior_configs"] = _normalize_generation_behavior_configs(payload.get("generation_behavior_configs"))

    _sync_role_configs_from_items(merged)
    _sync_prompts_from_prompt_configs(merged)

    with transactional_session() as db:
        _save_split_config_to_tables(db, merged, now)

    return merged
