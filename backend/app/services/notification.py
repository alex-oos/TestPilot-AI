from typing import Any, Dict, List

import httpx
from loguru import logger

from app.core.config import settings
from app.modules.persistence import config_center_store


async def _send_to_webhook(channel: str, webhook: str, title: str, text: str, custom_keyword: str = "") -> None:
    if not webhook:
        return

    prefix = str(custom_keyword or "").strip()
    body = f"{prefix}\n{title}\n{text}" if prefix else f"{title}\n{text}"

    payload: Dict[str, Any]
    if channel == "feishu":
        payload = {
            "msg_type": "text",
            "content": {"text": body},
        }
    elif channel == "dingtalk":
        payload = {
            "msgtype": "text",
            "text": {"content": body},
        }
    else:  # wecom
        payload = {
            "msgtype": "text",
            "text": {"content": body},
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
) -> None:
    cfg = await config_center_store.get_config_center()
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

        webhook = str(channel_cfg.get("webhook") or "").strip()
        custom_keyword = str(channel_cfg.get("custom_keyword") or "").strip()
        if not webhook:
            continue

        try:
            await _send_to_webhook(channel, webhook, title, text, custom_keyword)
            logger.info(f"Notification sent via {channel} for task={task_id}")
        except Exception as exc:
            logger.error(f"Notification send failed via {channel} for task={task_id}: {exc}")


async def notify_dingtalk_adoption_decision(
    *,
    task_id: str,
    review_summary: str,
    submitter: str = "unknown",
) -> bool:
    cfg = await config_center_store.get_config_center()
    dingtalk_cfg = (cfg.get("notifications") or {}).get("dingtalk") or {}
    if not dingtalk_cfg.get("enabled"):
        logger.info(f"DingTalk notification disabled, skip decision request for task={task_id}")
        return False

    webhook = str(dingtalk_cfg.get("webhook") or "").strip()
    if not webhook:
        logger.info(f"DingTalk webhook missing, skip decision request for task={task_id}")
        return False

    base_url = settings.APP_BASE_URL.rstrip("/")
    accept_link = f"{base_url}/api/tasks/{task_id}/decision?decision=accepted&by=dingtalk"
    reject_link = f"{base_url}/api/tasks/{task_id}/decision?decision=rejected&by=dingtalk"

    content = (
        "[AI测试平台] 用例评审已完成，请确认是否采纳\n"
        f"任务ID: {task_id}\n"
        f"提交人: {submitter}\n"
        f"评审摘要: {review_summary or '无'}\n"
        f"采纳: {accept_link}\n"
        f"不采纳: {reject_link}"
    )

    payload: Dict[str, Any] = {
        "msgtype": "text",
        "text": {"content": content},
    }

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.post(webhook, json=payload)
            resp.raise_for_status()
        logger.info(f"DingTalk decision request sent for task={task_id}")
        return True
    except Exception as exc:
        logger.error(f"DingTalk decision request failed for task={task_id}: {exc}")
        return False
