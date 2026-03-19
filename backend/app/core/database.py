import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from loguru import logger
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.models import Base
from app.repositories import ConfigRepository, TaskRepository, UserRepository


_DB_PATH = Path(settings.SQLITE_DB_PATH)


def _utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _build_engine():
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    return create_engine(
        f"sqlite:///{_DB_PATH}",
        future=True,
        connect_args={"check_same_thread": False},
    )


engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)


def init_db() -> None:
    inspector = inspect(engine)
    existing = set(inspector.get_table_names())
    required = {"users", "tasks", "task_details", "app_configs"}
    missing = required - existing
    if missing:
        logger.info(f"Missing tables detected: {sorted(missing)}. Creating...")

    Base.metadata.create_all(bind=engine, checkfirst=True)
    _migrate_legacy_columns()

    seed_default_user()
    seed_default_config_center()
    logger.info(f"SQLAlchemy initialized: {_DB_PATH}")


def _migrate_legacy_columns() -> None:
    inspector = inspect(engine)
    task_columns = {col["name"] for col in inspector.get_columns("tasks")}
    if "task_name" not in task_columns:
        logger.info("Column tasks.task_name missing, applying migration.")
        with engine.begin() as conn:
            conn.execute(text("ALTER TABLE tasks ADD COLUMN task_name TEXT"))


def seed_default_user() -> None:
    now = _utc_now()
    with SessionLocal() as db:
        existing = UserRepository.get_by_username(db, "admin")
        if existing:
            return
        UserRepository.create(db, username="admin", password="123456", created_at=now, updated_at=now)
        db.commit()


def _default_config_center() -> Dict[str, Any]:
    defaults = {
        "ai_models": {
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
                "business_types": ["ui_auto", "api"],
            },
            "dingtalk": {
                "name": "",
                "enabled": False,
                "webhook": "",
                "secret": "",
                "business_types": ["ui_auto", "api"],
            },
            "wecom": {
                "name": "",
                "enabled": False,
                "webhook": "",
                "secret": "",
                "business_types": ["ui_auto", "api"],
            },
        },
    }
    defaults["prompt_configs"] = _build_default_prompt_configs(defaults["prompts"])
    defaults["generation_behavior_configs"] = _build_default_generation_behavior_configs()
    return defaults


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
                "role": str(item.get("role") or "generation"),
                "api_key": str(item.get("api_key") or ""),
                "api_base_url": str(item.get("api_base_url") or settings.LLM_BASE_URL),
                "model_name": str(item.get("model_name") or settings.LLM_MODEL),
                "max_tokens": int(item.get("max_tokens") or 4096),
                "temperature": float(item.get("temperature") if item.get("temperature") is not None else 0.7),
                "top_p": float(item.get("top_p") if item.get("top_p") is not None else 0.9),
                "enabled": bool(item.get("enabled", True)),
                "created_at": str(item.get("created_at") or _utc_now()),
            }
        )
    return normalized


def _normalize_prompt_configs(items: Any, fallback_prompts: Dict[str, str]) -> List[Dict[str, Any]]:
    if not isinstance(items, list):
        return _build_default_prompt_configs(fallback_prompts)

    normalized: List[Dict[str, Any]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        normalized.append(
            {
                "id": str(item.get("id") or ""),
                "name": str(item.get("name") or ""),
                "prompt_type": _normalize_prompt_type(str(item.get("prompt_type") or "")),
                "content": str(item.get("content") or ""),
                "enabled": bool(item.get("enabled", True)),
                "created_at": str(item.get("created_at") or _utc_now()),
                "updated_at": str(item.get("updated_at") or _utc_now()),
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
                "created_at": str(item.get("created_at") or _utc_now()),
                "updated_at": str(item.get("updated_at") or _utc_now()),
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
            if _normalize_prompt_type(str(item.get("prompt_type") or "")) != role:
                continue
            content = str(item.get("content") or "").strip()
            if content:
                prompts[role] = content
                break
    config["prompts"] = prompts


def _merge_config_center(defaults: Dict[str, Any], loaded: Dict[str, Any]) -> Dict[str, Any]:
    merged = dict(defaults)
    merged["ai_models"] = {**defaults.get("ai_models", {}), **(loaded.get("ai_models") or {})}
    merged["prompts"] = {**defaults.get("prompts", {}), **(loaded.get("prompts") or {})}

    notifications = defaults.get("notifications", {})
    loaded_notifications = loaded.get("notifications") or {}
    merged["notifications"] = {
        "feishu": {**notifications.get("feishu", {}), **(loaded_notifications.get("feishu") or {})},
        "dingtalk": {**notifications.get("dingtalk", {}), **(loaded_notifications.get("dingtalk") or {})},
        "wecom": {**notifications.get("wecom", {}), **(loaded_notifications.get("wecom") or {})},
    }
    merged["ai_model_configs"] = _normalize_ai_model_configs(loaded.get("ai_model_configs"))
    merged["prompt_configs"] = _normalize_prompt_configs(loaded.get("prompt_configs"), merged["prompts"])
    merged["generation_behavior_configs"] = _normalize_generation_behavior_configs(loaded.get("generation_behavior_configs"))
    _sync_prompts_from_prompt_configs(merged)
    return merged


def seed_default_config_center() -> None:
    now = _utc_now()
    default_config = _default_config_center()
    with SessionLocal() as db:
        existing = ConfigRepository.get_by_key(db, "config_center")
        if existing:
            return
        ConfigRepository.create(
            db,
            config_key="config_center",
            config_json=json.dumps(default_config, ensure_ascii=False),
            created_at=now,
            updated_at=now,
        )
        db.commit()


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
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }


def ensure_user(username: str, password: str = "123456") -> Dict[str, Any]:
    existing = get_user_by_username(username)
    if existing:
        return existing

    now = _utc_now()
    with SessionLocal() as db:
        user = UserRepository.create(db, username=username, password=password, created_at=now, updated_at=now)
        db.commit()
        return {
            "id": user.id,
            "username": user.username,
            "password": user.password,
            "is_active": user.is_active,
            "created_at": user.created_at,
            "updated_at": user.updated_at,
        }


def create_task_record(
    task_id: str,
    task_name: Optional[str],
    source_type: Optional[str],
    doc_url: Optional[str],
    status: str = "running",
    status_text: Optional[str] = "本地文件分析中",
    user_id: Optional[int] = None,
) -> None:
    now = _utc_now()
    with SessionLocal() as db:
        TaskRepository.create_task(
            db,
            task_id=task_id,
            task_name=task_name,
            source_type=source_type,
            doc_url=doc_url,
            status=status,
            status_text=status_text,
            user_id=user_id,
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
        db.commit()


def update_task_status(
    task_id: str,
    status: str,
    error: Optional[str] = None,
    status_text: Optional[str] = None,
) -> None:
    now = _utc_now()
    with SessionLocal() as db:
        task = TaskRepository.get_task(db, task_id)
        if not task:
            return
        task.status = status
        task.error = error
        if status_text is not None:
            task.status_text = status_text
        task.updated_at = now
        db.commit()


def update_task_mindmap(task_id: str, mindmap: str) -> None:
    now = _utc_now()
    with SessionLocal() as db:
        task = TaskRepository.get_task(db, task_id)
        if not task:
            return
        task.mindmap = mindmap
        task.updated_at = now
        db.commit()


def update_task_phase(
    task_id: str,
    phase_key: str,
    status: str,
    data: Optional[Any] = None,
    error: Optional[str] = None,
) -> None:
    now = _utc_now()
    with SessionLocal() as db:
        detail = TaskRepository.get_task_detail_by_phase(db, task_id, phase_key)
        if not detail:
            return
        detail.status = status
        if data is not None:
            detail.data_json = json.dumps(data, ensure_ascii=False)
        detail.error = error
        detail.updated_at = now
        db.commit()


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
        "status": task.status,
        "status_text": task.status_text,
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
                "status": task.status,
                "status_text": task.status_text,
                "error": task.error,
                "created_at": task.created_at,
                "updated_at": task.updated_at,
                "submitter": username or "admin",
            }
        )

    return {
        "items": items,
        "total": total,
        "page": page,
        "page_size": page_size,
    }


def get_config_center() -> Dict[str, Any]:
    defaults = _default_config_center()
    with SessionLocal() as db:
        row = ConfigRepository.get_by_key(db, "config_center")
        if not row:
            return defaults
        try:
            loaded = json.loads(row.config_json)
        except json.JSONDecodeError:
            return defaults

    return _merge_config_center(defaults, loaded)


def get_default_prompt_configs() -> List[Dict[str, Any]]:
    defaults = _default_config_center()
    prompts = defaults.get("prompts", {})
    return _build_default_prompt_configs(prompts)


def update_config_center(payload: Dict[str, Any]) -> Dict[str, Any]:
    now = _utc_now()
    current = get_config_center()
    merged = dict(current)

    for section in ("ai_models", "prompts", "notifications"):
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
    if "prompt_configs" in payload:
        merged["prompt_configs"] = _normalize_prompt_configs(payload.get("prompt_configs"), merged.get("prompts", {}))
    if "generation_behavior_configs" in payload:
        merged["generation_behavior_configs"] = _normalize_generation_behavior_configs(payload.get("generation_behavior_configs"))

    _sync_prompts_from_prompt_configs(merged)

    with SessionLocal() as db:
        row = ConfigRepository.get_by_key(db, "config_center")
        if not row:
            ConfigRepository.create(
                db,
                config_key="config_center",
                config_json=json.dumps(merged, ensure_ascii=False),
                created_at=now,
                updated_at=now,
            )
        else:
            row.config_json = json.dumps(merged, ensure_ascii=False)
            row.updated_at = now
        db.commit()

    return merged
