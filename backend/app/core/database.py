import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Generator, List, Optional

from loguru import logger

from app.core.config import settings


_DB_PATH = Path(settings.SQLITE_DB_PATH)


def _utc_now() -> str:
    return datetime.utcnow().isoformat(timespec="seconds") + "Z"


def _dict_factory(cursor: sqlite3.Cursor, row: sqlite3.Row) -> Dict[str, Any]:
    return {col[0]: row[idx] for idx, col in enumerate(cursor.description)}


@contextmanager
def get_conn() -> Generator[sqlite3.Connection, None, None]:
    _DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(_DB_PATH))
    conn.row_factory = _dict_factory
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                user_id INTEGER,
                source_type TEXT,
                doc_url TEXT,
                status TEXT NOT NULL,
                status_text TEXT,
                error TEXT,
                mindmap TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            )
            """
        )

        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS task_details (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                task_id TEXT NOT NULL,
                phase_key TEXT NOT NULL,
                phase_label TEXT NOT NULL,
                status TEXT NOT NULL,
                data_json TEXT,
                error TEXT,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                UNIQUE(task_id, phase_key),
                FOREIGN KEY(task_id) REFERENCES tasks(id)
            )
            """
        )

        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_task_details_task_id ON task_details(task_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)"
        )
        _ensure_column(conn, "tasks", "status_text", "TEXT")

    seed_default_user()
    logger.info(f"SQLite initialized: {_DB_PATH}")


def seed_default_user() -> None:
    now = _utc_now()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT id FROM users WHERE username = ?",
            ("admin",),
        ).fetchone()
        if row:
            return

        conn.execute(
            """
            INSERT INTO users(username, password, is_active, created_at, updated_at)
            VALUES (?, ?, 1, ?, ?)
            """,
            ("admin", "123456", now, now),
        )


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, column_type: str) -> None:
    cols = conn.execute(f"PRAGMA table_info({table})").fetchall()
    exists = any(col["name"] == column for col in cols)
    if not exists:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {column_type}")


def get_user_by_username(username: str) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        return conn.execute(
            "SELECT * FROM users WHERE username = ? LIMIT 1",
            (username,),
        ).fetchone()


def create_task_record(
    task_id: str,
    source_type: Optional[str],
    doc_url: Optional[str],
    status: str = "running",
    status_text: Optional[str] = "本地文件分析中",
    user_id: Optional[int] = None,
) -> None:
    now = _utc_now()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO tasks(id, user_id, source_type, doc_url, status, status_text, error, mindmap, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, NULL, NULL, ?, ?)
            """,
            (task_id, user_id, source_type, doc_url, status, status_text, now, now),
        )

        phase_rows = [
            (task_id, "analysis", "需求分析", "pending", None, None, now, now),
            (task_id, "generation", "用例编写", "pending", None, None, now, now),
            (task_id, "review", "用例评审", "pending", None, None, now, now),
        ]
        conn.executemany(
            """
            INSERT INTO task_details(task_id, phase_key, phase_label, status, data_json, error, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            phase_rows,
        )


def update_task_status(
    task_id: str,
    status: str,
    error: Optional[str] = None,
    status_text: Optional[str] = None,
) -> None:
    now = _utc_now()
    with get_conn() as conn:
        conn.execute(
            "UPDATE tasks SET status = ?, status_text = COALESCE(?, status_text), error = ?, updated_at = ? WHERE id = ?",
            (status, status_text, error, now, task_id),
        )


def update_task_mindmap(task_id: str, mindmap: str) -> None:
    now = _utc_now()
    with get_conn() as conn:
        conn.execute(
            "UPDATE tasks SET mindmap = ?, updated_at = ? WHERE id = ?",
            (mindmap, now, task_id),
        )


def update_task_phase(
    task_id: str,
    phase_key: str,
    status: str,
    data: Optional[Any] = None,
    error: Optional[str] = None,
) -> None:
    now = _utc_now()
    data_json = json.dumps(data, ensure_ascii=False) if data is not None else None

    with get_conn() as conn:
        conn.execute(
            """
            UPDATE task_details
            SET status = ?, data_json = COALESCE(?, data_json), error = ?, updated_at = ?
            WHERE task_id = ? AND phase_key = ?
            """,
            (status, data_json, error, now, task_id, phase_key),
        )


def get_task_record(task_id: str) -> Optional[Dict[str, Any]]:
    with get_conn() as conn:
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if not task:
            return None

        rows = conn.execute(
            "SELECT phase_key, phase_label, status, data_json, error FROM task_details WHERE task_id = ?",
            (task_id,),
        ).fetchall()

    phases: Dict[str, Dict[str, Any]] = {}
    for row in rows:
        parsed_data = None
        if row["data_json"]:
            try:
                parsed_data = json.loads(row["data_json"])
            except json.JSONDecodeError:
                parsed_data = None

        phases[row["phase_key"]] = {
            "status": row["status"],
            "label": row["phase_label"],
            "data": parsed_data,
        }

    return {
        "id": task["id"],
        "status": task["status"],
        "status_text": task.get("status_text"),
        "phases": phases,
        "mindmap": task["mindmap"],
        "error": task["error"],
    }


def list_tasks(limit: int = 50) -> List[Dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, user_id, source_type, doc_url, status, error, created_at, updated_at
            , status_text
            FROM tasks
            ORDER BY updated_at DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    return rows
