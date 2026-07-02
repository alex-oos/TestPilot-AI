"""LLM 调用并发信号量。

用 `asyncio.Semaphore` 限制同进程内同时进行的 LLM HTTP 请求数，
避免 OOM、避免触发供应商 RPM/TPM 限制。

调用：
    async with llm_concurrency.slot():
        await openai_client.chat.completions.create(...)
    stats() -> { current, peak, max, total_holds, total_wait_seconds }
"""

from __future__ import annotations

import asyncio
import time
from contextlib import asynccontextmanager
from typing import Any

from app.core.config import settings


_sem: asyncio.Semaphore | None = None
_STATS: dict[str, Any] = {
    "current": 0,
    "peak": 0,
    "total_holds": 0,
    "total_wait_seconds": 0.0,
}


def _ensure() -> asyncio.Semaphore:
    global _sem
    if _sem is None:
        cap = max(1, int(getattr(settings, "LLM_MAX_CONCURRENCY", 4) or 1))
        _sem = asyncio.Semaphore(cap)
    return _sem


@asynccontextmanager
async def slot():
    sem = _ensure()
    started = time.time()
    await sem.acquire()
    waited = time.time() - started
    _STATS["total_wait_seconds"] = round(_STATS["total_wait_seconds"] + waited, 4)
    _STATS["current"] += 1
    _STATS["total_holds"] += 1
    if _STATS["current"] > _STATS["peak"]:
        _STATS["peak"] = _STATS["current"]
    try:
        yield
    finally:
        _STATS["current"] = max(0, _STATS["current"] - 1)
        sem.release()


def stats() -> dict[str, Any]:
    sem = _ensure()
    cap = max(1, int(getattr(settings, "LLM_MAX_CONCURRENCY", 4) or 1))
    return {
        "max": cap,
        "current": _STATS["current"],
        "peak": _STATS["peak"],
        "total_holds": _STATS["total_holds"],
        "total_wait_seconds": _STATS["total_wait_seconds"],
        "available": getattr(sem, "_value", cap),
    }
