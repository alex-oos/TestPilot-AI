from typing import Any, Dict, List

import httpx
from loguru import logger

from app.core import database


def _match_business_types(channel_cfg: Dict[str, Any], biz_type: str) -> bool:
    types = channel_cfg.get("business_types") or []
    if not types:
        return True
    return biz_type in types


async def _send_to_webhook(channel: str, webhook: str, title: str, text: str) -> None:
    if not webhook:
        return

    payload: Dict[str, Any]
    if channel == "feishu":
        payload = {
            "msg_type": "text",
            "content": {"text": f"{title}\n{text}"},
        }
    elif channel == "dingtalk":
        payload = {
            "msgtype": "text",
            "text": {"content": f"{title}\n{text}"},
        }
    else:  # wecom
        payload = {
            "msgtype": "text",
            "text": {"content": f"{title}\n{text}"},
        }

    async with httpx.AsyncClient(timeout=8.0) as client:
        resp = await client.post(webhook, json=payload)
        resp.raise_for_status()


async def notify_task_event(
    *,
    task_id: str,
    task_status: str,
    status_text: str,
    error: str = "",
    biz_type: str = "ui_auto",
) -> None:
    cfg = database.get_config_center()
    notifications = cfg.get("notifications") or {}

    title = "[AI测试平台] 任务状态通知"
    lines: List[str] = [
        f"任务ID: {task_id}",
        f"任务状态: {task_status}",
        f"状态说明: {status_text}",
    ]
    if error:
        lines.append(f"异常信息: {error}")
    text = "\n".join(lines)

    for channel in ("feishu", "wecom", "dingtalk"):
        channel_cfg = notifications.get(channel) or {}
        if not channel_cfg.get("enabled"):
            continue
        if not _match_business_types(channel_cfg, biz_type):
            continue

        webhook = str(channel_cfg.get("webhook") or "").strip()
        if not webhook:
            continue

        try:
            await _send_to_webhook(channel, webhook, title, text)
            logger.info(f"Notification sent via {channel} for task={task_id}")
        except Exception as exc:
            logger.error(f"Notification send failed via {channel} for task={task_id}: {exc}")
