from typing import Any, Dict

from app.modules.domain import config_center_domain


def get_generation_behavior_configs_section() -> Dict[str, Any]:
    return config_center_domain.get_generation_behavior_configs_section()


def update_generation_behavior_configs_section(items: Any) -> Dict[str, Any]:
    return config_center_domain.update_generation_behavior_configs_section(items)


def create_generation_behavior_config_item(payload: Dict[str, Any]) -> Dict[str, Any]:
    return config_center_domain.create_generation_behavior_config_item(payload)


def update_generation_behavior_config_item(config_id: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return config_center_domain.update_generation_behavior_config_item(config_id, payload)


def delete_generation_behavior_config_item(config_id: str) -> Dict[str, Any]:
    return config_center_domain.delete_generation_behavior_config_item(config_id)
