from typing import Any, Dict, List

from app.core.config import settings
from app.core.database import AsyncSessionLocal, transactional_session
from app.util.time_utils import to_beijing_time_text, utc_now_text
from app.repositories import (
    AIConfigRepository,
    GenerationBehaviorConfigRepository,
    NotificationConfigRepository,
    PromptConfigRepository,
    RoleConfigRepository,
)


def _normalize_role_type(value: str) -> str:
    v = str(value or "").strip().lower()
    if v in {"analysis", "需求分析", "需求分析专家"}:
        return "analysis"
    if v in {"review", "用例评审", "测试用例评审"}:
        return "review"
    return "generation"


def _default_prompt_items(now: str) -> List[Dict[str, Any]]:
    return [
        {
            "id": "default-analysis-prompt",
            "name": "默认需求分析提示词",
            "role": "analysis",
            "content": "你是一个资深的软件需求分析师。请阅读用户上传的项目文档内容，提取关键功能点、业务流程、边界与限制条件，并使用清晰 Markdown 输出。",
            "enabled": True,
            "creator": "admin",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "default-generation-prompt",
            "name": "默认用例编写提示词",
            "role": "generation",
            "content": "你是一个资深的软件测试工程师。请基于输入策略生成结构化测试用例，覆盖正常、边界、异常、兼容与回归场景，并保证输出可解析。",
            "enabled": True,
            "creator": "admin",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "default-review-prompt",
            "name": "默认用例评审提示词",
            "role": "review",
            "content": "你是一个资深的软件质量保证专家。请对生成的测试用例做质量评审，指出问题、优化建议、缺失场景，并给出质量评分与总结。",
            "enabled": True,
            "creator": "admin",
            "created_at": now,
            "updated_at": now,
        },
    ]


async def _load_ai_configs(db) -> List[Dict[str, Any]]:
    rows = await AIConfigRepository.list(db)
    result: List[Dict[str, Any]] = []
    for row in rows:
        if str(row.record_type or "model") != "model":
            continue
        result.append(
            {
                "id": str(row.config_id),
                "name": str(row.name or ""),
                "model_type": str(row.model_type or "other"),
                "api_key": str(row.api_key or ""),
                "api_base_url": str(row.api_base_url or settings.LLM_BASE_URL),
                "model_name": str(row.model_name or settings.LLM_MODEL),
                "max_tokens": int(row.max_tokens or 4096),
                "temperature": float(row.temperature if row.temperature is not None else 0.7),
                "top_p": float(row.top_p if row.top_p is not None else 0.9),
                "enabled": bool(row.enabled),
                "created_at": to_beijing_time_text(row.created_at),
                "updated_at": to_beijing_time_text(row.updated_at),
                "creator": str(row.creator or "admin"),
                "modifier": str(row.modifier or "admin"),
            }
        )
    return result


async def _load_role_items(db) -> List[Dict[str, Any]]:
    rows = await RoleConfigRepository.list(db)
    return [
        {
            "id": str(r.config_id),
            "name": str(r.name or ""),
            "role_type": _normalize_role_type(r.role_type),
            "mapped_model_name": str(r.mapped_model_name or settings.LLM_MODEL),
            "enabled": bool(r.enabled),
            "created_at": to_beijing_time_text(r.created_at),
            "updated_at": to_beijing_time_text(r.updated_at),
            "creator": str(r.creator or "admin"),
            "modifier": str(r.modifier or "admin"),
        }
        for r in rows
    ]


async def _load_role_map(db) -> Dict[str, str]:
    role_map = {
        "analysis": settings.LLM_MODEL,
        "generation": settings.LLM_MODEL,
        "review": settings.LLM_MODEL,
    }
    for item in await _load_role_items(db):
        if item["enabled"]:
            role_map[_normalize_role_type(item["role_type"])] = item["mapped_model_name"]
    return role_map


async def _load_prompt_items(db) -> List[Dict[str, Any]]:
    rows = await PromptConfigRepository.list(db)
    return [
        {
            "id": str(r.config_id),
            "name": str(r.name or ""),
            "role": _normalize_role_type(r.role),
            "prompt_type": _normalize_role_type(r.role),
            "content": str(r.content or ""),
            "enabled": bool(r.enabled),
            "creator": str(r.creator or "admin"),
            "created_at": to_beijing_time_text(r.created_at),
            "updated_at": to_beijing_time_text(r.updated_at),
        }
        for r in rows
    ]


async def _load_prompts(db) -> Dict[str, str]:
    prompts = {"analysis": "", "generation": "", "review": ""}
    for item in await _load_prompt_items(db):
        role = _normalize_role_type(item["role"])
        if item["enabled"] and item["content"].strip():
            prompts[role] = item["content"]
    return prompts


async def _load_notifications(db) -> Dict[str, Dict[str, Any]]:
    result = {
        "feishu": {"name": "", "enabled": False, "webhook": "", "secret": ""},
        "dingtalk": {"name": "", "enabled": False, "webhook": "", "secret": ""},
        "wecom": {"name": "", "enabled": False, "webhook": "", "secret": ""},
    }
    for r in await NotificationConfigRepository.list(db):
        ch = str(r.channel or "").lower()
        if ch in result:
            result[ch] = {
                "name": str(r.name or ""),
                "enabled": bool(r.enabled),
                "webhook": str(r.webhook or ""),
                "secret": str(r.secret or ""),
            }
    return result


async def _load_behavior_items(db) -> List[Dict[str, Any]]:
    rows = await GenerationBehaviorConfigRepository.list(db)
    return [
        {
            "id": str(r.config_id),
            "name": str(r.name or "默认生成配置"),
            "output_mode": str(r.output_mode or "stream"),
            "enable_ai_review": bool(r.enable_ai_review),
            "review_timeout_seconds": int(r.review_timeout_seconds or 1500),
            "enabled": bool(r.enabled),
            "created_at": to_beijing_time_text(r.created_at),
            "updated_at": to_beijing_time_text(r.updated_at),
        }
        for r in rows
    ]


async def seed_default_config_center() -> None:
    now = utc_now_text()
    async with transactional_session() as db:
        if not await AIConfigRepository.list(db):
            await AIConfigRepository.create(
                db,
                record_type="model",
                config_id="default-model",
                name="默认模型",
                model_type="other",
                api_key=settings.LLM_API_KEY,
                api_base_url=settings.LLM_BASE_URL,
                model_name=settings.LLM_MODEL,
                max_tokens=settings.LLM_MAX_TOKENS,
                temperature=settings.LLM_TEMPERATURE,
                top_p=settings.LLM_TOP_P,
                enabled=True,
                creator="admin",
                modifier="admin",
                created_at=now,
                updated_at=now,
            )

        if not await RoleConfigRepository.list(db):
            for role in ("analysis", "generation", "review"):
                await RoleConfigRepository.create(
                    db,
                    config_id=f"default-{role}-role-config",
                    name=f"默认{role}配置",
                    role_type=role,
                    mapped_model_name=settings.LLM_MODEL,
                    enabled=True,
                    creator="admin",
                    modifier="admin",
                    created_at=now,
                    updated_at=now,
                )

        if not await PromptConfigRepository.list(db):
            for item in _default_prompt_items(now):
                await PromptConfigRepository.create(
                    db,
                    record_type="prompt",
                    config_id=item["id"],
                    role=item["role"],
                    name=item["name"],
                    content=item["content"],
                    enabled=item["enabled"],
                    creator=item["creator"],
                    created_at=item["created_at"],
                    updated_at=item["updated_at"],
                )

        if not await GenerationBehaviorConfigRepository.list(db):
            await GenerationBehaviorConfigRepository.create(
                db,
                config_id="default-generation-behavior",
                name="默认生成配置",
                output_mode="stream",
                enable_ai_review=True,
                review_timeout_seconds=1500,
                enabled=True,
                created_at=now,
                updated_at=now,
            )

        if not await NotificationConfigRepository.list(db):
            for ch in ("feishu", "dingtalk", "wecom"):
                await NotificationConfigRepository.create(
                    db,
                    channel=ch,
                    name="",
                    enabled=False,
                    webhook="",
                    secret="",
                    created_at=now,
                    updated_at=now,
                )


async def get_default_prompt_configs() -> List[Dict[str, Any]]:
    return _default_prompt_items(utc_now_text())


async def get_config_center() -> Dict[str, Any]:
    async with AsyncSessionLocal() as db:
        role_map = await _load_role_map(db)
        return {
            "role_configs": role_map,
            "ai_models": role_map,
            "role_config_items": await _load_role_items(db),
            "ai_model_configs": await _load_ai_configs(db),
            "prompts": await _load_prompts(db),
            "prompt_configs": await _load_prompt_items(db),
            "notifications": await _load_notifications(db),
            "generation_behavior_configs": await _load_behavior_items(db),
        }


async def update_config_center(payload: Dict[str, Any]) -> Dict[str, Any]:
    if payload.get("ai_model_configs") is not None:
        await update_ai_model_configs_section(payload.get("ai_model_configs"))
    if payload.get("role_config_items") is not None or payload.get("role_configs") is not None:
        await update_role_configs_section(payload)
    if payload.get("prompt_configs") is not None or payload.get("prompts") is not None:
        await update_prompt_configs_section(payload)
    if payload.get("generation_behavior_configs") is not None:
        await update_generation_behavior_configs_section(payload.get("generation_behavior_configs"))
    if payload.get("notifications") is not None:
        await update_notifications_section(payload.get("notifications") or {})
    return await get_config_center()


async def get_ai_model_configs_section() -> Dict[str, Any]:
    async with AsyncSessionLocal() as db:
        return {"ai_model_configs": await _load_ai_configs(db)}


async def update_ai_model_configs_section(items: Any) -> Dict[str, Any]:
    now = utc_now_text()
    items = items if isinstance(items, list) else []
    async with transactional_session() as db:
        await AIConfigRepository.clear(db)
        for item in items:
            if not isinstance(item, dict):
                continue
            config_id = str(item.get("id") or item.get("config_id") or "").strip()
            if not config_id:
                continue
            await AIConfigRepository.create(
                db,
                record_type="model",
                config_id=config_id,
                name=str(item.get("name") or ""),
                model_type=str(item.get("model_type") or "other"),
                api_key=str(item.get("api_key") or ""),
                api_base_url=str(item.get("api_base_url") or settings.LLM_BASE_URL),
                model_name=str(item.get("model_name") or settings.LLM_MODEL),
                max_tokens=int(item.get("max_tokens") or 4096),
                temperature=float(item.get("temperature") if item.get("temperature") is not None else 0.7),
                top_p=float(item.get("top_p") if item.get("top_p") is not None else 0.9),
                enabled=bool(item.get("enabled", True)),
                creator=str(item.get("creator") or "admin"),
                modifier=str(item.get("modifier") or "admin"),
                created_at=to_beijing_time_text(item.get("created_at")) or now,
                updated_at=to_beijing_time_text(item.get("updated_at")) or now,
            )
        return {"ai_model_configs": await _load_ai_configs(db)}


async def create_ai_model_config_item(payload: Dict[str, Any]) -> Dict[str, Any]:
    now = utc_now_text()
    payload = dict(payload or {})
    payload["id"] = str(payload.get("id") or payload.get("config_id") or f"ai-model-{now}").strip()
    return await update_ai_model_configs_section([*(await get_ai_model_configs_section())["ai_model_configs"], payload])


async def update_ai_model_config_item(config_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    current = (await get_ai_model_configs_section())["ai_model_configs"]
    idx = next((i for i, x in enumerate(current) if str(x.get("id")) == str(config_id)), -1)
    if idx < 0:
        raise ValueError("AI模型配置不存在")
    current[idx] = {**current[idx], **payload, "id": str(config_id)}
    return await update_ai_model_configs_section(current)


async def delete_ai_model_config_item(config_id: str) -> Dict[str, Any]:
    current = (await get_ai_model_configs_section())["ai_model_configs"]
    next_items = [x for x in current if str(x.get("id")) != str(config_id)]
    if len(next_items) == len(current):
        raise ValueError("AI模型配置不存在")
    return await update_ai_model_configs_section(next_items)


async def get_role_configs_section() -> Dict[str, Any]:
    async with AsyncSessionLocal() as db:
        return {
            "role_configs": await _load_role_map(db),
            "role_config_items": await _load_role_items(db),
            "ai_model_configs": await _load_ai_configs(db),
        }


async def update_role_configs_section(payload: Dict[str, Any]) -> Dict[str, Any]:
    items = payload.get("role_config_items") if isinstance(payload, dict) else []
    if not isinstance(items, list):
        items = []
    now = utc_now_text()
    async with transactional_session() as db:
        await RoleConfigRepository.clear(db)
        for role in items:
            if not isinstance(role, dict):
                continue
            role_type = _normalize_role_type(role.get("role_type") or role.get("role") or "generation")
            cfg_id = str(role.get("id") or role.get("config_id") or f"default-{role_type}-role-config").strip()
            await RoleConfigRepository.create(
                db,
                config_id=cfg_id,
                name=str(role.get("name") or f"默认{role_type}配置"),
                role_type=role_type,
                mapped_model_name=str(role.get("mapped_model_name") or settings.LLM_MODEL),
                enabled=bool(role.get("enabled", True)),
                creator=str(role.get("creator") or "admin"),
                modifier=str(role.get("modifier") or "admin"),
                created_at=to_beijing_time_text(role.get("created_at")) or now,
                updated_at=to_beijing_time_text(role.get("updated_at")) or now,
            )
        return {
            "role_configs": await _load_role_map(db),
            "role_config_items": await _load_role_items(db),
            "ai_model_configs": await _load_ai_configs(db),
        }


async def create_role_config_item(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = await get_role_configs_section()
    items = data["role_config_items"] + [payload]
    return await update_role_configs_section({"role_config_items": items})


async def update_role_config_item(config_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    data = await get_role_configs_section()
    items = data["role_config_items"]
    idx = next((i for i, x in enumerate(items) if str(x.get("id")) == str(config_id)), -1)
    if idx < 0:
        raise ValueError("角色配置不存在")
    items[idx] = {**items[idx], **payload, "id": str(config_id)}
    return await update_role_configs_section({"role_config_items": items})


async def delete_role_config_item(config_id: str) -> Dict[str, Any]:
    data = await get_role_configs_section()
    items = [x for x in data["role_config_items"] if str(x.get("id")) != str(config_id)]
    if len(items) == len(data["role_config_items"]):
        raise ValueError("角色配置不存在")
    return await update_role_configs_section({"role_config_items": items})


async def get_prompt_configs_section() -> Dict[str, Any]:
    async with AsyncSessionLocal() as db:
        return {"prompts": await _load_prompts(db), "prompt_configs": await _load_prompt_items(db)}


async def update_prompt_configs_section(payload: Dict[str, Any]) -> Dict[str, Any]:
    items = payload.get("prompt_configs") if isinstance(payload, dict) else []
    if not isinstance(items, list):
        items = []
    now = utc_now_text()
    async with transactional_session() as db:
        await PromptConfigRepository.clear(db)
        for item in items:
            if not isinstance(item, dict):
                continue
            role = _normalize_role_type(item.get("role") or item.get("prompt_type") or "generation")
            cfg_id = str(item.get("id") or item.get("config_id") or f"prompt-{now}").strip()
            await PromptConfigRepository.create(
                db,
                record_type="prompt",
                config_id=cfg_id,
                role=role,
                name=str(item.get("name") or ""),
                content=str(item.get("content") or ""),
                enabled=bool(item.get("enabled", True)),
                creator=str(item.get("creator") or "admin"),
                created_at=to_beijing_time_text(item.get("created_at")) or now,
                updated_at=to_beijing_time_text(item.get("updated_at")) or now,
            )
        return {"prompts": await _load_prompts(db), "prompt_configs": await _load_prompt_items(db)}


async def create_prompt_config_item(payload: Dict[str, Any]) -> Dict[str, Any]:
    data = await get_prompt_configs_section()
    return await update_prompt_configs_section({"prompt_configs": data["prompt_configs"] + [payload]})


async def update_prompt_config_item(config_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    data = await get_prompt_configs_section()
    items = data["prompt_configs"]
    idx = next((i for i, x in enumerate(items) if str(x.get("id")) == str(config_id)), -1)
    if idx < 0:
        raise ValueError("提示词配置不存在")
    items[idx] = {**items[idx], **payload, "id": str(config_id)}
    return await update_prompt_configs_section({"prompt_configs": items})


async def delete_prompt_config_item(config_id: str) -> Dict[str, Any]:
    data = await get_prompt_configs_section()
    items = [x for x in data["prompt_configs"] if str(x.get("id")) != str(config_id)]
    if len(items) == len(data["prompt_configs"]):
        raise ValueError("提示词配置不存在")
    return await update_prompt_configs_section({"prompt_configs": items})


async def get_generation_behavior_configs_section() -> Dict[str, Any]:
    async with AsyncSessionLocal() as db:
        return {"generation_behavior_configs": await _load_behavior_items(db)}


async def update_generation_behavior_configs_section(items: Any) -> Dict[str, Any]:
    items = items if isinstance(items, list) else []
    now = utc_now_text()
    async with transactional_session() as db:
        await GenerationBehaviorConfigRepository.clear(db)
        for item in items:
            if not isinstance(item, dict):
                continue
            cfg_id = str(item.get("id") or item.get("config_id") or f"generation-behavior-{now}").strip()
            await GenerationBehaviorConfigRepository.create(
                db,
                config_id=cfg_id,
                name=str(item.get("name") or "默认生成配置"),
                output_mode=str(item.get("output_mode") or "stream"),
                enable_ai_review=bool(item.get("enable_ai_review", True)),
                review_timeout_seconds=int(item.get("review_timeout_seconds") or 1500),
                enabled=bool(item.get("enabled", True)),
                created_at=to_beijing_time_text(item.get("created_at")) or now,
                updated_at=to_beijing_time_text(item.get("updated_at")) or now,
            )
        return {"generation_behavior_configs": await _load_behavior_items(db)}


async def create_generation_behavior_config_item(payload: Dict[str, Any]) -> Dict[str, Any]:
    current = (await get_generation_behavior_configs_section())["generation_behavior_configs"]
    return await update_generation_behavior_configs_section(current + [payload])


async def update_generation_behavior_config_item(config_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    current = (await get_generation_behavior_configs_section())["generation_behavior_configs"]
    idx = next((i for i, x in enumerate(current) if str(x.get("id")) == str(config_id)), -1)
    if idx < 0:
        raise ValueError("生成行为配置不存在")
    current[idx] = {**current[idx], **payload, "id": str(config_id)}
    return await update_generation_behavior_configs_section(current)


async def delete_generation_behavior_config_item(config_id: str) -> Dict[str, Any]:
    current = (await get_generation_behavior_configs_section())["generation_behavior_configs"]
    next_items = [x for x in current if str(x.get("id")) != str(config_id)]
    if len(next_items) == len(current):
        raise ValueError("生成行为配置不存在")
    return await update_generation_behavior_configs_section(next_items)


async def get_notifications_section() -> Dict[str, Any]:
    async with AsyncSessionLocal() as db:
        return {"notifications": await _load_notifications(db)}


async def update_notifications_section(notifications_payload: Dict[str, Any]) -> Dict[str, Any]:
    now = utc_now_text()
    async with transactional_session() as db:
        merged = await _load_notifications(db)
        for ch in ("feishu", "dingtalk", "wecom"):
            if ch not in notifications_payload:
                continue
            cur = notifications_payload.get(ch) or {}
            merged[ch] = {
                "name": str(cur.get("name") or merged[ch]["name"]),
                "enabled": bool(cur.get("enabled", merged[ch]["enabled"])),
                "webhook": str(cur.get("webhook") or merged[ch]["webhook"]),
                "secret": str(cur.get("secret") or merged[ch]["secret"]),
            }
        await NotificationConfigRepository.clear(db)
        for ch, cfg in merged.items():
            await NotificationConfigRepository.create(
                db,
                channel=ch,
                name=cfg["name"],
                enabled=cfg["enabled"],
                webhook=cfg["webhook"],
                secret=cfg["secret"],
                created_at=now,
                updated_at=now,
            )
        return {"notifications": await _load_notifications(db)}


async def create_notification_channel_config(channel: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return await update_notification_channel_config(channel, payload)


async def update_notification_channel_config(channel: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    channel = str(channel or "").strip().lower()
    if channel not in {"feishu", "dingtalk", "wecom"}:
        raise ValueError("通知渠道不支持")
    now = utc_now_text()
    async with transactional_session() as db:
        row = await NotificationConfigRepository.get_by_channel(db, channel)
        if row:
            row.name = str(payload.get("name") or row.name or "")
            row.enabled = bool(payload.get("enabled", row.enabled))
            row.webhook = str(payload.get("webhook") or row.webhook or "")
            row.secret = str(payload.get("secret") or row.secret or "")
            row.updated_at = now
        else:
            await NotificationConfigRepository.create(
                db,
                channel=channel,
                name=str(payload.get("name") or ""),
                enabled=bool(payload.get("enabled", False)),
                webhook=str(payload.get("webhook") or ""),
                secret=str(payload.get("secret") or ""),
                created_at=now,
                updated_at=now,
            )
        return {"notifications": await _load_notifications(db)}


async def delete_notification_channel_config(channel: str) -> Dict[str, Any]:
    channel = str(channel or "").strip().lower()
    async with transactional_session() as db:
        deleted = await NotificationConfigRepository.delete_by_channel(db, channel)
        if deleted <= 0:
            raise ValueError("消息提醒配置不存在")
        return {"notifications": await _load_notifications(db)}
