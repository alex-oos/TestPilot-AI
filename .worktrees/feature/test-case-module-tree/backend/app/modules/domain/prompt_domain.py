from typing import Any, Dict

from app.modules.domain import config_center_domain


def get_prompt_configs_section() -> Dict[str, Any]:
    return config_center_domain.get_prompt_configs_section()


def update_prompt_configs_section(payload: Dict[str, Any]) -> Dict[str, Any]:
    return config_center_domain.update_prompt_configs_section(payload)


def create_prompt_config_item(payload: Dict[str, Any]) -> Dict[str, Any]:
    return config_center_domain.create_prompt_config_item(payload)


def update_prompt_config_item(config_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return config_center_domain.update_prompt_config_item(config_id, payload)


def delete_prompt_config_item(config_id: str) -> Dict[str, Any]:
    return config_center_domain.delete_prompt_config_item(config_id)
