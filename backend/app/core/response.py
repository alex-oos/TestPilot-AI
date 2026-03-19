from datetime import datetime, timezone
from typing import Any, Dict


def now_ms() -> int:
    return int(datetime.now(timezone.utc).timestamp() * 1000)


def success(data: Any, tid: str) -> Dict[str, Any]:
    return {
        "code": 0,
        "msg": "success",
        "data": data,
        "tid": tid,
        "ts": now_ms(),
    }


def error(code: int, msg: str, tid: str, data: Any = None) -> Dict[str, Any]:
    return {
        "code": code,
        "msg": msg,
        "data": data,
        "tid": tid,
        "ts": now_ms(),
    }
