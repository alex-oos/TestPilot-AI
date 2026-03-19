from fastapi import HTTPException

from app.ai.llm import llm_client
from app.core import database
from app.schemas.config_center import ConfigCenterUpdateRequest, TestModelRequest


def get_config_center() -> dict:
    return database.get_config_center()


def update_config_center(payload: ConfigCenterUpdateRequest) -> dict:
    return database.update_config_center(payload.model_dump(exclude_none=True))


def get_default_prompts() -> list[dict]:
    return database.get_default_prompt_configs()


def get_ai_model_configs_section() -> dict:
    return database.get_ai_model_configs_section()


def update_ai_model_configs_section(payload: dict) -> dict:
    return database.update_ai_model_configs_section(payload.get("ai_model_configs") or [])


def get_role_configs_section() -> dict:
    return database.get_role_configs_section()


def update_role_configs_section(payload: dict) -> dict:
    return database.update_role_configs_section(payload)


def get_prompt_configs_section() -> dict:
    return database.get_prompt_configs_section()


def update_prompt_configs_section(payload: dict) -> dict:
    return database.update_prompt_configs_section(payload)


def get_generation_behavior_configs_section() -> dict:
    return database.get_generation_behavior_configs_section()


def update_generation_behavior_configs_section(payload: dict) -> dict:
    return database.update_generation_behavior_configs_section(payload.get("generation_behavior_configs") or [])


def get_notifications_section() -> dict:
    return database.get_notifications_section()


def update_notifications_section(payload: dict) -> dict:
    return database.update_notifications_section(payload.get("notifications") or {})


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
