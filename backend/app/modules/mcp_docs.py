from __future__ import annotations

from typing import Any

import httpx
from loguru import logger


def _extract_text_from_mcp_response(payload: Any) -> str:
    if isinstance(payload, str):
        return payload.strip()
    if not isinstance(payload, dict):
        return ""

    for key in ("text", "content", "result_text"):
        value = payload.get(key)
        if isinstance(value, str) and value.strip():
            return value.strip()

    data = payload.get("data")
    if isinstance(data, dict):
        text = _extract_text_from_mcp_response(data)
        if text:
            return text

    result = payload.get("result")
    if isinstance(result, str):
        return result.strip()
    if isinstance(result, dict):
        text = _extract_text_from_mcp_response(result)
        if text:
            return text

    # Compatible with MCP tool response: {"result": {"content": [{"type":"text","text":"..."}]}}
    content = None
    if isinstance(result, dict):
        content = result.get("content")
    elif isinstance(payload.get("content"), list):
        content = payload.get("content")
    if isinstance(content, list):
        texts: list[str] = []
        for item in content:
            if isinstance(item, dict):
                if item.get("type") == "text" and isinstance(item.get("text"), str):
                    if item["text"].strip():
                        texts.append(item["text"].strip())
        if texts:
            return "\n".join(texts)

    return ""


async def fetch_document_via_mcp(
    *,
    provider: str,
    mcp_base_url: str,
    invoke_path: str,
    tool_name: str,
    doc_url: str,
    api_key: str = "",
    timeout_seconds: int = 20,
) -> str:
    base_url = (mcp_base_url or "").strip().rstrip("/")
    if not base_url:
        raise RuntimeError(f"{provider} MCP 服务地址未配置")
    if not doc_url.strip():
        raise RuntimeError(f"{provider} 文档地址为空")

    endpoint = f"{base_url}{invoke_path}"
    payload = {
        "tool": tool_name,
        "arguments": {
            "url": doc_url.strip(),
            "provider": provider,
        },
    }

    headers = {"Content-Type": "application/json"}
    if api_key.strip():
        headers["Authorization"] = f"Bearer {api_key.strip()}"

    logger.info("MCP doc fetch: provider={}, endpoint={}, tool={}", provider, endpoint, tool_name)
    async with httpx.AsyncClient(timeout=float(timeout_seconds)) as client:
        response = await client.post(endpoint, json=payload, headers=headers)
        response.raise_for_status()
        body = response.json()

    text = _extract_text_from_mcp_response(body)
    if not text:
        raise RuntimeError(f"{provider} MCP 返回内容中未找到可解析文本")
    return text
