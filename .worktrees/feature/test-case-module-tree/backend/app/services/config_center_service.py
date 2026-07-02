from fastapi import HTTPException

from app.ai.llm import llm_client
from app.modules.persistence import config_center_store
from app.schemas.config_center import ConfigCenterUpdateRequest, TestModelRequest


async def get_config_center() -> dict:
    return await config_center_store.get_config_center()


async def update_config_center(payload: ConfigCenterUpdateRequest) -> dict:
    return await config_center_store.update_config_center(payload.model_dump(exclude_none=True))


async def get_default_prompts() -> list[dict]:
    return await config_center_store.get_default_prompt_configs()


async def get_ai_model_configs_section() -> dict:
    return await config_center_store.get_ai_model_configs_section()


async def update_ai_model_configs_section(payload: dict) -> dict:
    return await config_center_store.update_ai_model_configs_section(payload.get("ai_model_configs") or [])


async def create_ai_model_config_item(payload: dict) -> dict:
    try:
        return await config_center_store.create_ai_model_config_item(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def update_ai_model_config_item(config_id: str, payload: dict) -> dict:
    try:
        return await config_center_store.update_ai_model_config_item(config_id, payload)
    except ValueError as exc:
        message = str(exc)
        if "不存在" in message:
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=400, detail=message) from exc


async def delete_ai_model_config_item(config_id: str) -> dict:
    try:
        return await config_center_store.delete_ai_model_config_item(config_id)
    except ValueError as exc:
        message = str(exc)
        if "不存在" in message:
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=400, detail=message) from exc


async def get_role_configs_section() -> dict:
    return await config_center_store.get_role_configs_section()


async def update_role_configs_section(payload: dict) -> dict:
    return await config_center_store.update_role_configs_section(payload)


async def create_role_config_item(payload: dict) -> dict:
    try:
        return await config_center_store.create_role_config_item(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def update_role_config_item(config_id: str, payload: dict) -> dict:
    try:
        return await config_center_store.update_role_config_item(config_id, payload)
    except ValueError as exc:
        message = str(exc)
        if "不存在" in message:
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=400, detail=message) from exc


async def delete_role_config_item(config_id: str) -> dict:
    try:
        return await config_center_store.delete_role_config_item(config_id)
    except ValueError as exc:
        message = str(exc)
        if "不存在" in message:
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=400, detail=message) from exc


async def get_prompt_configs_section() -> dict:
    return await config_center_store.get_prompt_configs_section()


async def update_prompt_configs_section(payload: dict) -> dict:
    return await config_center_store.update_prompt_configs_section(payload)


async def create_prompt_config_item(payload: dict) -> dict:
    try:
        return await config_center_store.create_prompt_config_item(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def update_prompt_config_item(config_id: str, payload: dict) -> dict:
    try:
        return await config_center_store.update_prompt_config_item(config_id, payload)
    except ValueError as exc:
        message = str(exc)
        if "不存在" in message:
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=400, detail=message) from exc


async def delete_prompt_config_item(config_id: str) -> dict:
    try:
        return await config_center_store.delete_prompt_config_item(config_id)
    except ValueError as exc:
        message = str(exc)
        if "不存在" in message:
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=400, detail=message) from exc


async def get_generation_behavior_configs_section() -> dict:
    return await config_center_store.get_generation_behavior_configs_section()


async def update_generation_behavior_configs_section(payload: dict) -> dict:
    return await config_center_store.update_generation_behavior_configs_section(payload.get("generation_behavior_configs") or [])


async def create_generation_behavior_config_item(payload: dict) -> dict:
    try:
        return await config_center_store.create_generation_behavior_config_item(payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def update_generation_behavior_config_item(config_id: str, payload: dict) -> dict:
    try:
        return await config_center_store.update_generation_behavior_config_item(config_id, payload)
    except ValueError as exc:
        message = str(exc)
        if "不存在" in message:
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=400, detail=message) from exc


async def delete_generation_behavior_config_item(config_id: str) -> dict:
    try:
        return await config_center_store.delete_generation_behavior_config_item(config_id)
    except ValueError as exc:
        message = str(exc)
        if "不存在" in message:
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=400, detail=message) from exc


async def get_notifications_section() -> dict:
    return await config_center_store.get_notifications_section()


async def update_notifications_section(payload: dict) -> dict:
    return await config_center_store.update_notifications_section(payload.get("notifications") or {})


async def create_notification_channel_config(channel: str, payload: dict) -> dict:
    try:
        return await config_center_store.create_notification_channel_config(channel, payload)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


async def update_notification_channel_config(channel: str, payload: dict) -> dict:
    try:
        return await config_center_store.update_notification_channel_config(channel, payload)
    except ValueError as exc:
        message = str(exc)
        if "不存在" in message:
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=400, detail=message) from exc


async def delete_notification_channel_config(channel: str) -> dict:
    try:
        return await config_center_store.delete_notification_channel_config(channel)
    except ValueError as exc:
        message = str(exc)
        if "不存在" in message:
            raise HTTPException(status_code=404, detail=message) from exc
        raise HTTPException(status_code=400, detail=message) from exc


async def test_model_connection(payload: TestModelRequest) -> dict:
    text = await llm_client.chat(
        messages=[
            {"role": "system", "content": "你是一个连接测试助手，只回复 ok。"},
            {"role": "user", "content": "请返回: ok"},
        ],
        temperature=0,
        model=payload.model_name,
        api_key=payload.api_key,
        base_url=payload.api_base_url,
        max_tokens=16,
        top_p=1,
    )
    if text.strip().lower().startswith("error:"):
        raise HTTPException(status_code=400, detail=text)
    return {"message": "连接成功", "response": text}
