"""LLM 响应缓存：内存 LRU + SQLite 持久化。

key = sha256(model + JSON(messages) + temperature + JSON(response_format))

线程模型：
- 内存层：单进程内 OrderedDict（线程安全足够，因为 FastAPI 是单事件循环）
- SQLite 层：每次操作短连接打开/关闭，避免长连接锁

调用：
    llm_cache.get(key)        # -> dict | None
    llm_cache.put(key, **kwargs)
    llm_cache.purge_expired() # 启动时跑一次
    llm_cache.stats()         # 返回 hit/miss/size
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from collections import OrderedDict
from pathlib import Path
from threading import Lock
from typing import Any

from loguru import logger

from app.core.config import settings


def _resolve_db_path() -> Path:
    """与 audit.py 保持一致：backend/data/app.db。"""
    base = Path(__file__).resolve().parents[2]  # backend/
    db = settings.SQLITE_DB_PATH
    if db.startswith("./"):
        db = db[2:]
    return (base / db).resolve()


_LOCK = Lock()
_MEM: "OrderedDict[str, dict[str, Any]]" = OrderedDict()
_STATS = {"hits": 0, "misses": 0, "puts": 0}


def init_cache_storage() -> None:
    """启动时初始化 SQLite 表。"""
    if not getattr(settings, "LLM_CACHE_ENABLED", True):
        logger.info("[llm-cache] 已禁用 (LLM_CACHE_ENABLED=false)")
        return
    db = _resolve_db_path()
    db.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS llm_cache (
                cache_key TEXT PRIMARY KEY,
                model TEXT,
                content TEXT NOT NULL,
                prompt_tokens INTEGER DEFAULT 0,
                completion_tokens INTEGER DEFAULT 0,
                total_tokens INTEGER DEFAULT 0,
                created_at REAL NOT NULL
            )
            """
        )
        conn.commit()
        logger.info("[llm-cache] SQLite 已初始化: {}", db)
    finally:
        conn.close()


def make_cache_key(
    *,
    model: str,
    messages: list,
    temperature: float | None,
    response_format: Any,
) -> str:
    payload = {
        "model": model or "",
        "messages": messages or [],
        "temperature": float(temperature) if temperature is not None else None,
        "response_format": response_format,
    }
    blob = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()


def _ttl_seconds() -> int:
    return int(getattr(settings, "LLM_CACHE_TTL_HOURS", 168) or 0) * 3600


def _is_expired(created_at: float) -> bool:
    ttl = _ttl_seconds()
    if ttl <= 0:
        return False
    return (time.time() - float(created_at)) > ttl


def get(cache_key: str) -> dict[str, Any] | None:
    if not getattr(settings, "LLM_CACHE_ENABLED", True) or not cache_key:
        return None
    with _LOCK:
        item = _MEM.get(cache_key)
        if item:
            if _is_expired(item.get("created_at", 0)):
                _MEM.pop(cache_key, None)
            else:
                _MEM.move_to_end(cache_key)
                _STATS["hits"] += 1
                return dict(item)

    # SQLite 兜底
    try:
        conn = sqlite3.connect(str(_resolve_db_path()))
        try:
            row = conn.execute(
                "SELECT model, content, prompt_tokens, completion_tokens, total_tokens, created_at "
                "FROM llm_cache WHERE cache_key=?",
                (cache_key,),
            ).fetchone()
        finally:
            conn.close()
    except Exception as e:  # noqa
        logger.debug("[llm-cache] sqlite get 失败: {}", e)
        with _LOCK:
            _STATS["misses"] += 1
        return None

    if not row:
        with _LOCK:
            _STATS["misses"] += 1
        return None
    if _is_expired(row[5]):
        with _LOCK:
            _STATS["misses"] += 1
        return None

    item = {
        "model": row[0],
        "content": row[1],
        "usage": {
            "prompt_tokens": int(row[2] or 0),
            "completion_tokens": int(row[3] or 0),
            "total_tokens": int(row[4] or 0),
        },
        "created_at": float(row[5]),
    }
    with _LOCK:
        _STATS["hits"] += 1
        _MEM[cache_key] = item
        _trim_locked()
    return dict(item)


def put(
    cache_key: str,
    *,
    model: str,
    content: str,
    usage: dict | None = None,
) -> None:
    if not getattr(settings, "LLM_CACHE_ENABLED", True) or not cache_key:
        return
    if not content or content.startswith("Error:"):
        return  # 错误响应不缓存
    usage = usage or {}
    item = {
        "model": model or "",
        "content": content,
        "usage": {
            "prompt_tokens": int(usage.get("prompt_tokens") or 0),
            "completion_tokens": int(usage.get("completion_tokens") or 0),
            "total_tokens": int(usage.get("total_tokens") or 0),
        },
        "created_at": time.time(),
    }
    with _LOCK:
        _MEM[cache_key] = item
        _MEM.move_to_end(cache_key)
        _STATS["puts"] += 1
        _trim_locked()

    try:
        conn = sqlite3.connect(str(_resolve_db_path()))
        try:
            conn.execute(
                """
                INSERT OR REPLACE INTO llm_cache
                (cache_key, model, content, prompt_tokens, completion_tokens, total_tokens, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    cache_key, item["model"], item["content"],
                    item["usage"]["prompt_tokens"],
                    item["usage"]["completion_tokens"],
                    item["usage"]["total_tokens"],
                    item["created_at"],
                ),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as e:  # noqa
        logger.debug("[llm-cache] sqlite put 失败: {}", e)


def _trim_locked() -> None:
    cap = int(getattr(settings, "LLM_CACHE_MEM_MAX", 256))
    while len(_MEM) > cap:
        _MEM.popitem(last=False)


def purge_expired() -> int:
    """主动清理过期项。返回删除数量。"""
    ttl = _ttl_seconds()
    if ttl <= 0:
        return 0
    cutoff = time.time() - ttl
    deleted = 0
    try:
        conn = sqlite3.connect(str(_resolve_db_path()))
        try:
            cur = conn.execute("DELETE FROM llm_cache WHERE created_at < ?", (cutoff,))
            conn.commit()
            deleted = cur.rowcount or 0
        finally:
            conn.close()
    except Exception as e:  # noqa
        logger.debug("[llm-cache] purge 失败: {}", e)
    with _LOCK:
        for k in list(_MEM.keys()):
            if _is_expired(_MEM[k].get("created_at", 0)):
                _MEM.pop(k, None)
    if deleted:
        logger.info("[llm-cache] 清理过期 {} 条", deleted)
    return deleted


def clear_all() -> int:
    """清空内存 + SQLite。"""
    n = 0
    try:
        conn = sqlite3.connect(str(_resolve_db_path()))
        try:
            cur = conn.execute("DELETE FROM llm_cache")
            conn.commit()
            n = cur.rowcount or 0
        finally:
            conn.close()
    except Exception as e:  # noqa
        logger.debug("[llm-cache] clear 失败: {}", e)
    with _LOCK:
        _MEM.clear()
    return n


def stats() -> dict[str, Any]:
    with _LOCK:
        mem_size = len(_MEM)
        st = dict(_STATS)
    sqlite_size = 0
    try:
        conn = sqlite3.connect(str(_resolve_db_path()))
        try:
            sqlite_size = conn.execute("SELECT COUNT(*) FROM llm_cache").fetchone()[0]
        finally:
            conn.close()
    except Exception:  # noqa
        pass
    total_lookups = max(1, st["hits"] + st["misses"])
    return {
        "enabled": bool(getattr(settings, "LLM_CACHE_ENABLED", True)),
        "ttl_hours": int(getattr(settings, "LLM_CACHE_TTL_HOURS", 168)),
        "mem_size": mem_size,
        "mem_max": int(getattr(settings, "LLM_CACHE_MEM_MAX", 256)),
        "sqlite_size": sqlite_size,
        "hits": st["hits"],
        "misses": st["misses"],
        "puts": st["puts"],
        "hit_rate": round(st["hits"] / total_lookups, 4),
    }
