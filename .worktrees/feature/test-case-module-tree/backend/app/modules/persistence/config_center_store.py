from typing import Any, Dict

from app.modules.domain import config_center_domain


async def get_config_center() -> Dict[str, Any]:
    return await config_center_domain.get_config_center()


async def update_config_center(payload: Dict[str, Any]) -> Dict[str, Any]:
    return await config_center_domain.update_config_center(payload)


async def get_default_prompt_configs() -> list[dict]:
    return await config_center_domain.get_default_prompt_configs()


async def get_ai_model_configs_section() -> Dict[str, Any]:
    return await config_center_domain.get_ai_model_configs_section()


async def update_ai_model_configs_section(items: Any) -> Dict[str, Any]:
    return await config_center_domain.update_ai_model_configs_section(items)


async def create_ai_model_config_item(payload: Dict[str, Any]) -> Dict[str, Any]:
    return await config_center_domain.create_ai_model_config_item(payload)


async def update_ai_model_config_item(config_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return await config_center_domain.update_ai_model_config_item(config_id, payload)


async def delete_ai_model_config_item(config_id: str) -> Dict[str, Any]:
    return await config_center_domain.delete_ai_model_config_item(config_id)


async def get_role_configs_section() -> Dict[str, Any]:
    return await config_center_domain.get_role_configs_section()


async def update_role_configs_section(payload: Dict[str, Any]) -> Dict[str, Any]:
    return await config_center_domain.update_role_configs_section(payload)


async def create_role_config_item(payload: Dict[str, Any]) -> Dict[str, Any]:
    return await config_center_domain.create_role_config_item(payload)


async def update_role_config_item(config_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return await config_center_domain.update_role_config_item(config_id, payload)


async def delete_role_config_item(config_id: str) -> Dict[str, Any]:
    return await config_center_domain.delete_role_config_item(config_id)


async def get_prompt_configs_section() -> Dict[str, Any]:
    return await config_center_domain.get_prompt_configs_section()


async def update_prompt_configs_section(payload: Dict[str, Any]) -> Dict[str, Any]:
    return await config_center_domain.update_prompt_configs_section(payload)


async def create_prompt_config_item(payload: Dict[str, Any]) -> Dict[str, Any]:
    return await config_center_domain.create_prompt_config_item(payload)


async def update_prompt_config_item(config_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return await config_center_domain.update_prompt_config_item(config_id, payload)


async def delete_prompt_config_item(config_id: str) -> Dict[str, Any]:
    return await config_center_domain.delete_prompt_config_item(config_id)


async def get_generation_behavior_configs_section() -> Dict[str, Any]:
    return await config_center_domain.get_generation_behavior_configs_section()


async def update_generation_behavior_configs_section(items: Any) -> Dict[str, Any]:
    return await config_center_domain.update_generation_behavior_configs_section(items)


async def create_generation_behavior_config_item(payload: Dict[str, Any]) -> Dict[str, Any]:
    return await config_center_domain.create_generation_behavior_config_item(payload)


async def update_generation_behavior_config_item(config_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return await config_center_domain.update_generation_behavior_config_item(config_id, payload)


async def delete_generation_behavior_config_item(config_id: str) -> Dict[str, Any]:
    return await config_center_domain.delete_generation_behavior_config_item(config_id)


async def get_notifications_section() -> Dict[str, Any]:
    return await config_center_domain.get_notifications_section()


async def update_notifications_section(payload: Dict[str, Any]) -> Dict[str, Any]:
    return await config_center_domain.update_notifications_section(payload)


async def create_notification_channel_config(channel: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return await config_center_domain.create_notification_channel_config(channel, payload)


async def update_notification_channel_config(channel: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return await config_center_domain.update_notification_channel_config(channel, payload)


async def delete_notification_channel_config(channel: str) -> Dict[str, Any]:
    return await config_center_domain.delete_notification_channel_config(channel)
