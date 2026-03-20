from datetime import datetime, timedelta, timezone
from typing import Any, Optional

_BEIJING_TZ = timezone(timedelta(hours=8), name="Asia/Shanghai")
_DB_TIME_FORMAT = "%Y-%m-%d %H:%M:%S"


def utc_now_text() -> str:
    return datetime.now(_BEIJING_TZ).strftime(_DB_TIME_FORMAT)


def to_beijing_time_text(value: Any) -> str:
    if value is None:
        return ""

    dt: Optional[datetime] = None
    if isinstance(value, datetime):
        dt = value
    else:
        text_value = str(value).strip()
        if not text_value:
            return ""
        parse_value = text_value[:-1] + "+00:00" if text_value.endswith("Z") else text_value
        try:
            dt = datetime.fromisoformat(parse_value)
        except ValueError:
            for fmt in (_DB_TIME_FORMAT, "%Y-%m-%d %H:%M:%S.%f"):
                try:
                    dt = datetime.strptime(text_value, fmt)
                    break
                except ValueError:
                    continue
            if dt is None:
                return text_value

    if dt.tzinfo is None:
        return dt.strftime(_DB_TIME_FORMAT)
    return dt.astimezone(_BEIJING_TZ).strftime(_DB_TIME_FORMAT)
