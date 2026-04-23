"""Skill 审计：记录每次 LLM 调用使用的 skill 元信息，便于追溯和 A/B 比较。

存储策略：
- 进程内 in-memory ring buffer（最近 N 条）—— 给前端 / 诊断接口实时查询
- 同时（QA_SKILL_AUDIT_PERSIST=true）落库到 SQLite 独立表 skill_audits
- pipeline.py 还会把每阶段的审计快照写到 task_details.data_json.skill_audit
"""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import threading
import time
from collections import deque
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from loguru import logger


@dataclass
class SkillAuditRecord:
    ts: float
    role: str                          # analysis / generation / review / supplement / discover / strategy
    task_id: str | None = None
    skill_id: str = ""
    skill_version: str = ""
    skill_lang: str = ""
    content_hash: str = ""
    overlays_applied: list[str] = field(default_factory=list)
    used_fewshot: bool = False
    detected_lang: str = ""
    prompt_tokens_est: int = 0
    prompt_tokens_actual: int = 0
    completion_tokens_actual: int = 0
    over_budget: bool = False
    extra_prompt_present: bool = False
    extra: dict[str, Any] = field(default_factory=dict)


_RING: deque[SkillAuditRecord] = deque(maxlen=500)
_LOCK = threading.Lock()

# ----------- SQLite 持久化 -----------
_DB_PATH: Path | None = None
_DB_INIT_DONE = False


def _resolve_db_path() -> Path:
    raw = os.environ.get("SQLITE_DB_PATH", "./data/app.db")
    p = Path(raw)
    if not p.is_absolute():
        p = Path(__file__).resolve().parents[3] / raw.lstrip("./")
    return p


async def init_audit_storage() -> None:
    """启动时建表。失败仅 WARN，不影响其他流程。"""
    global _DB_PATH, _DB_INIT_DONE
    try:
        _DB_PATH = _resolve_db_path()
        _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(_create_table_sync, _DB_PATH)
        _DB_INIT_DONE = True
        logger.info("[skill] audit SQLite 已初始化: {}", _DB_PATH)
    except Exception as exc:
        logger.warning("[skill] audit SQLite 初始化失败（仅使用内存 ring）: {}", exc)
        _DB_INIT_DONE = False


def _create_table_sync(path: Path) -> None:
    conn = sqlite3.connect(str(path))
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS skill_audits (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ts REAL NOT NULL,
                role TEXT NOT NULL,
                task_id TEXT,
                skill_id TEXT,
                skill_version TEXT,
                skill_lang TEXT,
                content_hash TEXT,
                overlays_applied TEXT,
                used_fewshot INTEGER,
                detected_lang TEXT,
                prompt_tokens_est INTEGER,
                prompt_tokens_actual INTEGER,
                completion_tokens_actual INTEGER,
                over_budget INTEGER,
                extra_prompt_present INTEGER,
                extra_json TEXT
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_task ON skill_audits(task_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_ts ON skill_audits(ts)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_audit_role ON skill_audits(role)")
        conn.commit()
    finally:
        conn.close()


def _persist_sync(rec: SkillAuditRecord) -> None:
    if not _DB_INIT_DONE or _DB_PATH is None:
        return
    try:
        from app.core.config import settings
        if not bool(getattr(settings, "QA_SKILL_AUDIT_PERSIST", True)):
            return
    except Exception:
        pass
    try:
        conn = sqlite3.connect(str(_DB_PATH))
        try:
            conn.execute(
                """
                INSERT INTO skill_audits
                (ts, role, task_id, skill_id, skill_version, skill_lang, content_hash,
                 overlays_applied, used_fewshot, detected_lang, prompt_tokens_est,
                 prompt_tokens_actual, completion_tokens_actual, over_budget,
                 extra_prompt_present, extra_json)
                VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    rec.ts, rec.role, rec.task_id, rec.skill_id, rec.skill_version,
                    rec.skill_lang, rec.content_hash,
                    json.dumps(rec.overlays_applied, ensure_ascii=False),
                    1 if rec.used_fewshot else 0,
                    rec.detected_lang, rec.prompt_tokens_est,
                    rec.prompt_tokens_actual, rec.completion_tokens_actual,
                    1 if rec.over_budget else 0,
                    1 if rec.extra_prompt_present else 0,
                    json.dumps(rec.extra, ensure_ascii=False),
                ),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        logger.warning("[skill] audit 落库失败: {}", exc)


def record(rec: SkillAuditRecord) -> None:
    with _LOCK:
        _RING.append(rec)
    # 同步落库（SQLite 写入 < 1ms，远低于 LLM 调用耗时）
    # 同步是为了让后续 update_actual_tokens 能立刻找到对应 row
    _persist_sync(rec)


def from_meta(
    *,
    role: str,
    meta: dict[str, Any],
    task_id: str | None = None,
    extra_prompt_present: bool = False,
    extra: dict[str, Any] | None = None,
) -> SkillAuditRecord:
    rec = SkillAuditRecord(
        ts=time.time(),
        role=role,
        task_id=task_id,
        skill_id=str(meta.get("skill_id") or ""),
        skill_version=str(meta.get("version") or ""),
        skill_lang=str(meta.get("lang") or ""),
        content_hash=str(meta.get("content_hash") or ""),
        overlays_applied=list(meta.get("overlays_applied") or []),
        used_fewshot=bool(meta.get("used_fewshot")),
        detected_lang=str(meta.get("detected_lang") or ""),
        prompt_tokens_est=int(meta.get("prompt_tokens_est") or 0),
        over_budget=bool(meta.get("over_budget")),
        extra_prompt_present=extra_prompt_present,
        extra=extra or {},
    )
    record(rec)
    return rec


def list_recent(limit: int = 50, role: str | None = None, task_id: str | None = None) -> list[dict[str, Any]]:
    with _LOCK:
        items = list(_RING)
    if role:
        items = [r for r in items if r.role == role]
    if task_id:
        items = [r for r in items if r.task_id == task_id]
    items = items[-limit:]
    return [asdict(r) for r in reversed(items)]


def clear() -> None:
    with _LOCK:
        _RING.clear()


# ----------- 持久化查询 -----------

def query_persisted(
    *,
    limit: int = 100,
    offset: int = 0,
    role: str | None = None,
    task_id: str | None = None,
    skill_id: str | None = None,
) -> dict[str, Any]:
    """从 SQLite 查询审计记录（分页）。"""
    if not _DB_INIT_DONE or _DB_PATH is None:
        return {"items": [], "total": 0, "persisted": False}
    where, params = [], []
    if role:
        where.append("role = ?"); params.append(role)
    if task_id:
        where.append("task_id = ?"); params.append(task_id)
    if skill_id:
        where.append("skill_id = ?"); params.append(skill_id)
    sql_where = ("WHERE " + " AND ".join(where)) if where else ""
    conn = sqlite3.connect(str(_DB_PATH))
    try:
        conn.row_factory = sqlite3.Row
        total = conn.execute(f"SELECT COUNT(*) AS c FROM skill_audits {sql_where}", params).fetchone()["c"]
        rows = conn.execute(
            f"SELECT * FROM skill_audits {sql_where} ORDER BY id DESC LIMIT ? OFFSET ?",
            (*params, limit, offset),
        ).fetchall()
    finally:
        conn.close()
    items = []
    for r in rows:
        d = dict(r)
        d["overlays_applied"] = json.loads(d.get("overlays_applied") or "[]")
        d["extra"] = json.loads(d.get("extra_json") or "{}")
        d.pop("extra_json", None)
        d["used_fewshot"] = bool(d["used_fewshot"])
        d["over_budget"] = bool(d["over_budget"])
        d["extra_prompt_present"] = bool(d["extra_prompt_present"])
        items.append(d)
    return {"items": items, "total": int(total), "persisted": True}


def get_token_usage_stats() -> dict[str, Any]:
    """聚合统计：按 role / skill 维度统计 token 消耗、few-shot 命中率。"""
    if not _DB_INIT_DONE or _DB_PATH is None:
        return {"persisted": False, "by_role": [], "by_skill": []}
    conn = sqlite3.connect(str(_DB_PATH))
    try:
        conn.row_factory = sqlite3.Row
        by_role = [dict(r) for r in conn.execute(
            """
            SELECT role,
                   COUNT(*) AS calls,
                   SUM(prompt_tokens_actual) AS prompt_actual_sum,
                   SUM(completion_tokens_actual) AS completion_actual_sum,
                   AVG(prompt_tokens_est) AS prompt_est_avg,
                   SUM(over_budget) AS over_budget_count,
                   SUM(used_fewshot) AS fewshot_used
            FROM skill_audits GROUP BY role ORDER BY calls DESC
            """
        ).fetchall()]
        by_skill = [dict(r) for r in conn.execute(
            """
            SELECT skill_id,
                   COUNT(*) AS calls,
                   SUM(prompt_tokens_actual) AS prompt_actual_sum,
                   SUM(completion_tokens_actual) AS completion_actual_sum
            FROM skill_audits WHERE skill_id != '' GROUP BY skill_id ORDER BY calls DESC
            """
        ).fetchall()]
    finally:
        conn.close()
    return {"persisted": True, "by_role": by_role, "by_skill": by_skill}


def update_actual_tokens(record_id_filter: dict[str, Any], usage: dict[str, int]) -> None:
    """根据 ts 范围 + role + task_id 把最近一条审计补上真实 token 用量。"""
    if not _DB_INIT_DONE or _DB_PATH is None:
        return
    if not usage:
        return
    role = record_id_filter.get("role")
    task_id = record_id_filter.get("task_id")
    if not role:
        return
    pt = int(usage.get("prompt_tokens", 0) or 0)
    ct = int(usage.get("completion_tokens", 0) or 0)
    try:
        conn = sqlite3.connect(str(_DB_PATH))
        try:
            row = conn.execute(
                "SELECT id FROM skill_audits WHERE role=? AND (task_id=? OR ?='' ) "
                "ORDER BY id DESC LIMIT 1",
                (role, task_id or "", "" if task_id else "_"),
            ).fetchone()
            if row:
                conn.execute(
                    "UPDATE skill_audits SET prompt_tokens_actual=?, completion_tokens_actual=? WHERE id=?",
                    (pt, ct, row[0]),
                )
                conn.commit()
        finally:
            conn.close()
    except Exception as exc:
        logger.debug("[skill] audit 回填 token 失败: {}", exc)
    # 同步更新 ring 里最近一条
    with _LOCK:
        for rec in reversed(_RING):
            if rec.role == role and (not task_id or rec.task_id == task_id):
                rec.prompt_tokens_actual = pt
                rec.completion_tokens_actual = ct
                break
