from typing import Any, Dict

from app.modules.domain import config_center_domain


def get_notifications_section() -> Dict[str, Any]:
    return config_center_domain.get_notifications_section()


def update_notifications_section(notifications_payload: Dict[str, Any]) -> Dict[str, Any]:
    return config_center_domain.update_notifications_section(notifications_payload)


def create_notification_channel_config(channel: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return config_center_domain.create_notification_channel_config(channel, payload)


def update_notification_channel_config(channel: str, payload: Dict[str, Any]) -> Dict[str, Any]:
    return config_center_domain.update_notification_channel_config(channel, payload)


def delete_notification_channel_config(channel: str) -> Dict[str, Any]:
    return config_center_domain.delete_notification_channel_config(channel)
